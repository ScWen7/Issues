"""Check composed order materials against actual Codex App Server model requests."""
import argparse
from copy import deepcopy
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "knowledge"))
from observe_context import client_for
from observe_rule import RecordingEndpoint, string_leaves


DIRECTIVE = "Use the supplied order work materials for this turn."


class CompositionEndpoint(RecordingEndpoint):
    def do_POST(self):
        if self.path == "/v1/responses":
            if self.headers.get("Content-Encoding", "identity") != "identity":
                self.send_error(415, "expected the uncompressed fixture transport")
                return
            # The inherited recorder reads and hashes exactly this request body.
            self.server.wire_lengths.append(int(self.headers["Content-Length"]))
        super().do_POST()


def digest(body):
    return sha256(body.encode("utf-8")).hexdigest()


def description(ref):
    # Only this string can reveal the prepared test Skill via its native catalog description.
    return f"Order research skill. Catalog locator CATALOG-{digest(ref)[:16]}."


def check_plan(plan):
    materials, cases = plan["materials"], plan["cases"]
    for ref, material in materials.items():
        marker, body = material["marker"], material["body"]
        if not marker or marker not in body or any(marker in m["body"] for k, m in materials.items() if k != ref):
            raise ValueError(f"{ref}: body marker must be exclusive to its own material")
        if material["kind"] == "skill" and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", ref):
            raise ValueError(f"{ref}: invalid native Skill name")
    if len({c["id"] for c in cases}) != len(cases):
        raise ValueError("duplicate case")
    for c in cases:
        check_case(c, materials)
    if not any(c["status"] == "blocked" for c in cases):
        raise ValueError("one blocked control is required")


def check_case(case, materials):
    refs, binding = case["selected"], case["binding"]
    if case["status"] not in ("blocked", "ready") or bool(refs) != (case["status"] == "ready"):
        raise ValueError("blocked cases withhold all materials; ready cases must have a selection")
    if set(refs) - materials.keys() or len(refs) != len(set(refs)):
        raise ValueError(f"{case['id']}: unknown or duplicate selected material")
    if (not all(binding.get(k) for k in ("issue", "node", "run", "role"))
            or type(binding.get("attempt")) is not int or binding["attempt"] < 1):
        raise ValueError(f"{case['id']}: expected a bound Issue, node, attempt, Run and role")


def stage_skills(work, materials, refs):
    files = {}
    for ref in refs:
        path = work / ".agents" / "skills" / ref / "SKILL.md"
        path.parent.mkdir(parents=True)
        content = f"---\nname: {ref}\ndescription: {description(ref)}\n---\n" + materials[ref]["body"]
        path.write_bytes(content.encode("utf-8"))
        files[ref] = path, content
    return files


def inspect_wire(envelope, materials, selected, files, prompt):
    plain = [r for r in selected if materials[r]["kind"] != "skill"]
    hits, catalog = {}, {}
    framed_skills = {ref: f"<skill>\n<name>{ref}</name>\n<path>{path}</path>\n{content}\n</skill>"
                     for ref, (path, content) in files.items()}
    user_text = {f"input[{i}].content[{j}].text" for i, m in enumerate(envelope["input"]) if m.get("role") == "user"
                 for j, part in enumerate(m["content"]) if part.get("type") == "input_text"}
    prompt_paths = []
    for path, value in string_leaves(envelope):
        if value == prompt and path in user_text:
            prompt_paths.append(path)
        for ref, m in materials.items():
            if m["kind"] == "skill" and description(ref) in value:
                if value.startswith("<skills_instructions>") and ref in files:
                    catalog.setdefault(ref, []).append(path)
                elif ref not in selected or value != framed_skills.get(ref):
                    raise AssertionError(f"{ref}: unexpected catalog metadata in {path}")
            if m["marker"] not in value:
                continue
            if ref not in selected or ref in hits or path not in user_text:
                raise AssertionError(f"{ref}: unexpected occurrence in {path}")
            if ref in plain:
                if value != prompt:
                    raise AssertionError(f"{ref}: expected the exact composed user input")
                start = value.index(m["body"])
                observed, channel = value[start:start + len(m["body"])], "explicit_text"
            else:
                if value != framed_skills[ref]:
                    raise AssertionError(f"{ref}: expected the exact native Skill file inside its host wrapper")
                start = len(value) - len("\n</skill>") - len(m["body"])
                observed, channel = value[start:-len("\n</skill>")], "native_skill"
            if observed != m["body"]:
                raise AssertionError(f"{ref}: observed body mismatch")
            hits[ref] = {"ref": ref, "kind": m["kind"], "path": path, "channel": channel, "sha256": digest(observed)}
    if len(prompt_paths) != 1 or hits.keys() != set(selected) or catalog.keys() != files.keys():
        raise AssertionError("mismatch between selected, listed and actually supplied materials")
    return hits, catalog


def send_turn(binary, root, endpoint, materials, selected, staged, label):
    client, work = client_for(binary, root, label, endpoint)
    files = stage_skills(work, materials, staged)
    with client as rpc:
        catalog = rpc.call("skills/list", {"cwds": [str(work)]})
        available = {s["name"]: s for row in catalog["data"] for s in row["skills"] if s["scope"] == "repo"}
        if set(available) != files.keys() or any(not available[r]["enabled"] or available[r]["path"] != str(f[0])
                                                 for r, f in files.items()):
            raise AssertionError(f"unexpected worktree Skill catalog {list(available)}")
        thread = rpc.call("thread/start", {"cwd": str(work), "sandbox": "read-only",
                                           "approvalPolicy": "on-request"})["thread"]["id"]
        plain = [materials[r]["body"] for r in selected if r not in files]
        prompt = "\n\n".join([DIRECTIVE, *plain])
        inputs = [{"type": "text", "text": prompt}]
        inputs.extend({"type": "skill", "name": ref, "path": str(files[ref][0])} for ref in selected if ref in files)
        before = endpoint.requests
        turn = rpc.call("turn/start", {"threadId": thread, "input": inputs})["turn"]["id"]
        done = rpc.wait(lambda m: m.get("method") == "turn/completed" and m["params"]["turn"]["id"] == turn)
        history = rpc.call("thread/read", {"threadId": thread, "includeTurns": True})["thread"]["turns"]
        if (done["params"]["turn"]["status"] != "completed" or endpoint.requests != before + 1
                or [t["id"] for t in history] != [turn] or history[0]["status"] != "completed"):
            raise AssertionError("expected a single native turn and model request in a fresh thread")
        item_types = [item["type"] for item in history[0]["items"]]
        if item_types != ["userMessage", "agentMessage"]:
            raise AssertionError(f"fixture expected no tool execution, got {item_types}")
        envelope = endpoint.envelopes[before]
        hits, listed = inspect_wire(envelope, materials, selected, files, prompt)
        offered = [t.get("name", t["type"]) for t in envelope["tools"]]
        if "exec_command" not in offered:
            raise AssertionError("host's expected control tool is absent from the request")
        return {"thread_id": thread, "turn_id": turn, "wire_request_sha256": endpoint.wire_digests[before],
                "wire_request_bytes": endpoint.wire_lengths[before],
                "requests_before": before, "requests_after": endpoint.requests, "observations": [hits[r] for r in selected],
                "observed_sha256": {r: hits[r]["sha256"] for r in selected}, "native_skill_catalog": listed,
                "offered_tools": offered, "called_tools": [], "thread_read_item_types": item_types}


def observe(binary, root, endpoint, plan, before_dispatch):
    check_plan(plan)
    materials = plan["materials"]
    control_ref = "catalog-calibration"
    control_material = {"kind": "skill", "body": "Calibration only. CATALOG-BODY-CONTROL", "marker": "CATALOG-BODY-CONTROL"}
    if control_ref in materials:
        raise ValueError("the catalog control uses its own reserved synthetic skill")
    control = send_turn(binary, root, endpoint, {**materials, control_ref: control_material}, [], [control_ref], "catalog-control")
    records = []
    for i, queued in enumerate(plan["cases"]):
        before = endpoint.requests
        case = queued if before_dispatch is None else before_dispatch(deepcopy(queued))
        check_case(case, materials)
        if case["id"] != queued["id"] or case["binding"] != queued["binding"]:
            raise ValueError("dispatch recheck changed the identity of the queued case")
        refs = case["selected"]
        record = {key: case[key] for key in ("id", "binding", "selected", "status", "reason") if key in case}
        if case["status"] == "ready":
            staged = [r for r in refs if materials[r]["kind"] == "skill"]
            receipt = send_turn(binary, root, endpoint, materials, refs, staged, f"case-{i}")
        else:
            # A held dispatch has no host workspace, thread or turn.
            receipt = {"thread_id": None, "turn_id": None, "requests_before": before, "requests_after": endpoint.requests,
                       "observations": [], "observed_sha256": {}}
        records.append({**record, **receipt})
    ready = [r for r in records if r["status"] == "ready"]
    if len({r["turn_id"] for r in ready} | {control["turn_id"]}) != endpoint.requests or endpoint.requests != len(ready) + 1:
        raise AssertionError("not every request is uniquely accounted for by a completed turn")
    return {"cases": records, "catalog_control": control, "requests": endpoint.requests}


def run_host(codex, plan, before_dispatch=None):
    """With a callback, recheck each bound dispatch immediately before preparing its host."""
    binary = shutil.which(codex)
    if not binary or subprocess.check_output([binary, "--version"], text=True).strip() != "codex-cli 0.144.6":
        raise ValueError("this probe expects codex-cli 0.144.6")
    with tempfile.TemporaryDirectory() as tmp, ThreadingHTTPServer(("127.0.0.1", 0), CompositionEndpoint) as endpoint:
        endpoint.requests, endpoint.ask_mcp = 0, False
        endpoint.inputs, endpoint.envelopes, endpoint.wire_digests, endpoint.wire_lengths = [], [], [], []
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            report = observe(binary, Path(tmp), endpoint, plan, before_dispatch)
        finally:
            endpoint.shutdown()
    report.update(host="codex-cli 0.144.6", observer="local Responses endpoint")
    report["mode"] = "recorded_plan_replay" if before_dispatch is None else "pre_dispatch_recheck"
    return report


def main():
    parser = argparse.ArgumentParser(description="Replay a recorded synthetic dispatch plan in Codex.")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_host(args.codex, json.loads(args.plan.read_bytes()))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
