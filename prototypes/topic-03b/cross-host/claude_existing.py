"""Probe an already-open, observable Claude Code stream with one earlier member turn."""
from contextlib import contextmanager
from hashlib import sha256
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from uuid import uuid4

import claude_tool as native

MODEL = "claude-sonnet-4-6"
AUDIT_HOOK = Path(native.__file__).resolve()
EVENTS = ("UserPromptSubmit", "PreToolUse", "PostToolUse", "PostToolUseFailure", "Stop")


class SessionMessages(native.Messages):
    def do_POST(self):
        if self.server.business:
            return super().do_POST()
        if self.path.split("?")[0] != "/v1/messages":
            self.send_error(404)
            return
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.warm_requests.append(json.loads(raw))
        message = {"id": "msg_warm_" + uuid4().hex, "type": "message", "role": "assistant",
                   "model": MODEL, "content": [], "stop_reason": None, "stop_sequence": None,
                   "usage": {"input_tokens": 10, "output_tokens": 0}}
        frames = [
            {"type": "message_start", "message": message},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Received."}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None}, "usage": {"output_tokens": 1}},
            {"type": "message_stop"},
        ]
        body = "".join(f"event: {f['type']}\ndata: {native.plain(f)}\n\n" for f in frames).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def events_at(path):
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def prompt(send, receive, text):
    send({"type": "user", "session_id": "", "parent_tool_use_id": None, "message": {"role": "user", "content": text}})
    frames = []
    while not frames or frames[-1]["type"] != "result":
        frames.append(receive())
    assert frames[-1]["subtype"] == "success"
    return frames


def control_read(send, receive, subtype):
    rid = uuid4().hex
    send({"type": "control_request", "request_id": rid, "request": {"subtype": subtype}})
    while True:
        frame = receive()
        if frame["type"] == "control_response" and frame["response"]["request_id"] == rid:
            assert frame["response"]["subtype"] == "success"
            return frame["response"]["response"]


def observed_hooks(send, receive, settings):
    readback = control_read(send, receive, "get_settings")
    effective = readback["effective"]["hooks"]
    sources = [item["source"] for item in readback["sources"] if item["settings"].get("hooks")]
    checksum = native.digest(native.plain({"hooks": effective}))
    assert checksum == native.digest(settings.read_text()) and sources == ["flagSettings"]
    return {"settings_sha256": checksum, "hook_sources": sources}


def catalog(send, receive, case):
    # The SDK has one initialize request per stream. mcp_status is also valid between turns.
    until = time.monotonic() + 15
    while True:
        states = {s["name"]: s for s in control_read(send, receive, "mcp_status")["mcpServers"]}
        if all(alias in states and states[alias]["status"] != "pending" for alias in case["servers"]):
            break
        if time.monotonic() >= until:
            raise TimeoutError("MCP catalog unavailable")
        time.sleep(.05)
    target = states[case["expected_server"]]
    spec = case["servers"][case["expected_server"]]
    assert states.keys() == case["servers"].keys()
    assert target["status"] == "connected" and target["scope"] == "dynamic"
    assert target["serverInfo"]["name"] == "orders/inspect-workbook@2"
    assert target["config"]["command"] == spec["command"] and target["config"]["args"] == spec["args"]
    assert [t["name"] for t in target["tools"]] == [case["tool"]]
    return {"scope": target["scope"], "provider": target["serverInfo"]["name"],
            "launch_sha256": native.digest(native.plain(spec)),
            "discovered": sorted(f"mcp__{alias}__{tool['name']}" for alias, state in states.items()
                                 for tool in state.get("tools", []))}


@contextmanager
def open_session(binary, case, callback, extra_hook=False, transform_log=None):
    aliases = case["servers"]
    target = f"mcp__{case['expected_server']}__{case['tool']}"
    namesakes = [f"mcp__{alias}__{case['tool']}" for alias in aliases if alias != case["expected_server"]]
    with tempfile.TemporaryDirectory() as temp, ThreadingHTTPServer(("127.0.0.1", 0), SessionMessages) as endpoint:
        root = Path(temp)
        home, work = root / "home", root / "project"
        home.mkdir()
        work.mkdir()
        audit_log = root / "audit.jsonl"
        def command(path):
            return {"type": "command", "command": shlex.join([sys.executable, str(AUDIT_HOOK), "hook", str(path)])}
        hooks = {key: [{"hooks": [command(audit_log)]}] for key in EVENTS}
        if transform_log is not None:
            modify_command = shlex.join([sys.executable, str(Path(__file__).resolve()), "transform", str(transform_log)])
            hooks["PostToolUse"][0]["hooks"].append({"type": "command", "command": modify_command})
        trusted_settings = native.digest(native.plain({"hooks": hooks}))
        local_log = root / "member-hook.jsonl"
        if extra_hook:
            hooks["UserPromptSubmit"][0]["hooks"].append(command(local_log))
        settings = root / "settings.json"
        settings.write_text(native.plain({"hooks": hooks}))
        profile = root / "issued-mcp.json"
        profile.write_text(native.plain({"mcpServers": aliases}))
        env = {"HOME": str(home), "CLAUDE_CONFIG_DIR": str(home), "PATH": os.environ["PATH"],
               "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{endpoint.server_port}", "ANTHROPIC_API_KEY": "fixture-loopback",
               "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1", "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS": "1",
               "DISABLE_AUTOUPDATER": "1", "ENABLE_TOOL_SEARCH": "false", "NO_COLOR": "1"}
        args = [binary, "-p", "--model", MODEL, "--allowedTools=" + target,
                "--permission-prompts", "none", "--tools=", "--settings", str(settings), "--setting-sources", "project",
                "--strict-mcp-config", "--mcp-config", str(profile), "--input-format", "stream-json",
                "--output-format", "stream-json", "--verbose"]
        if namesakes:
            args.append("--disallowedTools=" + ",".join(namesakes))
        endpoint.warm_requests, endpoint.received, endpoint.hashes = [], [], []
        endpoint.business, endpoint.callback_error = False, None
        endpoint.run_id, endpoint.call_id = uuid4().hex, "toolu_" + uuid4().hex
        endpoint.arguments, endpoint.input_schema = case["arguments"], case["expected_input_schema"]
        endpoint.before_call, endpoint.denied, endpoint.tool, endpoint.target = callback, set(namesakes), target, target
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            with native.stream(args, env, work) as (send, receive):
                native.inspect_servers(send, receive, set(aliases))
                yield (send, receive, endpoint, audit_log, settings, trusted_settings, local_log)
        finally:
            endpoint.shutdown()


def business(session, case, marker):
    send, receive, endpoint, audit_log, settings, trusted_settings, _ = session
    config = observed_hooks(send, receive, settings)
    assert config["settings_sha256"] == trusted_settings
    mcp = catalog(send, receive, case)
    offset = len(events_at(audit_log))
    endpoint.business = True
    frames = prompt(send, receive, "Inspect this bound order candidate. " + native.plain(case["binding"]))
    hooks = events_at(audit_log)[offset:]
    assert all(r["model"] == MODEL for r in endpoint.received)
    marker_seen = [marker in native.plain(r["messages"]) for r in endpoint.received]
    assert len(marker_seen) == 2 and marker_seen[0] == marker_seen[1]
    result = native.finish(endpoint.received, frames, hooks, endpoint.target, endpoint, case, mcp["discovered"],
                           {"binding": case["binding"], "host": "Claude Code 2.1.325"})
    tool_hooks = [h for h in hooks if h["hook_event_name"] in ("PreToolUse", "PostToolUse", "PostToolUseFailure")]
    expected = ["PreToolUse", "PostToolUse" if result["result"]["status"] == "ok" else "PostToolUseFailure"]
    assert [h["hook_event_name"] for h in tool_hooks] == expected
    assert all(h["session_id"] == result["session_id"] and h["tool_use_id"] == result["call_id"]
               and h["prompt_id"] == result["prompt_id"] and h["tool_name"] == endpoint.target for h in tool_hooks)
    return result, marker_seen[0], {**config, "model": MODEL,
                                    "mcp_status": mcp, "hook_events": tool_hooks}


def run_claude_existing(binary, case, before_call=None, *, scenario="reuse"):
    if scenario not in ("reuse", "history-revoked", "unknown-hook"):
        raise ValueError("unexpected existing-session case")
    assert subprocess.check_output([binary, "--version"], text=True).strip() == "2.1.325 (Claude Code)"
    marker = "synthetic-member-turn-" + uuid4().hex
    with open_session(binary, case, before_call, extra_hook=scenario == "unknown-hook") as prior:
        send, receive, endpoint, log, settings, trusted, local_log = prior
        warm = prompt(send, receive, marker)
        prior_id = warm[-1]["session_id"]
        init, = [f for f in warm if f["type"] == "system" and f["subtype"] == "init"]
        assert init["session_id"] == prior_id and init["model"] == MODEL
        assert len(endpoint.warm_requests) == 1 and endpoint.warm_requests[0]["model"] == MODEL
        assert marker in native.plain(endpoint.warm_requests[0]["messages"])
        start, stop = events_at(log)
        assert (start["hook_event_name"], stop["hook_event_name"]) == ("UserPromptSubmit", "Stop")
        assert start["session_id"] == stop["session_id"] == prior_id and start["prompt_id"] == stop["prompt_id"]
        mcp = catalog(send, receive, case)
        # A per-session grant covers the one synthetic prior turn. The control withdraws it before dispatch.
        history_grants = {prior_id: {start["prompt_id"]}}
        if scenario == "history-revoked":
            history_grants.pop(prior_id)
        scope_ok = start["prompt_id"] in history_grants.get(prior_id, set())
        effective = observed_hooks(send, receive, settings)
        settings_hash = effective["settings_sha256"]
        trusted_hooks = settings_hash == trusted
        local_events = events_at(local_log)
        if local_events:
            assert local_events == [start]
        if scope_ok and trusted_hooks:
            decision, reason = "reuse", "prior turn authorized and observed launch settings match"
            actual, included, selected = business(prior, case, marker)
        else:
            decision = "fresh"
            reason = "prior turn sharing withdrawn" if not scope_ok else "hook settings differ from approved command set"
            with open_session(binary, case, before_call) as fresh:
                actual, included, selected = business(fresh, case, marker)
        same_session = actual["session_id"] == prior_id
        assert same_session == included == (decision == "reuse")
        assert actual["prompt_id"] != start["prompt_id"]
        if decision == "fresh":
            assert len(events_at(log)) == 2
        assert bool(local_events) == (scenario == "unknown-hook")
        assert len(events_at(local_log)) == len(local_events)
        details = {"decision": decision, "reason": reason, "prior_session_id": prior_id,
                   "prior_prompt_id": start["prompt_id"], "selected_session_id": actual["session_id"],
                   "prior_business_requests": len(endpoint.received), "selected_model_requests": actual["model_requests"],
                   "prior_marker_in_selected_input": included, "prior_model_requests": len(endpoint.warm_requests),
                   "prior_model": init["model"], "prior_mcp_status": mcp, "prior_settings_sha256": settings_hash,
                   "prior_hook_sources": effective["hook_sources"],
                   "approved_prior_settings_sha256": trusted, "prior_history_authorized": scope_ok,
                   "extra_hook_warm_events": len(local_events), "extra_hook_work_events": len(events_at(local_log))-len(local_events),
                   "hook_program_sha256": sha256(AUDIT_HOOK.read_bytes()).hexdigest(), "selected": selected}
        return {**actual, "existing_session": details}


def order_values(content):
    """Find the order service's JSON within native MCP text blocks or the hook's original response."""
    if isinstance(content, str):
        try:
            parsed, _ = json.JSONDecoder().raw_decode(content.lstrip())
        except ValueError:
            return []
        return order_values(parsed)
    if isinstance(content, dict):
        if {"report", "receipt", "provider", "status"} <= content.keys():
            return [content]
        return [value for item in content.values() for value in order_values(item)]
    if isinstance(content, list):
        return [value for item in content for value in order_values(item)]
    return []


def transform(log_path):
    event = json.load(sys.stdin)
    original, = order_values(event["tool_response"])
    amended = {**original, "hook_note": "synthetic-presentation-change"}
    record = {"prompt_id": event["prompt_id"], "session_id": event["session_id"], "call_id": event["tool_use_id"],
              "receipt": original["receipt"], "source_sha256": native.digest(native.plain(original)),
              "amended_sha256": native.digest(native.plain(amended))}
    with log_path.open("x") as out:
        out.write(native.plain(record))
    print(native.plain({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                        "updatedMCPToolOutput": [{"type": "text", "text": native.plain(amended)}]}}))


def transformed_call(binary, case):
    """Observe the service return before the Hook and both native and model-visible content after it."""
    with tempfile.TemporaryDirectory() as temporary:
        log = Path(temporary) / "transform.json"
        with open_session(binary, case, None, transform_log=log) as session:
            send, receive, endpoint, audit_log, _, _, _ = session
            catalog(send, receive, case)
            endpoint.business = True
            frames = prompt(send, receive, "Inspect this bound order candidate. " + native.plain(case["binding"]))
            assert endpoint.callback_error is None and len(endpoint.received) == 2
            call_id = endpoint.call_id
            native_call, = [b for f in frames if f["type"] == "assistant" for b in f["message"]["content"]
                            if b.get("type") == "tool_use" and b["id"] == call_id]
            assert native_call["input"] == case["arguments"] and native_call["name"] == endpoint.target
            native_block, = [b for f in frames if f["type"] == "user" for b in f["message"]["content"]
                             if b.get("tool_use_id") == call_id]
            wire_block, = [b for m in endpoint.received[1]["messages"] if isinstance(m["content"], list)
                           for b in m["content"] if b.get("type") == "tool_result" and b["tool_use_id"] == call_id]
            wire_value, = order_values(wire_block["content"])
            native_value, = order_values(native_block["content"])
            assert wire_value["hook_note"] == "synthetic-presentation-change" and wire_value["status"] == "ok"
            hooks = events_at(audit_log)
            hook = json.loads(log.read_bytes())
            assert hook["call_id"] == call_id and hook["session_id"] == frames[-1]["session_id"]
            assert [h["hook_event_name"] for h in hooks] == ["UserPromptSubmit","PreToolUse","PostToolUse","Stop"]
            assert {h["prompt_id"] for h in hooks} == {hook["prompt_id"]}
            assert all(h["tool_name"] == endpoint.target and h["tool_use_id"] == call_id for h in hooks[1:3])
            model_hash = native.digest(native.plain(wire_value))
            native_hash = native.digest(native.plain(native_value))
            assert hook["amended_sha256"] == model_hash == native_hash and model_hash != hook["source_sha256"]
            actual = {"status": "completed", "model_requests": 2, "selected_tool": endpoint.target, "call_id": call_id,
                      "arguments": native_call["input"], "result": wire_value, "result_text_sha256": model_hash,
                      "session_id": hook["session_id"], "prompt_id": hook["prompt_id"]}
            return actual, {**hook, "native_result_sha256": native_hash, "model_result_sha256": model_hash,
                            "audited_tool_hooks": [h["hook_event_name"] for h in hooks[1:3]]}


def run_claude_hook_transform(study, record):
    """Pass the changed result through the same host-proof and node admission path as a normal run."""
    from contextlib import closing
    import sqlite3
    from order_tool import PROJECT

    evidence = {}
    def adapter(binary, case, before_call=None):
        assert before_call is None
        actual, observed = transformed_call(binary, case)
        evidence["actual"], evidence["hook"] = actual, observed
        return actual

    try:
        study.invoke(record, "claude", "post-tool-use-output-change", adapter_override=adapter)
    except ValueError as exc:
        if str(exc) != "service receipt differs from native tool result":
            raise
    else:
        raise AssertionError("changed native tool result received an authoritative host proof")
    actual, hook = evidence["actual"], evidence["hook"]
    with closing(sqlite3.connect(study.db)) as conn:
        event, = conn.execute("SELECT receipt,service,run,outcome,result_hash FROM events")
        assert conn.execute("SELECT COUNT(*) FROM host_proof").fetchone()[0] == 0
    assert event == (hook["receipt"], PROJECT, record.run, "ok", hook["source_sha256"])
    assert event[4] != actual["result_text_sha256"] and actual["result"]["receipt"] == event[0]
    decision = study.submit(record, actual)
    assert decision == "no verified tool result" and study.counts() == {"consumed": 0, "artifact": 0}
    return {**hook, "service": event[1], "run": record.run, "service_result_sha256": event[4],
            "business_requests": actual["model_requests"], "service_calls": 1, "disposition": decision,
            "proof_rejection": "service receipt differs from native tool result", "before_reverification": study.counts()}


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "transform":
    transform(Path(sys.argv[2]))
