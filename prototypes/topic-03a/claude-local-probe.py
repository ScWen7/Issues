"""Exercise a real Claude Code CLI against a local, deterministic Messages endpoint.

Usage: python claude-local-probe.py /path/to/claude
Only Python's standard library and the Claude Code binary are required.
The fixture uses synthetic prompts, a temporary Claude config, and a local test key.
"""

import json
import os
import shlex
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def capture_hook(output):
    event = json.load(sys.stdin)
    with Path(output).open("a") as dest:
        dest.write(json.dumps(event) + "\n")


class MessagesFixture(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/v1/logs":
            for resource in payload["resourceLogs"]:
                for scope in resource["scopeLogs"]:
                    for record in scope["logRecords"]:
                        self.server.telemetry.append({
                            a["key"]: next(iter(a["value"].values())) for a in record["attributes"]
                        })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        if self.path.split("?")[0] != "/v1/messages" or not payload.get("stream"):
            self.send_error(404)
            return
        self.server.call_number += 1
        number = self.server.call_number
        # The third scenario's initial request asks the real CLI to read a local file.
        if number == 3:
            block = {"type": "tool_use", "id": "toolu_fixture_read", "name": "Read", "input": {}}
            delta = {"type": "input_json_delta", "partial_json": json.dumps({"file_path": str(self.server.artifact)})}
            reason = "tool_use"
        else:
            block = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": f"fixture response {number}"}
            reason = "end_turn"
        message = {
            "type": "message", "id": f"msg_fixture_{number}", "model": payload["model"],
            "role": "assistant", "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 10, "output_tokens": 0, "cache_read_input_tokens": 0,
                      "cache_creation_input_tokens": 0},
        }
        events = [
            {"type": "message_start", "message": message},
            {"type": "content_block_start", "index": 0, "content_block": block},
            {"type": "content_block_delta", "index": 0, "delta": delta},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": reason, "stop_sequence": None},
             "usage": {"output_tokens": 4}},
            {"type": "message_stop"},
        ]
        data = "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("request-id", f"req_fixture_{number}")
        self.end_headers()
        self.wfile.write(data)


def run_probe(cli, temp):
    project = temp / "project"
    config = temp / "config"
    project.mkdir()
    config.mkdir()
    hooks_path = temp / "hooks.jsonl"
    hooks_path.touch()
    settings = temp / "settings.json"
    command = shlex.join([sys.executable, str(Path(__file__).resolve()), "hook", str(hooks_path)])
    events = ["SessionStart", "UserPromptSubmit", "MessageDisplay", "PreToolUse", "PostToolUse",
              "PostToolUseFailure", "Stop", "SessionEnd"]
    settings.write_text(json.dumps({"hooks": {e: [{"hooks": [{"type": "command", "command": command}]}]
                                                 for e in events}}))
    with ThreadingHTTPServer(("127.0.0.1", 0), MessagesFixture) as server:
        server.telemetry = []
        server.call_number = 0
        server.artifact = project / "order-check.txt"
        server.artifact.write_text("fixture artifact selected by member\n")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        env = {
            "PATH": os.environ["PATH"], "HOME": str(config), "CLAUDE_CONFIG_DIR": str(config),
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}",
            "CLAUDE_CODE_ENABLE_TELEMETRY": "1", "OTEL_LOGS_EXPORTER": "otlp",
            "OTEL_METRICS_EXPORTER": "none", "OTEL_EXPORTER_OTLP_PROTOCOL": "http/json",
            "OTEL_LOGS_EXPORT_INTERVAL": "100",
            "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": f"http://127.0.0.1:{server.server_port}/v1/logs",
            "ANTHROPIC_API_KEY": "test-local-only", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1", "DISABLE_AUTOUPDATER": "1", "NO_COLOR": "1",
        }

        def run(prompt, *extra):
            before = len(read_jsonl(hooks_path))
            args = [cli, "-p", "--model", "claude-sonnet-4-6", "--allowedTools=Read", "--settings",
                    str(settings), "--setting-sources", "", "--output-format", "stream-json",
                    "--verbose", *extra, prompt]
            proc = subprocess.run(args, env=env, cwd=project, capture_output=True, text=True, timeout=45)
            if proc.returncode:
                raise RuntimeError(f"Claude CLI exited {proc.returncode}: {proc.stderr.strip()}")
            frames = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
            hooks = read_jsonl(hooks_path)[before:]
            result = next(f for f in frames if f["type"] == "result")
            assert result["subtype"] == "success" and not result["is_error"]
            return frames, {e["hook_event_name"]: e for e in hooks}, result

        try:
            f1, h1, r1 = run("FIRST")
            f2, h2, r2 = run("SECOND", "--resume", r1["session_id"])
            assert r1["session_id"] == r2["session_id"]
            assert [h1["SessionStart"]["source"], h2["SessionStart"]["source"]] == ["startup", "resume"]
            assert h1["Stop"]["prompt_id"] != h2["Stop"]["prompt_id"]
            history = read_jsonl(Path(h2["Stop"]["transcript_path"]))
            for frames, hooks, result in [(f1, h1, r1), (f2, h2, r2)]:
                assistant = next(f for f in frames if f["type"] == "assistant")
                prompt = hooks["UserPromptSubmit"]
                display = hooks["MessageDisplay"]
                stored_user = next(e for e in history if e.get("type") == "user"
                                   and e.get("message", {}).get("content") == prompt["prompt"])
                stored_response = next(e for e in history if e.get("uuid") == assistant["uuid"])
                assert stored_response["message"]["id"] == assistant["message"]["id"]
                assert prompt["prompt_id"] == hooks["Stop"]["prompt_id"] == display["prompt_id"]
                assert len({prompt["prompt_id"], stored_user["uuid"], display["turn_id"]}) == 3
                assert len({display["message_id"], assistant["message"]["id"], assistant["uuid"]}) == 3
                assert assistant["message"]["usage"]["output_tokens"] == 0
                assert (result["usage"]["input_tokens"], result["usage"]["output_tokens"]) == (10, 4)
            assert r1["total_cost_usd"] > 0
            assert abs(r2["total_cost_usd"] - 2 * r1["total_cost_usd"]) < 1e-12
            f3, h3, r3 = run("Read the local fixture.")
            assert r3["session_id"] != r2["session_id"]
            assert h3["PreToolUse"]["tool_use_id"] == h3["PostToolUse"]["tool_use_id"] == "toolu_fixture_read"
            assert "fixture artifact selected by member" in json.dumps(h3["PostToolUse"]["tool_response"])
            assert any(b.get("tool_use_id") == "toolu_fixture_read" for f in f3 if f["type"] == "user"
                       for b in f["message"]["content"])
            assert r3["num_turns"] == 2 and r3["usage"]["output_tokens"] == 8
            requests = {e["request_id"]: e for e in server.telemetry if e["event.name"] == "api_request"}
            responses = {e["request_id"]: e for e in server.telemetry if e["event.name"] == "assistant_response"}
            for number, (frames, hooks) in enumerate([(f1, h1), (f2, h2)], start=1):
                req_id = f"req_fixture_{number}"
                prompt_id = hooks["UserPromptSubmit"]["prompt_id"]
                assistant_id = next(f["uuid"] for f in frames if f["type"] == "assistant")
                assert requests[req_id]["prompt.id"] == responses[req_id]["prompt.id"] == prompt_id
                assert responses[req_id]["message.uuid"] == assistant_id
            assert len(requests) == server.call_number == 4
            assert sum(e["output_tokens"] for e in requests.values()) == 16
            print(json.dumps({"passed": ["session_resume", "distinct_id_namespaces", "transcript_match",
                                         "output_placeholder", "cumulative_cost", "tool_result_join", "otel_usage_join"],
                              "cli_processes": 3, "fixture_api_requests": server.call_number,
                              "estimates_usd": [r1["total_cost_usd"], r2["total_cost_usd"]],
                              "host_read_confirmed": True}, indent=2))
        finally:
            server.shutdown()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "hook":
        capture_hook(sys.argv[2])
    elif len(sys.argv) == 2:
        with tempfile.TemporaryDirectory(prefix="claude-local-probe-") as tmp:
            run_probe(str(Path(sys.argv[1]).resolve()), Path(tmp))
    else:
        sys.exit("Usage: python claude-local-probe.py /path/to/claude")
