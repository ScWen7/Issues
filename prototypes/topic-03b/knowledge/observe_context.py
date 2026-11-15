"""Exercise role-scoped context and a revoked selection against an actual Codex host."""
import argparse
from contextlib import ExitStack
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observe_rule import RecordingEndpoint, fixture, string_leaves


STEPS = ("developer", "verifier", "old_thread_after_revoke", "new_thread_after_revoke")


def fingerprint(text):
    return sha256(text.encode("utf-8")).hexdigest()


def check_plan(plan):
    sections = plan["sections"]
    markers = plan.get("markers", sections)
    if (not sections or markers.keys() != sections.keys()
            or any(not isinstance(value, str) or not value.strip() for value in sections.values())):
        raise ValueError("expected a catalog of nonempty synthetic sections and matching marker keys")
    for ref, marker in markers.items():
        if (not isinstance(marker, str) or not marker.strip() or marker not in sections[ref]
                or any(marker in value for key, value in sections.items() if key != ref)):
            raise ValueError(f"{ref}: each test marker must be exclusive to its own section")
    turns = plan["turns"]
    if [t["step"] for t in turns] != list(STEPS):
        raise ValueError("unexpected probe sequence")
    for t in turns:
        selected = t["selected"]
        if not isinstance(selected, list) or len(set(selected)) != len(selected) or set(selected) - sections.keys():
            raise ValueError("unknown or duplicate selection")
        if not all(isinstance(t["binding"].get(k), str) and t["binding"][k] for k in ("issue", "run", "role")):
            raise ValueError("each turn must have a preselected Issue, Run and role")
    dev, ver, old, fresh = turns
    dev_refs, ver_refs = set(dev["selected"]), set(ver["selected"])
    if not (dev_refs - ver_refs and ver_refs - dev_refs and sections.keys() - dev_refs - ver_refs):
        raise ValueError("require developer-only, verifier-only and never-shared control paragraphs")
    if (dev["binding"]["role"] == ver["binding"]["role"] or
            not all(t["binding"]["role"] == dev["binding"]["role"] for t in (old, fresh)) or
            old["selected"] != fresh["selected"] or not dev_refs - set(old["selected"])):
        raise ValueError("require a withdrawn developer paragraph and identical post-revocation selections")
    return markers


def prompt_for(selected, sections):
    return "\n\n".join(["Review the authorized excerpts for this turn.", *(sections[key] for key in selected)])


def inspect_request(endpoint, index, current, history, sections, markers):
    items = endpoint.inputs[index]
    # The current user item must be the actual prompt; regress if the host changes framing.
    user_indices = [i for i, message in enumerate(items) if message.get("role") == "user"]
    last = user_indices[-1]
    if [p.get("text") for p in items[last]["content"]] != [prompt_for(current, sections)]:
        raise AssertionError("current user message differs from authorized assembly")
    assigned = {"current": set(), "history": set()}
    sightings = []
    eligible_paths = {
        f"input[{i}].content[{j}].text": ("current" if i == last else "history")
        for i in user_indices for j, part in enumerate(items[i]["content"]) if part.get("type") == "input_text"
    }
    # Inspect the complete model-bound envelope, including tools, instructions and carried input.
    for path, text in string_leaves(endpoint.envelopes[index]):
        for ref, marker in markers.items():
            if marker not in text:
                continue
            kind = eligible_paths.get(path)
            if kind is None or sections[ref] not in text:
                raise AssertionError(f"{ref}: unexpected request location or incomplete section at {path}")
            assigned[kind].add(ref)
            sightings.append({"ref": ref, "sha256": fingerprint(sections[ref]), "location": kind, "path": path})
    if assigned != {"current": set(current), "history": set(history)}:
        raise AssertionError(f"actual evidence does not match this control: {assigned}")
    return sightings


def client_for(binary, root, name, server):
    home, work = root / (name + "-home"), root / (name + "-work")
    home.mkdir()
    work.mkdir()
    subprocess.run(["git", "init", "-q", str(work)], check=True)
    (home / "config.toml").write_text(f'''model = "gpt-5.1-codex"
model_provider = "fixture"
project_doc_max_bytes = 0
[model_providers.fixture]
name = "fixture"
base_url = "http://127.0.0.1:{server.server_port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
[projects.{json.dumps(str(work))}]
trust_level = "trusted"
[analytics]
enabled = false
''')
    return fixture.client(binary, home, work), work


def observe(binary, plan, root, endpoint):
    markers = check_plan(plan)
    sections = plan["sections"]
    records = []
    with ExitStack() as stack:
        clients = {}
        for name in ("developer", "verifier"):
            client, cwd = client_for(binary, root, name, endpoint)
            clients[name] = (stack.enter_context(client), cwd)
        developer_thread = None
        for t in plan["turns"]:
            step, selected = t["step"], tuple(t["selected"])
            rpc, cwd = clients["verifier" if step == "verifier" else "developer"]
            if step == "old_thread_after_revoke":
                thread = developer_thread
                history = plan["turns"][0]["selected"]
            else:
                thread = rpc.call("thread/start", {"cwd": str(cwd), "sandbox": "read-only",
                                                   "approvalPolicy": "on-request"})["thread"]["id"]
                history = ()
            if step == "developer":
                developer_thread = thread
            binding = dict(t["binding"])
            prompt = prompt_for(selected, sections)
            before = endpoint.requests
            tid = rpc.call("turn/start", {"threadId": thread, "input": [{"type": "text", "text": prompt}]})["turn"]["id"]
            done = rpc.wait(lambda m: m.get("method") == "turn/completed" and m["params"]["turn"]["id"] == tid)
            if done["params"]["turn"]["status"] != "completed" or endpoint.requests != before + 1:
                raise AssertionError(f"{step}: expected one live request from one completed native turn")
            seen = inspect_request(endpoint, before, selected, history, sections, markers)
            records.append({"step": step, "binding": binding, "thread_id": thread, "turn_id": tid,
                            "selection": list(selected), "prompt_sha256": fingerprint(prompt),
                            "wire_request_sha256": endpoint.wire_digests[before], "observations": seen})
    if len({r["turn_id"] for r in records}) != 4 or len({r["thread_id"] for r in records}) != 3:
        raise AssertionError("unexpected native execution identity reuse")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    executable = shutil.which(args.codex)
    if not executable:
        parser.error("Codex executable not found")
    binary = Path(executable).resolve()
    version = subprocess.check_output([binary, "--version"], text=True).strip()
    if version != "codex-cli 0.144.6":
        parser.error("this regression uses codex-cli 0.144.6")
    plan = json.loads(args.plan.read_bytes())
    with tempfile.TemporaryDirectory() as tmp, ThreadingHTTPServer(("127.0.0.1", 0), RecordingEndpoint) as endpoint:
        endpoint.inputs, endpoint.wire_digests, endpoint.envelopes = [], [], []
        endpoint.requests, endpoint.ask_mcp = 0, False
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            turns = observe(binary, plan, Path(tmp), endpoint)
        finally:
            endpoint.shutdown()
    report = {"host": version, "observer": "localhost Responses fixture", "requests": len(turns), "turns": turns}
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
