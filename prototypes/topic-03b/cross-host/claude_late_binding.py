"""Attach a newly issued C2 project tool to an already running, consenting Claude stream."""
from contextlib import closing
import sqlite3
from uuid import uuid4

from claude_existing import business, events_at, open_session, prompt
import claude_tool
from order_tool import SCHEMA, TOOL


def control(session, subtype, **params):
    send, receive = session[:2]
    request_id = uuid4().hex
    send({"type": "control_request", "request_id": request_id,
          "request": {"subtype": subtype, **params}})
    while True:
        frame = receive()
        if frame.get("type") == "control_response" and frame["response"]["request_id"] == request_id:
            return frame["response"]


def run_late_binding(study):
    marker = "synthetic-pre-dispatch-" + uuid4().hex
    # A harmless unused allow rule keeps the prior session's tool surface empty. No
    # project server, secret, order identity or model business prompt exists at this point.
    blank = {"servers": {}, "expected_server": "unconfigured", "tool": "unconfigured",
             "arguments": {}, "expected_input_schema": None}
    with open_session(study.binaries["claude"], blank, None) as session:
        send, receive, endpoint, audit, *_ = session
        prior_frames = prompt(send, receive, marker)
        prior_session = prior_frames[-1]["session_id"]
        warm_hook, stop = events_at(audit)
        assert warm_hook["session_id"] == stop["session_id"] == prior_session
        assert control(session, "mcp_status")["response"]["mcpServers"] == []
        first_settings = control(session, "get_settings")["response"]["effective"]
        assert not first_settings.get("permissions", {}).get("allow")
        [earlier] = endpoint.warm_requests
        assert not [t for t in earlier["tools"] if t["name"].startswith("mcp__")]
        assert marker in claude_tool.plain(earlier["messages"])
        with closing(sqlite3.connect(study.db)) as db:
            for table in ("leases", "dispatch", "events", "consumed"):
                assert db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0
        assert not list(study.root.glob("*-project_orders.json"))
        record = study.issue("issued-after-member-prompt", "claude", 1)
        # This update applies to a known empty server set. Replacing an arbitrary
        # user's complete MCP set would need a separate agreement.
        alias = "project_orders"
        target = f"mcp__{alias}__{TOOL}"
        servers = {alias: record.providers[alias]}
        applied = control(session, "mcp_set_servers", servers=servers)
        assert applied["subtype"] == "success", applied.get("error", "MCP update failed")
        result = applied["response"]
        assert result["added"] == [alias] and not result["errors"] and not result["removed"], result
        settings = control(session, "apply_flag_settings", settings={"permissions": {"allow": [target]}})
        assert settings["subtype"] == "success", settings.get("error", "permission update failed")
        readback = control(session, "get_settings")["response"]
        assert readback["effective"]["permissions"]["allow"] == [target]
        sources = [row["source"] for row in readback["sources"]
                   if row["settings"].get("permissions", {}).get("allow") == [target]]
        assert sources == ["flagSettings"]
        endpoint.arguments = {"candidate": record.contract["candidate"]}
        endpoint.tool = endpoint.target = target
        endpoint.input_schema = SCHEMA["inputSchema"]

        def attached(_binary, case, before_call=None):
            assert before_call is None
            # The person's test grant covers the one previous turn on this exclusive stream.
            result, marker_seen, selected = business(session, {**case, "servers": servers}, marker)
            assert result["session_id"] == prior_session and result["prompt_id"] != warm_hook["prompt_id"]
            assert marker_seen and result["selected_tool"] == target
            return {**result, "existing_session": {
                "decision": "reuse", "prior_session_id": prior_session, "selected_session_id": result["session_id"],
                "prior_prompt_id": warm_hook["prompt_id"], "prior_model_requests": len(endpoint.warm_requests),
                "selected_model_requests": result["model_requests"], "prior_marker_in_selected_input": marker_seen,
                "dispatches_before_issue": 0, "project_servers_before_issue": 0,
                "mcp_update": {"added": applied["response"]["added"]}, "permission_update": target,
                "effective_allow_after_update": [target], "permission_source": sources[0],
                "selected": selected}}

        actual = study.invoke(record, "claude", "attach-issued-project-tool", adapter_override=attached)
        assert study.submit(record, actual) == "current" and study.submit(record, actual) == "duplicate"
        assert study.counts() == {"consumed": 1, "artifact": 3}
        return {**study.summary(), "accepted_result": study.accepted_result(record, actual)}
