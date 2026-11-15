"""Continue a member's live interactive Codex TUI from an authorized second client."""
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from uuid import uuid4

import pexpect
from websockets.sync.client import connect

from codex_connection import SocketClient, shared_endpoint
from codex_existing import ExistingEndpoint, MODEL, origin_evidence, pinned_codex, surface, turn, visible_tools
from codex_tool import configuration, verify_return


def run_terminal(binary, case, before_call=None):
    binary = pinned_codex(binary)
    marker = "member-tui-fixture-" + uuid4().hex
    with tempfile.TemporaryDirectory() as tmp, ThreadingHTTPServer(("127.0.0.1", 0), ExistingEndpoint) as endpoint:
        home, work = Path(tmp) / "home", Path(tmp) / "project"
        home.mkdir()
        work.mkdir()
        project_only = {"project_orders": case["servers"]["project_orders"]}
        (home / "config.toml").write_text(configuration(work, endpoint, project_only))
        endpoint.case, endpoint.before_call = case, before_call
        endpoint.model_server, endpoint.call_id = "project_orders", "order-" + uuid4().hex
        endpoint.business, endpoint.requests, endpoint.wire_hashes, endpoint.warmup = False, [], [], []
        threading.Thread(target=endpoint.serve_forever, daemon=True).start()
        with ExitStack() as stack:
            stack.callback(endpoint.shutdown)
            url, token = stack.enter_context(shared_endpoint(binary, home, work))
            env = {"PATH": os.environ["PATH"], "HOME": str(home), "CODEX_HOME": str(home),
                   "TERM": "xterm-256color", "MEMBER_SESSION_TOKEN": token}
            args = ["--remote", url, "--remote-auth-token-env", "MEMBER_SESSION_TOKEN", "--no-alt-screen",
                    "--ask-for-approval", "on-request", "--sandbox", "read-only", marker]
            member = pexpect.spawn(binary, args, env=env, cwd=str(work), encoding="utf8", dimensions=(40, 120))
            stack.callback(member.close, force=True)
            # Receipt on the actual terminal, after its project-free member turn has completed.
            member.expect_exact("Ready for the next turn.", timeout=15)
            assert member.isalive() and len(endpoint.warmup) == 1 and not endpoint.requests
            socket = stack.enter_context(connect(url, additional_headers={"Authorization": "Bearer " + token}, proxy=None))
            platform = SocketClient(socket, "tui-order-takeover")
            # The fixture is a member-authorized, isolated host containing exactly one active thread.
            [tid] = platform.call("thread/loaded/list", {"limit": 2})["data"]
            deadline = time.monotonic() + 5
            while True:
                history = platform.call("thread/read", {"threadId": tid, "includeTurns": True})["thread"]
                if history["status"]["type"] == "idle":
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("member TUI has not finished its previous turn")
                time.sleep(.05)
            [previous] = history["turns"]
            assert previous["status"] == "completed" and marker in json.dumps(previous["items"])
            # Consent in this scenario covers this single earlier turn locally and in model input.
            granted = (tid, previous["id"])
            resumed = platform.call("thread/resume", {"threadId": tid, "excludeTurns": True})
            assert resumed["thread"]["id"] == granted[0] and resumed["cwd"] == str(work)
            assert resumed["model"] == MODEL and resumed["modelProvider"] == "fixture"
            assert resumed["approvalPolicy"] == "on-request" and resumed["sandbox"]["type"] == "readOnly"
            provenance = origin_evidence(platform, home, work, {**case, "servers": project_only})
            catalog = surface(platform, tid)
            assert visible_tools(catalog) == ["mcp__project_orders.inspect_order"]
            assert catalog["project_orders"][case["tool"]]["inputSchema"] == case["expected_input_schema"]
            prompt = "Check the authorized order workbooks for this binding. " + json.dumps(case["binding"], sort_keys=True)
            endpoint.business = True
            business = turn(platform, tid, prompt)
            turns = platform.call("thread/read", {"threadId": tid, "includeTurns": True})["thread"]["turns"]
            assert [t["id"] for t in turns] == [granted[1], business]
            notices = [m["params"] for m in platform.seen if m.get("method") == "item/completed"
                       and m["params"]["turnId"] == business and m["params"]["item"]["type"] == "mcpToolCall"]
            actual = verify_return(endpoint, tid, business, turns[-1]["items"], notices, case, prompt)
            assert all(marker in json.dumps(req["input"]) and req["model"] == MODEL for req in endpoint.requests)
            assert member.isalive()
            return {**actual, "existing_session": {
                "decision": "reuse", "reason": "member shared the live TUI endpoint and its only prior turn",
                "prior_session_id": tid, "selected_session_id": tid, "prior_turn_id": granted[1],
                "prior_business_requests": 2, "selected_model_requests": 2, "prior_marker_in_selected_input": True,
                "prior_marker_in_followup": True, "client": "codex TUI --remote, pseudoterminal",
                "tui_alive_at_result": True, "unauthenticated_client_rejected": True,
                "selected_model": MODEL, "selected_mcp": visible_tools(catalog), **provenance}}
