"""Observe selected Rule bytes in three real Codex turns against a loopback model."""
import argparse
from hashlib import sha256
from http.server import ThreadingHTTPServer
from importlib import import_module
from io import BytesIO
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import threading


# Reuse the project-channel client and Responses fixture from Topic 3A.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "topic-03a"))
fixture = import_module("codex-context-probe")
EXPLICIT = "Current contract for this turn:\n"
STEPS = ("open_with_R1", "same_thread_after_R2_write", "same_thread_with_explicit_R2")


class RecordingEndpoint(fixture.CapturingEndpoint):
    def do_POST(self):
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.wire_digests.append(sha256(raw).hexdigest())
        self.server.envelopes.append(json.loads(raw))
        stream = self.rfile
        try:
            self.rfile = BytesIO(raw)
            super().do_POST()
        finally:
            self.rfile = stream


def string_leaves(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from string_leaves(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from string_leaves(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def input_evidence(items, project, rules):
    observations = []
    guide_prefix = f"# AGENTS.md instructions for {project}\n\n<INSTRUCTIONS>\n"
    guide_suffix = "\n</INSTRUCTIONS>"
    for index, item in enumerate(items):
        for part_index, part in enumerate(item.get("content", [])):
            if item.get("role") != "user" or part.get("type") != "input_text":
                continue
            text = part["text"]
            if text.startswith(guide_prefix) and text.endswith(guide_suffix):
                source, body = "project_file", text[len(guide_prefix):-len(guide_suffix)]
            elif text.startswith(EXPLICIT):
                source, body = "explicit_current_turn", text[len(EXPLICIT):]
            else:
                continue
            data = body.encode("utf-8")
            revision = next((key for key, value in rules.items() if data == value), None)
            if revision is None:
                raise AssertionError("observed Rule bytes differ from both selected inputs")
            observations.append({
                "rule": revision, "rule_sha256": sha256(data).hexdigest(), "source": source,
                "input_path": f"input[{index}].content[{part_index}].text",
                "message_text_sha256": sha256(text.encode()).hexdigest(),
            })
    return observations


def observe(binary, rules, project, home, endpoint, bindings):
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    (home / "config.toml").write_text(f'''model = "gpt-5.1-codex"
model_provider = "fixture"
[model_providers.fixture]
name = "fixture"
base_url = "http://127.0.0.1:{endpoint.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
[projects.{json.dumps(str(project))}]
trust_level = "trusted"
[analytics]
enabled = false
''')
    guide = project / "AGENTS.md"
    guide.write_bytes(rules["R1"])
    turns = []
    with fixture.client(binary, home, project) as rpc:
        thread = rpc.call("thread/start", {"cwd": str(project), "sandbox": "read-only",
                                         "approvalPolicy": "on-request"})["thread"]["id"]

        def turn(step, prompt, expected):
            # Capture the caller's dispatch reference before it opens the native turn.
            binding = bindings[step] if bindings is not None else None
            disk_sha = sha256(guide.read_bytes()).hexdigest()
            if binding is not None and binding["expected_rule_sha"] != disk_sha:
                raise ValueError(f"{step}: selection differs from the Rule staged for this invocation")
            before = endpoint.requests
            native_id = rpc.call("turn/start", {"threadId": thread,
                                  "input": [{"type": "text", "text": prompt}]})["turn"]["id"]
            done = rpc.wait(lambda x: x.get("method") == "turn/completed"
                            and x["params"]["turn"]["id"] == native_id)
            if done["params"]["turn"]["status"] != "completed" or endpoint.requests != before + 1:
                raise AssertionError(f"{step}: expected one request from a completed host turn")
            inputs = endpoint.inputs[before]
            matches = input_evidence(inputs, project, rules)
            if [(m["rule"], m["source"]) for m in matches] != expected:
                raise AssertionError(f"{step}: unexpected host inputs {matches!r}")
            # Scan the entire model envelope as well as the two known delivery channels.
            # A substring shared by R1 and R2 is attributed using the complete framed Rule.
            locations = {match["input_path"] for match in matches}
            for path, value in string_leaves(endpoint.envelopes[before]):
                if path not in locations and any(data.decode("utf-8") in value for data in rules.values()):
                    raise AssertionError(f"{step}: Rule also appeared at unclassified request path {path}")
            # Distinguish the carried project block from the actual submission of this round.
            last_user = next(i for i in reversed(inputs) if i.get("role") == "user")
            if [p.get("text") for p in last_user["content"]] != [prompt]:
                raise AssertionError(f"{step}: current submission missing from model request")
            for match in matches:
                if match["source"] == "project_file":
                    match["occurrence"] = "initial_file_input" if not turns else "carried_history"
                else:
                    match["occurrence"] = "current_submission"
            turns.append({
                "step": step, "thread_id": thread, "turn_id": native_id,
                "caller": "fixture_app_server_client", "observer": "loopback_responses_endpoint",
                **({"binding": binding} if binding is not None else {}),
                "project_file_sha256": disk_sha,
                "wire_request_sha256": endpoint.wire_digests[before],
                "input_json_sha256": sha256(json.dumps(inputs, ensure_ascii=False, sort_keys=True,
                                                       separators=(",", ":")).encode()).hexdigest(),
                "materials_in_model_request": matches,
            })

        old = [("R1", "project_file")]
        turn("open_with_R1", "Read the current export requirements.", old)
        guide.write_bytes(rules["R2"])
        turn("same_thread_after_R2_write", "Continue the export verification.", old)
        turn("same_thread_with_explicit_R2", EXPLICIT + rules["R2"].decode("utf-8"),
             old + [("R2", "explicit_current_turn")])
    if len({row["turn_id"] for row in turns}) != 3 or endpoint.requests != len(turns):
        raise AssertionError("host turn or request sequence did not match")
    return turns


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    for name in ("r1", "r2", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--bindings", type=Path, help="optional pre-dispatch Issue / Run identity for each step")
    args = parser.parse_args()
    bindings = None
    if args.bindings is not None:
        bindings = json.loads(args.bindings.read_bytes())
        if not isinstance(bindings, dict) or set(bindings) != set(STEPS):
            parser.error("bindings must identify all three probe steps")
        for binding in bindings.values():
            required = ("issue", "node", "instance", "run", "expected_rule_sha")
            if (not isinstance(binding, dict) or not all(isinstance(binding.get(k), str) and binding[k] for k in required)
                    or type(binding.get("attempt")) is not int or binding["attempt"] < 1):
                parser.error("invalid Issue / Run binding")
    executable = shutil.which(args.codex)
    if not executable:
        parser.error("Codex executable not found")
    binary = str(Path(executable).resolve())
    version = subprocess.check_output([binary, "--version"], text=True).strip()
    if version != "codex-cli 0.144.6":
        parser.error("this regression validates codex-cli 0.144.6")
    rules = {"R1": args.r1.read_bytes(), "R2": args.r2.read_bytes()}
    for data in rules.values():
        if not data.decode("utf-8").strip():
            parser.error("expected a nonempty UTF-8 Rule")
    if rules["R1"] == rules["R2"]:
        parser.error("choose distinct revisions to observe the transition")
    with tempfile.TemporaryDirectory() as temp, ThreadingHTTPServer(("127.0.0.1", 0), RecordingEndpoint) as server:
        project, home = Path(temp) / "project", Path(temp) / "home"
        project.mkdir()
        home.mkdir()
        server.wire_digests, server.envelopes = [], []
        server.inputs, server.requests, server.ask_mcp = [], 0, False
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            turns = observe(binary, rules, project, home, server, bindings)
        finally:
            server.shutdown()
    report = {"host": version, "transport": "App Server → local Responses fixture",
              "rule_sha256": {key: sha256(value).hexdigest() for key, value in rules.items()},
              "request_count": len(turns), "turns": turns}
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
