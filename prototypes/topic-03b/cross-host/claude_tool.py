"""Exercise Claude Code's native control, Messages, and stdio MCP paths on one dispatch."""
import argparse
from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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
import time
from uuid import uuid4


def plain(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(text):
    return sha256(text.encode()).hexdigest()


def write_hook(path):
    event = json.load(sys.stdin)
    record = {k: event[k] for k in ("hook_event_name", "session_id", "prompt_id", "tool_use_id", "tool_name") if k in event}
    with path.open("a") as out:
        out.write(plain(record) + "\n")


class Messages(BaseHTTPRequestHandler):
    """Only an explicitly scripted tool_use and final acknowledgement are generated."""
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path.split("?")[0] != "/v1/messages":
            self.send_error(404)
            return
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        payload = json.loads(raw)
        self.server.received.append(payload)
        self.server.hashes.append(sha256(raw).hexdigest())
        count = len(self.server.received)
        if count == 1:
            try:
                offered = {tool["name"]: tool for tool in payload["tools"]}
                assert self.server.target in offered and self.server.denied.isdisjoint(offered)
                if self.server.input_schema is not None and offered[self.server.target]["input_schema"] != self.server.input_schema:
                    raise ValueError("model-facing schema differs from the issued order tool")
                if self.server.before_call is not None:
                    self.server.before_call()
            except Exception as error:
                self.server.callback_error = error
        if count == 1 and self.server.callback_error is None:
            block = {"type": "tool_use", "name": self.server.tool, "id": self.server.call_id, "input": {}}
            delta = {"type": "input_json_delta", "partial_json": plain(self.server.arguments)}
            stop = "tool_use"
        else:
            block = {"type": "text", "text": ""}
            delta = {"type": "text_delta", "text": "Order inspection response received."}
            stop = "end_turn"
        events = [
            {"type": "message_start", "message": {
                "id": f"msg_{self.server.run_id}_{count}", "type": "message", "role": "assistant", "model": payload["model"],
                "content": [], "stop_reason": None, "stop_sequence": None, "usage": {"input_tokens": 10, "output_tokens": 0}}},
            {"type": "content_block_start", "index": 0, "content_block": block},
            {"type": "content_block_delta", "index": 0, "delta": delta},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": stop, "stop_sequence": None}, "usage": {"output_tokens": 4}},
            {"type": "message_stop"},
        ]
        body = "".join(f"event: {e['type']}\ndata: {plain(e)}\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@contextmanager
def stream(args, env, cwd):
    proc = subprocess.Popen(args, env=env, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, bufsize=1)
    messages = queue.Queue()

    def pump():
        try:
            for line in proc.stdout:
                messages.put(json.loads(line))
        finally:
            messages.put(None)

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()

    def send(obj):
        proc.stdin.write(plain(obj) + "\n")
        proc.stdin.flush()

    def receive():
        frame = messages.get(timeout=45)
        if frame is None:
            raise RuntimeError(f"Claude stream stopped before the expected response (exit {proc.poll()})")
        return frame

    try:
        yield send, receive
    finally:
        proc.stdin.close()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)
        proc.stdout.close()


def inspect_servers(send, receive, configured):
    def control(subtype):
        request_id = uuid4().hex
        send({"type": "control_request", "request_id": request_id, "request": {"subtype": subtype}})
        while True:
            frame = receive()
            if frame["type"] == "control_response" and frame["response"]["request_id"] == request_id:
                assert frame["response"]["subtype"] == "success"
                return frame["response"]["response"]

    assert control("initialize")["claude_code_version"] == "2.1.325"
    deadline = time.monotonic() + 15
    while True:
        statuses = control("mcp_status")["mcpServers"]
        observed = {s["name"]: s for s in statuses}
        if configured <= observed.keys() and all(s["status"] != "pending" for s in statuses):
            return observed
        if time.monotonic() >= deadline:
            return observed
        time.sleep(.05)


def finish(received, frames, hooks, target, server, case, offered, baseline):
    if server.callback_error:
        raise server.callback_error
    assert len(received) == 2 and frames[-1]["subtype"] == "success"
    assert {h["session_id"] for h in hooks} == {frames[-1]["session_id"]}
    start, = [h for h in hooks if h["hook_event_name"] == "UserPromptSubmit"]
    stop, = [h for h in hooks if h["hook_event_name"] == "Stop"]
    assert start["prompt_id"] and start["prompt_id"] == stop["prompt_id"]
    wire_tools = [t["name"] for t in received[0]["tools"]]
    assert target in wire_tools and not ((set(offered) - {target}) & set(wire_tools))
    tool_schema, = [t["input_schema"] for t in received[0]["tools"] if t["name"] == target]
    if "expected_input_schema" in case:
        assert tool_schema == case["expected_input_schema"], "offered MCP schema differs from the release"
    call_id = server.call_id
    out = []
    for i, message in enumerate(received[1]["messages"]):
        for j, block in enumerate(message["content"] if isinstance(message["content"], list) else []):
            if block.get("type") == "tool_result" and block.get("tool_use_id") == call_id:
                out.append((f"messages[{i}].content[{j}]", block))
    (path, result_block), = out
    native_call, = [b for f in frames if f["type"] == "assistant" for b in f["message"]["content"]
                    if b["type"] == "tool_use" and b["id"] == call_id]
    native_result, = [b for f in frames if f["type"] == "user" for b in f["message"]["content"]
                      if b["type"] == "tool_result" and b["tool_use_id"] == call_id]
    assert native_call["input"] == case["arguments"] and native_call["name"] == server.tool
    # This host can append a newline and an independent system-reminder to returned content.
    def text_items(content):
        return [content] if isinstance(content, str) else [item["text"] for item in content if item["type"] == "text"]
    text, = text_items(native_result["content"])
    model_texts = text_items(result_block["content"])
    matches = [i for i, item in enumerate(model_texts)
               if item in (text, text + "\n") or (item.startswith(text + "\n\n<system-reminder>\n")
                                                  and item.endswith("</system-reminder>"))]
    assert len(matches) == 1, "tool_result text changed en route to the next model request"
    index, = matches
    assert all(i == index or item.startswith("<system-reminder>") for i, item in enumerate(model_texts))
    path += f".content[{index}].text" if isinstance(result_block["content"], list) else ".content"
    is_error = bool(result_block.get("is_error", False))
    tool_hooks = [h for h in hooks if h.get("tool_use_id") == call_id]
    if server.tool != target:
        # A directed negative control may request a personal alias hidden by explicit deny.
        assert is_error and server.tool not in wire_tools and not tool_hooks
        assert "No such tool available: " + server.tool in text
        result = {"status": "host_rejected"}
    else:
        assert any(h["hook_event_name"] == "PreToolUse" and h["tool_name"] == target for h in tool_hooks)
        assert any(h["hook_event_name"] in ("PostToolUse", "PostToolUseFailure")
                   and h["tool_name"] == target for h in tool_hooks)
        result = json.loads(text)
    assert all(f["session_id"] == frames[-1]["session_id"] for f in frames if "session_id" in f)
    return {**baseline, "status": "completed", "model_requests": len(received), "selected_tool": server.tool,
            "call_id": call_id, "arguments": native_call["input"], "result": result, "is_error": is_error,
            "offered_schema_sha256": digest(plain(tool_schema)), "result_text_sha256": digest(text), "result_path": path, "wire_sha256": server.hashes,
            "offered_mcp": sorted(set(wire_tools) & set(offered)), "session_id": frames[-1]["session_id"],
            "prompt_id": start["prompt_id"], "tool_hooks": [h["hook_event_name"] for h in tool_hooks]}


def run_claude(binary, case, before_call=None):
    """Run one binding in a fresh member environment; connection preflight precedes any prompt."""
    binary = str(Path(binary).resolve())
    if subprocess.check_output([binary, "--version"], text=True).strip() != "2.1.325 (Claude Code)":
        raise ValueError("expected Claude Code 2.1.325")
    aliases, expected, leaf = case["servers"], case["expected_server"], case["tool"]
    if any(not re.fullmatch("[a-zA-Z0-9_]+", n) for n in (*aliases, expected, leaf)):
        raise ValueError("invalid fixture tool or server name")
    target = f"mcp__{expected}__{leaf}"
    requested = case.get("model_request_server", expected)
    with tempfile.TemporaryDirectory(prefix="order-claude-") as temporary, ThreadingHTTPServer(("127.0.0.1", 0), Messages) as endpoint:
        root = Path(temporary)
        home, work = root / "home", root / "project"
        home.mkdir()
        work.mkdir()
        log = root / "events.jsonl"
        log.touch()
        hook_command = shlex.join([sys.executable, str(Path(__file__).resolve()), "hook", str(log)])
        events = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop")
        settings = root / "settings.json"
        settings.write_text(plain({"hooks": {key: [{"hooks": [{"type": "command", "command": hook_command}]}] for key in events}}))
        native_config = root / "profile.json"
        native_config.write_text(plain({"mcpServers": aliases}))
        # The existing member worktree also declares a personal service under the expected project alias.
        # It points to this fixture's real personal server, not another copy of the authorized source.
        if "personal_orders" in aliases:
            (work / ".mcp.json").write_text(plain({"mcpServers": {expected: aliases["personal_orders"]}}))
        endpoint.received, endpoint.hashes, endpoint.callback_error = [], [], None
        endpoint.run_id = uuid4().hex
        endpoint.call_id = f"toolu_{endpoint.run_id}"
        endpoint.arguments, endpoint.tool, endpoint.before_call = case["arguments"], f"mcp__{requested}__{leaf}", before_call
        env = {"HOME": str(home), "CLAUDE_CONFIG_DIR": str(home), "PATH": os.environ["PATH"],
               "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{endpoint.server_port}", "ANTHROPIC_API_KEY": "fixture-loopback",
               "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
               "DISABLE_AUTOUPDATER": "1", "ENABLE_TOOL_SEARCH": "false", "NO_COLOR": "1"}
        args = [binary, "-p", "--model", "claude-sonnet-4-6", "--allowedTools=" + target,
                "--permission-prompts", "none", "--tools=", "--settings", str(settings), "--setting-sources", "project",
                "--strict-mcp-config", "--mcp-config", str(native_config),
                "--input-format", "stream-json", "--output-format", "stream-json", "--verbose"]
        denied_names = [f"mcp__{alias}__{leaf}" for alias in aliases if alias != expected]
        endpoint.target, endpoint.denied = target, set(denied_names)
        endpoint.input_schema = case.get("expected_input_schema")
        if denied_names:
            args.append("--disallowedTools=" + ",".join(denied_names))
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            with stream(args, env, work) as (send, receive):
                states = inspect_servers(send, receive, set(aliases))
                available = [f"mcp__{alias}__{tool['name']}" for alias, state in states.items()
                             if state["status"] == "connected" for tool in state.get("tools", [])]
                baseline = {"binding": case["binding"], "host": "Claude Code 2.1.325",
                            "discovered": sorted(available), "server_status": {n: s["status"] for n, s in states.items()}}
                if target not in available or expected not in aliases:
                    assert not endpoint.received and not log.read_text()
                    return {**baseline, "status": "blocked", "model_requests": 0, "selected_tool": None,
                            "call_id": None, "arguments": None, "result": None, "session_id": None, "prompt_id": None}
                state = states[expected]
                actual = state["config"]
                assert state["scope"] == "dynamic" and actual["type"] == "stdio"
                baseline["source"] = state["scope"]
                baseline["server_info"] = state.get("serverInfo", {})
                assert (actual["command"], actual["args"]) == (aliases[expected]["command"], aliases[expected].get("args", []))
                prompt = "Inspect this bound order candidate. " + plain(case["binding"])
                send({"type": "user", "session_id": "", "parent_tool_use_id": None, "message": {"role": "user", "content": prompt}})
                frames = []
                while not frames or frames[-1]["type"] != "result":
                    frames.append(receive())
                hooks = [json.loads(line) for line in log.read_text().splitlines()]
                return finish(endpoint.received, frames, hooks, target, endpoint, case, available, baseline)
        finally:
            endpoint.shutdown()


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "hook":
        write_hook(Path(sys.argv[2]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--claude", required=True)
        parser.add_argument("--case", type=Path, required=True)
        parser.add_argument("--output", type=Path, required=True)
        opt = parser.parse_args()
        opt.output.write_text(json.dumps(run_claude(opt.claude, json.loads(opt.case.read_bytes())), ensure_ascii=False, indent=2) + "\n")
