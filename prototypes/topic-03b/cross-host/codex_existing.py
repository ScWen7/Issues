"""Check an already-open Codex thread before delivering the bound order turn."""
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import uuid

from codex_connection import connected_clients
from codex_tool import OrderEndpoint, configuration, mcp_functions, tool_catalog, verify_return

MODEL = "gpt-5.1-codex"
SCENARIOS = ("reuse", "history-revoked", "expanded-catalog", "unknown-provenance", "unshared-turn")


class ExistingEndpoint(OrderEndpoint):
    def do_POST(self):
        if self.server.business:
            return super().do_POST()
        assert self.path == "/v1/responses"
        wire = self.rfile.read(int(self.headers["Content-Length"]))
        self.server.warmup.append(json.loads(wire))
        item = {"type": "message", "role": "assistant", "id": "msg_member", "content": [
            {"type": "output_text", "text": "Ready for the next turn."}]}
        rid = "member_response"
        events = [{"type": "response.created", "response": {"id": rid}},
                  {"type": "response.output_item.done", "item": item},
                  {"type": "response.completed", "response": {"id": rid}}]
        payload = "".join("data: " + json.dumps(e) + "\n\n" for e in events).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def turn(rpc, thread, text):
    result = rpc.call("turn/start", {"threadId": thread, "input": [{"type": "text", "text": text}]})
    tid = result["turn"]["id"]
    done = rpc.wait(lambda m: m.get("method") == "turn/completed" and m["params"]["turn"]["id"] == tid)
    assert done["params"]["threadId"] == thread and done["params"]["turn"]["status"] == "completed"
    return tid


def surface(rpc, tid):
    rows = tool_catalog(rpc, tid)
    return {name: row["tools"] for name, row in rows.items() if row["tools"]}


def visible_tools(catalog):
    return sorted("mcp__" + name + "." + tool for name, tools in catalog.items() for tool in tools)


def origin_evidence(rpc, home, work, case):
    config = rpc.call("config/read", {"cwd": str(work), "includeLayers": True})
    user, = [l for l in config["layers"] if l["name"].get("file") == str(home / "config.toml")]
    origins = config["origins"]
    needed = ["model", "model_provider", "model_providers.fixture.base_url",
              "mcp_servers.project_orders.command", "mcp_servers.project_orders.args.0",
              "mcp_servers.project_orders.args.1"]
    assert all(origins[key]["version"] == user["version"] and origins[key]["name"] == user["name"] for key in needed)
    assert user["config"]["mcp_servers"] == case["servers"] and user["config"]["model"] == MODEL
    hooks, = rpc.call("hooks/list", {"cwds": [str(work)]})["data"]
    assert hooks == {"cwd": str(work), "hooks": [], "warnings": [], "errors": []}
    return {"config_source": user["name"]["type"], "config_version": user["version"],
            "config_layers": sorted(l["name"]["type"] for l in config["layers"]),
            "hook_source": "hooks/list(cwd)", "hooks_observed": [], "hook_scope": "cwd, not per-thread"}


def verify_selected(start, work):
    assert (start["model"], start["modelProvider"], start["approvalPolicy"]) == (MODEL, "fixture", "on-request")
    assert start["sandbox"] == {"type": "readOnly", "networkAccess": False}
    assert start["cwd"] == str(work) and not start["instructionSources"]


def experiment(binary, home, work, endpoint, case, scenario):
    server, tool = case["expected_server"], case["tool"]
    scoped = {**{f"mcp_servers.{alias}.enabled": False for alias in case["servers"] if alias != server},
              f"mcp_servers.{server}.enabled_tools": [tool]}
    params = {"cwd": str(work), "approvalPolicy": "on-request", "sandbox": "read-only"}
    marker = "private-fixture-" + uuid.uuid4().hex
    prompt = "Check the authorized order workbooks for this binding. " + json.dumps(case["binding"], sort_keys=True)
    with connected_clients(binary, home, work) as (member, connect_platform):
        # Only the member operates the first client. Its prior turn finishes before the platform connects.
        old = member.call("thread/start", {**params, "config": {} if scenario == "expanded-catalog" else scoped})
        prior = old["thread"]["id"]
        at_open = origin_evidence(member, home, work, case)
        receipt_at_open = {} if scenario == "unknown-provenance" else {prior: at_open["config_version"]}
        warm = turn(member, prior, marker)
        assert len(endpoint.warmup) == 1 and marker in json.dumps(endpoint.warmup[0]["input"])
        private_markers = [marker]
        if scenario == "unshared-turn":
            private_markers.append("another-member-only-" + uuid.uuid4().hex)
            turn(member, prior, private_markers[-1])
        rpc = connect_platform()
        listed = rpc.call("thread/loaded/list", {"limit": 100})
        assert prior in listed["data"] and not listed.get("nextCursor")
        # thread/read can return a preview. Inspect the IDs and statuses with item bodies omitted.
        page = rpc.call("thread/turns/list", {"threadId": prior, "itemsView": "notLoaded",
                        "limit": 100, "sortDirection": "asc"})
        assert all(not t["items"] and t["status"] == "completed" for t in page["data"])
        previous_surface = surface(rpc, prior)
        config = origin_evidence(rpc, home, work, case)
        verify_selected(old, work)
        selected_name = f"mcp__{server}.{tool}"
        expected_tools = [selected_name]
        assert set(visible_tools(previous_surface)) == mcp_functions(endpoint.warmup[0])
        # This fixture's member granted inspection locally; only this one completed turn may be carried to the model.
        history_scope = {prior: [warm]}
        if scenario == "history-revoked":
            history_scope.clear()
        if prior not in history_scope:
            reason = "prior history sharing withdrawn"
        elif page["nextCursor"] or [t["id"] for t in page["data"]] != history_scope[prior]:
            reason = "prior history includes an unshared turn"
        elif receipt_at_open.get(prior) != config["config_version"]:
            reason = "original configuration revision unavailable"
        elif visible_tools(previous_surface) != expected_tools:
            reason = "existing MCP surface includes an unapproved provider"
        else:
            reason = "authorized history and verified thread scope"
        reuse = reason == "authorized history and verified thread scope"
        if reuse:
            resumed = rpc.call("thread/resume", {"threadId": prior, "excludeTurns": True})
            verify_selected(resumed, work)
            tid = resumed["thread"]["id"]
            assert tid == prior
            history = rpc.call("thread/read", {"threadId": tid, "includeTurns": True})["thread"]["turns"]
            assert [t["id"] for t in history] == history_scope[prior]
        else:
            fresh = rpc.call("thread/start", {**params, "config": scoped})
            verify_selected(fresh, work)
            tid = fresh["thread"]["id"]
            assert tid != prior
        current = surface(rpc, tid)
        assert visible_tools(current) == expected_tools and current[server][tool]["inputSchema"] == case["expected_input_schema"]
        assert endpoint.requests == []
        endpoint.business = True
        business_turn = turn(rpc, tid, prompt)
        turns = rpc.call("thread/read", {"threadId": tid, "includeTurns": True})["thread"]["turns"]
        assert [t["id"] for t in turns] == ([warm, business_turn] if reuse else [business_turn])
        notifications = [m["params"] for m in rpc.seen if m.get("method") == "item/completed"
                         and m["params"]["turnId"] == business_turn and m["params"]["item"]["type"] == "mcpToolCall"]
        actual = verify_return(endpoint, tid, business_turn, turns[-1]["items"], notifications, case, prompt)
        markers = [marker in json.dumps(req["input"]) for req in endpoint.requests]
        assert markers == [reuse, reuse] and all(req["model"] == MODEL for req in endpoint.requests)
        if not reuse:
            assert all(private not in json.dumps(req["input"]) for req in endpoint.requests for private in private_markers)
        assert all(prompt not in json.dumps(req["input"]) for req in endpoint.warmup)
        return {**actual, "existing_session": {"decision": "reuse" if reuse else "fresh", "reason": reason,
                "prior_session_id": prior, "prior_turn_id": warm, "selected_session_id": tid,
                "selected_model_requests": len(endpoint.requests), "prior_business_requests": 2 if tid == prior else 0,
                "prior_marker_in_selected_input": markers[0], "prior_marker_in_followup": markers[1],
                "private_markers_checked": len(private_markers),
                "selected_model": endpoint.requests[0]["model"], "observed_provider": old["modelProvider"],
                "prior_mcp": visible_tools(previous_surface), "selected_mcp": visible_tools(current),
                "non_mcp_tools": sorted(t.get("name", t["type"]) for t in endpoint.requests[0]["tools"]
                                       if not t.get("name", "").startswith("mcp__")),
                "history_grant": "prior turn" if prior in history_scope else "withdrawn",
                "prior_turn_count_inspected": len(page["data"]), "prior_turn_items_inspected": 0,
                "prior_config_receipt_present": prior in receipt_at_open,
                "config_version_at_open": receipt_at_open.get(prior),
                "connection": "authenticated second client on member-shared loopback App Server",
                **config}}


def run_codex_existing(binary, case, before_call=None, *, scenario="reuse"):
    binary = pinned_codex(binary)
    if scenario not in SCENARIOS:
        raise ValueError("unsupported Codex session scenario")
    with tempfile.TemporaryDirectory() as tmp, ThreadingHTTPServer(("127.0.0.1", 0), ExistingEndpoint) as endpoint:
        home, work = Path(tmp) / "home", Path(tmp) / "work"
        home.mkdir()
        work.mkdir()
        (home / "config.toml").write_text(configuration(work, endpoint, case["servers"]))
        endpoint.case, endpoint.before_call = case, before_call
        endpoint.model_server = case["expected_server"]
        endpoint.call_id = "order-" + uuid.uuid4().hex
        endpoint.business, endpoint.requests, endpoint.wire_hashes, endpoint.warmup = False, [], [], []
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            return experiment(binary, home, work, endpoint, case, scenario)
        finally:
            endpoint.shutdown()



def pinned_codex(binary):
    binary = shutil.which(str(binary))
    if not binary or subprocess.check_output([binary, "--version"], text=True).strip() != "codex-cli 0.144.6":
        raise ValueError("requires Codex 0.144.6")
    return binary


def probe_interleaving(binary):
    """Two authorized clients on an idle thread. Only harmless text reaches the fixture model."""
    binary = pinned_codex(binary)
    with tempfile.TemporaryDirectory() as tmp, ThreadingHTTPServer(("127.0.0.1", 0), ExistingEndpoint) as endpoint:
        home, work = Path(tmp) / "home", Path(tmp) / "work"
        home.mkdir()
        work.mkdir()
        (home / "config.toml").write_text(configuration(work, endpoint, {}))
        endpoint.business, endpoint.warmup = False, []
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        try:
            with connected_clients(binary, home, work) as (member, connect_platform):
                opened = member.call("thread/start", {"cwd": str(work), "sandbox": "read-only",
                                     "approvalPolicy": "on-request"})
                tid = opened["thread"]["id"]
                known = turn(member, tid, "shared diagnostic turn")
                rpc = connect_platform()
                assert rpc.call("thread/resume", {"threadId": tid, "excludeTurns": True})["thread"]["id"] == tid
                page = rpc.call("thread/turns/list", {"threadId": tid, "itemsView": "notLoaded", "limit": 10})
                assert not page["nextCursor"] and [t["id"] for t in page["data"]] == [known]
                marker = "interleaved-fixture-" + uuid.uuid4().hex
                added = turn(member, tid, marker)
                diagnostic = turn(rpc, tid, "return a diagnostic acknowledgment")
                requests = endpoint.warmup
                assert len(requests) == 3 and not any(mcp_functions(r) for r in requests)
                assert not any(i.get("type") in ("function_call", "function_call_output") for r in requests
                               for i in r["input"])
                assert [marker in json.dumps(r["input"]) for r in requests] == [False, True, True]
                assert not any(m.get("params", {}).get("item", {}).get("type") == "mcpToolCall" for m in rpc.seen)
                return {"session_id": tid, "checked_turn_ids": [known], "member_turn_after_check": added,
                        "diagnostic_turn_id": diagnostic, "new_marker_in_diagnostic_input": True,
                        "diagnostic_model_requests": 1, "mcp_tool_calls": 0, "order_prompts": 0}
        finally:
            endpoint.shutdown()
