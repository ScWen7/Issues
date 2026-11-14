"""Observe home or project rules in real Codex model-bound requests.

Run beside codex_observation_probe.py. Pass "project" for the Multica path.
For this channel, AP_CONTEXT_MATERIALIZER can point to the upstream writer.
"""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading

from codex_observation_probe import AppServer


D1 = "ap3-fixture-D1-basic-columns"
D2 = "ap3-fixture-D2-payment-time"
SKILL = "ap3-fixture-skill-body-A2"
REMOVE = "The previously provided AGENTS.md instructions no longer apply."
REPLACE = "These AGENTS.md instructions replace all previously provided AGENTS.md instructions."


class CapturingEndpoint(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.inputs.append(body["input"])
        self.server.requests += 1
        number = self.server.requests
        rid = f"resp_fixture_{number}"
        if self.server.ask_mcp:
            self.server.ask_mcp = False
            item = {"type": "function_call", "id": "fc_fixture", "call_id": "order-probe-call",
                    "name": "inspect_report", "namespace": "mcp__order_fixture", "arguments": "{}"}
        else:
            item = {"type": "message", "role": "assistant", "id": f"msg_{number}",
                    "content": [{"type": "output_text", "text": "fixture response"}]}
        events = [
            {"type": "response.created", "response": {"id": rid}},
            {"type": "response.output_item.done", "item": item},
            {"type": "response.completed", "response": {"id": rid, "usage": {
                "input_tokens": 8, "output_tokens": 4, "total_tokens": 12}}},
        ]
        wire = "".join(f"data: {json.dumps(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(wire)))
        self.end_headers()
        self.wfile.write(wire)


def text_items(items):
    for item in items:
        for part in item.get("content", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                yield item.get("role"), part["text"]


def mcp_fixture(log):
    def record(method):
        with log.open("a") as stream:
            stream.write(method + "\n")

    for line in sys.stdin:
        request = json.loads(line)
        method = request.get("method")
        if "id" not in request:
            continue
        record(method)
        if method == "initialize":
            result = {"protocolVersion": request["params"]["protocolVersion"],
                      "serverInfo": {"name": "order-receipt", "version": "1"}, "capabilities": {"tools": {}}}
        elif method == "tools/list":
            result = {"tools": [{"name": "inspect_report", "description": "Read fixture report identity",
                                 "annotations": {"readOnlyHint": True}, "inputSchema": {"type": "object", "properties": {}}}]}
        elif method == "tools/call" and request["params"]["name"] == "inspect_report":
            result = {"content": [{"type": "text", "text": "synthetic-candidate-C2"}], "isError": False}
        else:
            result = {}
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)


@contextmanager
def client(binary, home, project):
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "CODEX_HOME": str(home),
           "NO_PROXY": "127.0.0.1,localhost", "HTTP_PROXY": "http://127.0.0.1:1",
           "HTTPS_PROXY": "http://127.0.0.1:1"}
    with (home / "stderr.log").open("a") as err:
        rpc = AppServer(binary, project, env, err)
        try:
            rpc.call("initialize", {"clientInfo": {"name": "contextfixture", "version": "1"},
                                    "capabilities": {"experimentalApi": True}})
            rpc.send("initialized", {})
            yield rpc
        finally:
            rpc.close()


def probe(home, project, endpoint, binary, channel, version):
    live_baselines = {
        ("codex-cli 0.144.6", "home"): False,
        ("codex-cli 0.144.6", "project"): False,
        ("codex-cli 0.167.0-alpha.4", "home"): True,
    }
    baseline = live_baselines.get((version, channel))
    review = []
    print("Probe mode:", "exploration" if baseline is None else "regression", version, channel)

    def compare(label, actual, expected, recognized):
        if baseline is not None:
            assert actual == expected, (label, actual, expected)
        elif actual not in recognized:
            review.append(label)
            print("Review unfamiliar observation:", label, json.dumps(actual))

    log = home / "mcp-calls.log"
    skill = project / ".agents/skills/order-a2/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: order-a2\ndescription: Order fixture validator.\n---\n" + SKILL)
    guide = (project if channel == "project" else home) / "AGENTS.md"
    def write_guide(marker):
        materializer = os.environ.get("AP_CONTEXT_MATERIALIZER")
        if materializer and channel == "project":
            subprocess.run([materializer, str(project), "codex", marker], check=True, stdout=subprocess.DEVNULL)
            assert marker in guide.read_text()
        else:
            guide.write_text(marker)

    (home / "config.toml").write_text(f'''model = "gpt-5.1-codex"
model_provider = "fixture"
project_doc_max_bytes = {32768 if channel == "project" else 0}
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
[mcp_servers.order_fixture]
command = {json.dumps(sys.executable)}
args = {json.dumps([str(Path(__file__).resolve()), "mcp", str(log)])}
[analytics]
enabled = false
''')

    def start(rpc):
        return rpc.call("thread/start", {"cwd": str(project), "approvalPolicy": "on-request",
                                        "sandbox": "read-only"})["thread"]["id"]

    def turn(rpc, thread, label, extra=(), requests=1):
        before = len(endpoint.inputs)
        inputs = [{"type": "text", "text": "fixture-turn-" + label}, *extra]
        tid = rpc.call("turn/start", {"threadId": thread, "input": inputs})["turn"]["id"]
        done = rpc.wait(lambda m: m.get("method") == "turn/completed" and m["params"]["turn"]["id"] == tid)
        assert done["params"]["turn"]["status"] == "completed", done
        assert len(endpoint.inputs) == before + requests, label
        observations = []
        for role, body in text_items(endpoint.inputs[-1]):
            found = [name for name, marker in (("D1", D1), ("D2", D2), ("replace", REPLACE),
                                               ("remove", REMOVE), ("skill", SKILL)) if marker in body]
            if found:
                observations.append((role, found))
        print(label, json.dumps(observations))
        return observations

    with client(binary, home, project) as rpc:
        write_guide(D2)
        fresh = start(rpc)
        assert turn(rpc, fresh, "fresh-D2") == [("user", ["D2"])]
        listed = rpc.call("skills/list", {"cwds": [str(project)]})
        assert any(s["name"] == "order-a2" and s["enabled"] and s["path"] == str(skill)
                   for row in listed["data"] for s in row["skills"])
        result = turn(rpc, fresh, "picked-skill", [{"type": "skill", "name": "order-a2", "path": str(skill)}])
        assert any("skill" in names for _, names in result)
        status = rpc.call("mcpServerStatus/list", {"threadId": fresh, "serverName": "order_fixture"})
        print("MCP status", [(x["name"], x.get("runtimeStatus"), list(x["tools"])) for x in status["data"]])
        assert "inspect_report" in status["data"][0]["tools"]
        assert {"initialize", "tools/list"}.issubset(log.read_text().splitlines())
        assert "tools/call" not in log.read_text().splitlines()
        called = rpc.call("mcpServer/tool/call", {"threadId": fresh, "server": "order_fixture", "tool": "inspect_report", "arguments": {}})
        assert called["content"][0]["text"] == "synthetic-candidate-C2" and not called.get("isError")
        assert log.read_text().splitlines().count("tools/call") == 1
        endpoint.ask_mcp = True
        turn(rpc, fresh, "turn-mcp-call", requests=2)
        outputs = [i for i in endpoint.inputs[-1] if i.get("type") == "function_call_output"]
        print("MCP result", [(i.get("call_id"), i.get("output")) for i in outputs])
        assert any(i.get("call_id") == "order-probe-call"
                   and "synthetic-candidate-C2" in str(i.get("output")) for i in outputs)
        assert log.read_text().splitlines().count("tools/call") == 2
        write_guide(D1)
        old = start(rpc)
        assert turn(rpc, old, "fresh-D1") == [("user", ["D1"])]
        write_guide(D2)
        old_only = [("user", ["D1"])]
        replaced = old_only + [("user", ["D2", "replace"])]
        for action in ("same-live-thread", "resume-live-thread"):
            if action == "resume-live-thread":
                assert rpc.call("thread/resume", {"threadId": old})["thread"]["id"] == old
            observed = turn(rpc, old, action)
            compare(action, observed, replaced if baseline else old_only, [old_only, replaced])
    with client(binary, home, project) as rpc:
        assert rpc.call("thread/resume", {"threadId": old})["thread"]["id"] == old
        observed = turn(rpc, old, "resume-new-process")
        compare("resume-new-process", observed, replaced, [old_only, replaced])
    guide.unlink()
    with client(binary, home, project) as rpc:
        assert rpc.call("thread/resume", {"threadId": old})["thread"]["id"] == old
        removed = [("user", ["remove"])]
        observed = turn(rpc, old, "resume-file-removed")
        compare("resume-file-removed", observed, replaced + removed,
                [old_only, replaced, old_only + removed, replaced + removed])
        assert turn(rpc, start(rpc), "fresh-file-missing") == []
        # A new managed input can deliver the current contract on a stale thread.
        # Use a separate fresh thread so it cannot change the history of the resume test above.
        write_guide(D1)
        stale = start(rpc)
        assert turn(rpc, stale, "before-explicit-correction") == old_only
        write_guide(D2)
        correction = "Contract update for this turn: " + D2
        turn(rpc, stale, "explicit-correction", [{"type": "text", "text": correction}])
        texts = [text for role, text in text_items(endpoint.inputs[-1]) if role == "user"]
        assert any(correction in text for text in texts)
        if baseline is not None:
            assert any(D1 in text for text in texts)
        file_d2 = any(D2 in text and correction not in text for text in texts)
        print("Explicit current-turn contract contains D2; refreshed file block:", file_d2)
        compare("explicit-correction-file-refresh", file_d2, baseline, [False, True])
    assert endpoint.requests == 12
    print("Model requests", endpoint.requests)
    if review:
        print("Evidence to review:", ", ".join(review))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "mcp":
        mcp_fixture(Path(sys.argv[2]))
        return
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] not in {"home", "project"}):
        raise SystemExit("Usage: python3 codex-context-probe.py [home|project]")
    binary = shutil.which("codex")
    if not binary:
        raise SystemExit("Requires codex-cli on PATH")
    version = subprocess.check_output([binary, "--version"], text=True).strip()
    print(version)
    with tempfile.TemporaryDirectory(prefix="codex-context-") as temp:
        home, project = Path(temp) / "home", Path(temp) / "project"
        home.mkdir()
        project.mkdir()
        subprocess.run(["git", "init", "-q", str(project)], check=True)
        with ThreadingHTTPServer(("127.0.0.1", 0), CapturingEndpoint) as endpoint:
            endpoint.requests, endpoint.inputs, endpoint.ask_mcp = 0, [], False
            threading.Thread(target=endpoint.serve_forever, daemon=True).start()
            try:
                probe(home, project, endpoint, binary, sys.argv[1] if len(sys.argv) == 2 else "home", version)
            finally:
                endpoint.shutdown()


if __name__ == "__main__":
    main()
