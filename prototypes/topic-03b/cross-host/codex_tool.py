"""Exercise one read-only MCP tool through a real Codex 0.144.6 App Server."""
import argparse
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "topic-03a"))
client = import_module("codex-context-probe").client


class OrderEndpoint(BaseHTTPRequestHandler):
    """The first response requests the project's tool; the next ends the same native turn."""
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        server = self.server
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        server.requests.append(json.loads(raw))
        server.wire_hashes.append(sha256(raw).hexdigest())
        n = len(server.requests)
        if n == 1:
            if server.before_call is not None:
                server.before_call()
            item = {"type": "function_call", "id": "fc_order", "call_id": server.call_id,
                    "namespace": "mcp__" + server.model_server, "name": server.case["tool"],
                    "arguments": json.dumps(server.case["arguments"])}
        elif n == 2:
            item = {"type": "message", "role": "assistant", "id": "msg_order", "content": [
                {"type": "output_text", "text": "Recorded the tool response."}]}
        else:
            self.send_error(409, "expected two model requests")
            return
        rid = f"response_fixture_{n}"
        events = [{"type": "response.created", "response": {"id": rid}},
                  {"type": "response.output_item.done", "item": item},
                  {"type": "response.completed", "response": {"id": rid}}]
        payload = "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def configuration(work, endpoint, servers):
    text = f'''model = "gpt-5.1-codex"
model_provider = "fixture"
project_doc_max_bytes = 0
[model_providers.fixture]
name = "fixture"
base_url = "http://127.0.0.1:{endpoint.server_port}/v1"
wire_api = "responses"
supports_websockets = false
requires_openai_auth = false
request_max_retries = 0
stream_max_retries = 0
[projects.{json.dumps(str(work))}]
trust_level = "trusted"
[analytics]
enabled = false
'''
    for name, spec in servers.items():
        if re.fullmatch(r"[a-z][a-z0-9_]*", name) is None:
            raise ValueError("invalid synthetic MCP alias")
        text += f"\n[mcp_servers.{name}]\ncommand = {json.dumps(spec['command'])}\nargs = {json.dumps(spec['args'])}\n"
    return text


def tool_catalog(rpc, thread):
    servers = {}
    params = {"threadId": thread, "limit": 25}
    while True:
        page = rpc.call("mcpServerStatus/list", params)
        for row in page["data"]:
            if row["name"] in servers:
                raise ValueError("duplicate MCP status row")
            servers[row["name"]] = row
        if not page.get("nextCursor"):
            return servers
        params["cursor"] = page["nextCursor"]


def mcp_functions(envelope):
    return {f"{ns['name']}.{f['name']}" for ns in envelope["tools"]
            if ns["type"] == "namespace" and ns["name"].startswith("mcp__")
            for f in ns["tools"] if f["type"] == "function"}


def verify_return(endpoint, thread, turn, items, notifications, case, prompt):
    assert len(endpoint.requests) == 2
    first, second = endpoint.requests
    server, tool, args = case["expected_server"], case["tool"], case["arguments"]
    requested = endpoint.model_server
    offered = "mcp__" + server + "." + tool
    for req in (first, second):
        assert mcp_functions(req) == {offered}
    assert any(m.get("role") == "user" and any(p.get("text") == prompt for p in m["content"]) for m in first["input"])
    assert not any(m.get("type") in {"function_call", "function_call_output"} for m in first["input"])
    calls = [i for i in second["input"] if i.get("type") == "function_call"]
    outputs = [i for i in second["input"] if i.get("type") == "function_call_output"]
    assert len(calls) == len(outputs) == 1
    call, output = calls[0], outputs[0]
    assert (call["call_id"], call["namespace"], call["name"], json.loads(call["arguments"])) == (
        endpoint.call_id, "mcp__" + requested, tool, args)
    assert output["call_id"] == call["call_id"] and second["input"].index(call) < second["input"].index(output)
    common = {"status": "completed", "thread_id": thread, "turn_id": turn, "model_requests": 2,
              "call_id": call["call_id"], "arguments": args, "selected_tool": f"mcp__{requested}.{tool}",
              "offered_tools": sorted(mcp_functions(first)), "wire_request_sha256": endpoint.wire_hashes,
              "wire_tool_output_index": second["input"].index(output)}
    if requested != server:
        assert [i["type"] for i in items] == ["userMessage", "agentMessage"] and not notifications
        assert output["output"] == f"unsupported call: mcp__{requested}{tool}"
        return {**common, "result": {"status": "host_rejected"}, "native_status": "no MCP item",
                "host_rejection": output["output"], "result_sha256": None}
    assert [i["type"] for i in items] == ["userMessage", "mcpToolCall", "agentMessage"]
    native = items[1]
    notification, = notifications
    # This pinned client renders MCP content as an array following its measured wall time.
    header, separator, body = output["output"].partition("\nOutput:\n")
    assert separator and header.startswith("Wall time: ")
    content = json.loads(body)
    assert len(content) == 1 and content[0]["type"] == "text" and content == native["result"]["content"]
    text = content[0]["text"]
    result = json.loads(text)
    assert (native["id"], native["server"], native["tool"], native["arguments"]) == (endpoint.call_id, server, tool, args)
    assert notification["threadId"] == thread and notification["turnId"] == turn and notification["item"] == native
    assert native["status"] == ("completed" if result.get("status") == "ok" else "failed")
    return {**common, "result": result, "result_sha256": sha256(text.encode()).hexdigest(), "native_status": native["status"]}


def run_codex(binary, case, before_call=None):
    binary = shutil.which(str(binary))
    if not binary or subprocess.check_output([binary, "--version"], text=True).strip() != "codex-cli 0.144.6":
        raise ValueError("requires codex-cli 0.144.6")
    with tempfile.TemporaryDirectory() as temp, ThreadingHTTPServer(("127.0.0.1", 0), OrderEndpoint) as endpoint:
        work, home = Path(temp) / "work", Path(temp) / "home"
        work.mkdir()
        home.mkdir()
        (home / "config.toml").write_text(configuration(work, endpoint, case["servers"]))
        endpoint.case, endpoint.before_call = case, before_call
        endpoint.model_server = case.get("model_request_server", case["expected_server"])
        if endpoint.model_server not in (case["expected_server"], "personal_orders"):
            raise ValueError("unknown model request control")
        endpoint.call_id = "order-" + uuid.uuid4().hex
        endpoint.requests, endpoint.wire_hashes = [], []
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            with client(binary, home, work) as rpc:
                start = {"cwd": str(work), "sandbox": "read-only", "approvalPolicy": "on-request"}
                inventory = rpc.call("thread/start", start)["thread"]["id"]
                def inspect_catalog(t):
                    rows = tool_catalog(rpc, t)
                    names = {alias: sorted(row["tools"]) for alias, row in rows.items()}
                    descriptor = rows.get(server, {}).get("tools", {}).get(tool)
                    return names, descriptor

                def blocked(receipt, reason):
                    assert not endpoint.requests
                    return {**receipt, "status": "blocked", "reason": reason, "thread_id": None,
                            "turn_id": None, "model_requests": 0, "selected_tool": None, "call_id": None,
                            "arguments": None, "result": None, "offered_tools": []}

                server, tool = case["expected_server"], case["tool"]
                catalog, descriptor = inspect_catalog(inventory)
                common = {"id": case["id"], "binding": case["binding"], "host": "codex-cli 0.144.6",
                          "configured_catalog": catalog}
                if descriptor is None:
                    return blocked(common, "required project tool unavailable")
                schema = descriptor["inputSchema"]
                common["observed_input_schema"] = schema
                if case.get("expected_input_schema", schema) != schema:
                    return blocked(common, "required tool schema mismatch")
                # Keep local servers in the member's config, constrain the actual business thread.
                overrides = {f"mcp_servers.{name}.enabled": False for name in catalog if name != server}
                overrides[f"mcp_servers.{server}.enabled_tools"] = [tool]
                thread = rpc.call("thread/start", {**start, "config": overrides})["thread"]["id"]
                active, current_descriptor = inspect_catalog(thread)
                common["active_catalog"] = active
                if (current_descriptor is None or current_descriptor["inputSchema"] != schema
                        or {n: t for n, t in active.items() if t} != {server: [tool]}):
                    return blocked(common, "active MCP surface changed before turn")
                prompt = ("Check the authorized order workbooks for the following issued binding. "
                          + json.dumps(case["binding"], ensure_ascii=False, sort_keys=True))
                turn = rpc.call("turn/start", {"threadId": thread, "input": [{"type": "text", "text": prompt}]})["turn"]["id"]
                done = rpc.wait(lambda m: m.get("method") == "turn/completed" and m["params"]["turn"]["id"] == turn)
                history = rpc.call("thread/read", {"threadId": thread, "includeTurns": True})["thread"]["turns"]
                assert len(history) == 1 and history[0]["id"] == turn
                assert history[0]["status"] == done["params"]["turn"]["status"] == "completed"
                items = history[0]["items"]
                notifications = [m["params"] for m in rpc.seen if m.get("method") == "item/completed"
                                 and m["params"]["item"]["type"] == "mcpToolCall"]
                return {**common, **verify_return(endpoint, thread, turn, items, notifications, case, prompt)}
        finally:
            endpoint.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    params = parser.parse_args()
    report = run_codex(params.codex, json.loads(params.case.read_bytes()))
    params.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
