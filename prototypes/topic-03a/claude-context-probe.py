"""Claude Code context delivery probe. Python 3.10+, POSIX, Claude Code 2.1.325.

Run: python3 claude-context-probe.py /path/to/claude
Uses a temporary project, plain synthetic markers and loopback Messages SSE.
"""
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import shlex
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

D1 = "ORDER_RULE_F831_V1_NO_PAYMENT_TIME"
D2 = "ORDER_RULE_5A72_V2_INCLUDE_PAYMENT_TIME"
SKILL_NAME = "order-evidence"
SKILL_DESC = "ORDER_SKILL_DESC_9483"
SKILL_BODY = "ORDER_SKILL_BODY_C93E"
MCP_TOOL = "mcp__context_fixture__check_order"
MCP_RESULT = "MCP_ORDER_CHECK_7B3A"

def mcp_fixture(log_path):
    """Minimal local MCP stdio server implementing one read-only fixture tool."""
    for line in sys.stdin:
        req = json.loads(line)
        if "id" not in req:
            continue
        method = req["method"]
        if method == "initialize":
            answer = {"protocolVersion": req["params"]["protocolVersion"], "capabilities": {"tools": {}},
                      "serverInfo": {"name": "order-fixture", "version": "1.0"}}
        elif method == "tools/list":
            answer = {"tools": [{"name": "check_order", "description": "Inspect the synthetic order candidate.",
                                  "inputSchema": {"type": "object", "properties": {}}}]}
        elif method == "tools/call":
            assert req["params"]["name"] == "check_order"
            answer = {"content": [{"type": "text", "text": MCP_RESULT}]}
        elif method == "ping":
            answer = {}
        else:
            print(json.dumps({"jsonrpc": "2.0", "id": req["id"],
                              "error": {"code": -32601, "message": "Unknown method"}}), flush=True)
            continue
        with log_path.open("a") as dest:
            dest.write(method + "\n")
        print(json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": answer}), flush=True)



def sha(data):
    return hashlib.sha256(data).hexdigest()


def locations(payload, marker):
    """Capture only structural addresses of selected fixture markers."""
    paths = []
    def visit(value, path):
        if isinstance(value, dict):
            for name, child in value.items():
                visit(child, f"{path}.{name}" if path else name)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        elif isinstance(value, str) and marker in value:
            paths.append(path)
    visit(payload, "")
    return paths


class ModelFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path.split("?")[0] != "/v1/messages":
            self.send_error(404)
            return
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert payload.get("stream")
        self.server.requests.append({
            marker: locations(payload, marker) for marker in (D1, D2, SKILL_DESC, SKILL_BODY, MCP_TOOL, MCP_RESULT)
        })
        number = len(self.server.requests)
        if self.server.ask_tool:
            name = self.server.ask_tool
            self.server.ask_tool = None
            call_id = "toolu_order_skill" if name == "Skill" else "toolu_order_mcp"
            args = {"skill": SKILL_NAME} if name == "Skill" else {}
            block = {"type": "tool_use", "name": name, "id": call_id, "input": {}}
            delta = {"type": "input_json_delta", "partial_json": json.dumps(args)}
            reason = "tool_use"
        else:
            # All scenarios get exactly the same candidate, with no payment-time column.
            block = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": '{"columns":["order_id"]}'}
            reason = "end_turn"
        message = {"id": f"msg_fixture_{number}", "type": "message", "role": "assistant",
                   "model": payload["model"], "content": [], "stop_reason": None,
                   "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 0}}
        events = [
            {"type": "message_start", "message": message},
            {"type": "content_block_start", "index": 0, "content_block": block},
            {"type": "content_block_delta", "index": 0, "delta": delta},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": reason, "stop_sequence": None},
             "usage": {"output_tokens": 4}},
            {"type": "message_stop"},
        ]
        body = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def hook(path):
    event = json.load(sys.stdin)
    selected = {k: event[k] for k in ("hook_event_name", "file_path", "memory_type", "load_reason", "session_id",
                                      "tool_name", "tool_use_id", "source", "tool_input") if k in event}
    with path.open("a") as f:
        f.write(json.dumps(selected) + "\n")


def run_probe(cli, temp):
    config = temp / "config"
    project = temp / "project"
    config.mkdir()
    project.mkdir()
    skill = project / ".claude" / "skills" / SKILL_NAME / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(f"---\nname: {SKILL_NAME}\ndescription: {SKILL_DESC}\n---\n{SKILL_BODY}\n")
    hook_file = temp / "hooks.jsonl"
    hook_file.touch()
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "hook", str(hook_file)])
    events = ("SessionStart", "InstructionsLoaded", "UserPromptSubmit", "PreToolUse",
              "PostToolUse", "PostToolUseFailure", "Stop")
    settings = temp / "settings.json"
    settings.write_text(json.dumps({"hooks": {
        e: [{"hooks": [{"type": "command", "command": command}]}] for e in events
    }}))
    instructions = project / "CLAUDE.md"
    def material(version):
        requirement = "Export order_id." if version == D1 else "Export order_id and payment_time."
        return f"# Order export rule\n\nVersion {version}. {requirement}\n".encode()

    mcp_log = temp / "mcp-log"
    mcp_log.touch()
    mcp_config = temp / "mcp.json"
    mcp_config.write_text(json.dumps({"mcpServers": {"context_fixture": {"command": sys.executable,
        "args": [str(Path(__file__).resolve()), "mcp", str(mcp_log)]}}}))
    result_rows = {}
    with ThreadingHTTPServer(("127.0.0.1", 0), ModelFixture) as server:
        server.requests = []
        server.ask_tool = None
        threading.Thread(target=server.serve_forever, daemon=True).start()
        env = {
            "HOME": str(config), "CLAUDE_CONFIG_DIR": str(config), "PATH": os.environ["PATH"],
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}", "ANTHROPIC_API_KEY": "test-local-only",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
            "DISABLE_AUTOUPDATER": "1", "NO_COLOR": "1", "ENABLE_TOOL_SEARCH": "false",
        }
        def run(name, on_disk, expected, resume=None, invoke=None, with_mcp=False, pre_materialized=False):
            if pre_materialized:
                disk_bytes = instructions.read_bytes()
                assert expected.encode() in disk_bytes
            elif on_disk:
                instructions.write_bytes(material(on_disk))
            else:
                instructions.unlink(missing_ok=True)
            actual_hash = sha(instructions.read_bytes()) if instructions.exists() else None
            before_hooks = len(hook_file.read_text().splitlines())
            before_requests = len(server.requests)
            server.ask_tool = invoke
            before_mcp = len(mcp_log.read_text().splitlines())
            args = [cli, "-p", "--model", "claude-sonnet-4-6", f"--allowedTools=Skill,{MCP_TOOL}",
                    "--settings", str(settings), "--setting-sources", "project",
                    "--output-format", "stream-json", "--verbose"]
            if with_mcp:
                args += ["--mcp-config", str(mcp_config), "--strict-mcp-config"]
            if resume:
                args += ["--resume", resume]
            args += [f"Produce an order export candidate ({name})."]
            proc = subprocess.run(args, env=env, cwd=project, capture_output=True, text=True, timeout=60)
            if proc.returncode:
                raise RuntimeError(f"Claude exited {proc.returncode}: {proc.stderr.strip()}")
            frames = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
            result = next(f for f in frames if f["type"] == "result")
            assert result["subtype"] == "success" and not result["is_error"], result
            hooks = [json.loads(line) for line in hook_file.read_text().splitlines()[before_hooks:]]
            assert all(h["session_id"] == result["session_id"] for h in hooks)
            loads = [h for h in hooks if h.get("file_path") == str(instructions)
                     and h["hook_event_name"] == "InstructionsLoaded"]
            requests = server.requests[before_requests:]
            assert len(requests) == (2 if invoke else 1)
            tools = [(h["hook_event_name"], h.get("tool_use_id"), h.get("tool_input", {}).get("skill"))
                     for h in hooks if h.get("tool_name") in ("Skill", MCP_TOOL)]
            result_rows[name] = {
                "disk_sha256": actual_hash,
                "expected_content_sha256": None if pre_materialized else sha(material(expected)),
                "disk_expected_match": None if pre_materialized else actual_hash == sha(material(expected)),
                "instruction_hook": [(h.get("memory_type"), h.get("load_reason")) for h in loads],
                "request_marker_locations": requests,
                "tool_events": tools,
                "mcp_requests": mcp_log.read_text().splitlines()[before_mcp:],
                "payment_time_check": "payment_time" in json.loads(result["result"])["columns"],
            }
            return result["session_id"]
        def active_session():
            """Update project instructions while one CLI process keeps its session open."""
            instructions.write_bytes(material(D1))
            args = [cli, "-p", "--model", "claude-sonnet-4-6", "--allowedTools=Skill",
                    "--settings", str(settings), "--setting-sources", "project",
                    "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
            proc = subprocess.Popen(args, env=env, cwd=project, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, bufsize=1)
            frames = queue.Queue()
            def read():
                for line in proc.stdout:
                    if line.startswith("{"):
                        frames.put(json.loads(line))
                frames.put(None)
            threading.Thread(target=read, daemon=True).start()
            session = None
            try:
                for name, version, prompt in [
                    ("active-baseline", D1, "Return the order columns for C1."),
                    ("active-changed", D2, "Return the order columns for C2."),
                    ("active-supplement", D2, "Apply this approved decision: " + D2),
                ]:
                    instructions.write_bytes(material(version))
                    before = len(server.requests)
                    hook_offset = len(hook_file.read_text().splitlines())
                    frame = {"type": "user", "session_id": "", "parent_tool_use_id": None,
                             "message": {"role": "user", "content": prompt}}
                    proc.stdin.write(json.dumps(frame) + "\n")
                    proc.stdin.flush()
                    while True:
                        message = frames.get(timeout=30)
                        if message is None:
                            raise RuntimeError("Claude stream ended before a result")
                        if message["type"] == "result":
                            break
                    assert not message["is_error"], message
                    if session:
                        assert message["session_id"] == session
                    session = message["session_id"]
                    hooks = [json.loads(l) for l in hook_file.read_text().splitlines()[hook_offset:]]
                    loads = [h for h in hooks if h.get("file_path") == str(instructions)
                             and h["hook_event_name"] == "InstructionsLoaded"]
                    reqs = server.requests[before:]
                    assert len(reqs) == 1
                    result_rows[name] = {"disk_expected_match": True,
                                         "instruction_hook": [(h["memory_type"], h["load_reason"]) for h in loads],
                                         "request_marker_locations": reqs, "explicit_supplement": name == "active-supplement",
                                         "payment_time_check": "payment_time" in json.loads(message["result"])["columns"]}
            finally:
                proc.stdin.close()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                proc.stdout.close()

        try:
            run("fresh", D2, D2)
            original = run("baseline", D1, D1)
            restored = run("restored", D2, D2, resume=original)
            assert restored == original
            run("stale", D1, D2)
            run("absent", None, D2)
            run("invoke", D2, D2, invoke="Skill")
            run("mcp-discover", D2, D2, with_mcp=True)
            run("mcp-call", D2, D2, invoke=MCP_TOOL, with_mcp=True)
            active_session()
            materializer = os.environ.get("AP_CONTEXT_MATERIALIZER")
            if materializer:
                instructions.unlink(missing_ok=True)
                subprocess.run([materializer, str(project), "claude", D2], cwd=project, check=True,
                               capture_output=True, text=True, timeout=20)
                run("multica-materialized", None, D2, pre_materialized=True)
        finally:
            server.shutdown()
    verify(result_rows)
    print(json.dumps({"cli_processes": len(result_rows) - 2, "user_turns": len(result_rows),
                      "model_requests": len(server.requests), "results": result_rows}, indent=2))
    return result_rows


def verify(rows):
    def first(name):
        return rows[name]["request_marker_locations"][0]

    def message_positions(paths):
        return [int(re.match(r"messages\[(\d+)\]", path).group(1)) for path in paths]

    # Disk hash agreement, per-load witness, and membership in this actual request are separate.
    assert rows["fresh"]["disk_expected_match"] and first("fresh")[D2] and not first("fresh")[D1]
    assert not rows["stale"]["disk_expected_match"] and first("stale")[D1] and not first("stale")[D2]
    assert rows["fresh"]["instruction_hook"] == rows["stale"]["instruction_hook"] == [("Project", "session_start")]
    assert not rows["absent"]["disk_expected_match"] and not rows["absent"]["instruction_hook"]
    assert not first("absent")[D2] and not first("absent")[D1]
    assert first("baseline")[D1] and not first("baseline")[D2]
    resumed = first("restored")
    assert rows["restored"]["disk_expected_match"] and rows["restored"]["instruction_hook"]
    assert max(message_positions(resumed[D1])) < min(message_positions(resumed[D2]))

    # Discovery, actual invocation, and seeing the body/result after the tool are separate.
    assert first("fresh")[SKILL_DESC] and not first("fresh")[SKILL_BODY] and not rows["fresh"]["tool_events"]
    skill = rows["invoke"]
    assert not first("invoke")[SKILL_BODY] and skill["request_marker_locations"][1][SKILL_BODY]
    assert set(skill["tool_events"]) == {("PreToolUse", "toolu_order_skill", SKILL_NAME),
                                          ("PostToolUse", "toolu_order_skill", SKILL_NAME)}
    discovery, calls = rows["mcp-discover"], rows["mcp-call"]
    assert {"initialize", "tools/list"} <= set(discovery["mcp_requests"])
    assert "tools/call" not in discovery["mcp_requests"] and not discovery["tool_events"]
    assert any(path.startswith("tools[") for path in first("mcp-discover")[MCP_TOOL])
    assert {"initialize", "tools/list", "tools/call"} <= set(calls["mcp_requests"])
    assert set(calls["tool_events"]) == {("PreToolUse", "toolu_order_mcp", None),
                                         ("PostToolUse", "toolu_order_mcp", None)}
    assert not first("mcp-call")[MCP_RESULT] and calls["request_marker_locations"][1][MCP_RESULT]
    assert first("active-baseline")[D1] and not first("active-baseline")[D2]
    # This tests the immediately following plain turn, without a reload command or new process.
    assert rows["active-changed"]["disk_expected_match"] and not rows["active-changed"]["instruction_hook"]
    assert first("active-changed")[D1] and not first("active-changed")[D2]
    supplied = first("active-supplement")
    assert not rows["active-supplement"]["instruction_hook"]
    assert max(message_positions(supplied[D1])) < min(message_positions(supplied[D2]))
    if "multica-materialized" in rows:
        row = rows["multica-materialized"]
        assert row["disk_sha256"] and row["instruction_hook"] == [("Project", "session_start")]
        assert first("multica-materialized")[D2] and not first("multica-materialized")[D1]
    assert not any(row["payment_time_check"] for row in rows.values())


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "hook":
        hook(Path(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "mcp":
        mcp_fixture(Path(sys.argv[2]))
    elif len(sys.argv) == 2:
        with tempfile.TemporaryDirectory(prefix="claude-context-") as tmp:
            run_probe(str(Path(sys.argv[1]).resolve()), Path(tmp))
    else:
        sys.exit("Usage: python3 claude-context-probe.py /path/to/claude")
