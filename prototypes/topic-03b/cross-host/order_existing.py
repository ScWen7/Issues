"""Admit order results from an authorized existing session or an isolated replacement."""
import argparse
from functools import partial
from pathlib import Path
import sqlite3
import subprocess
import sys

from claude_existing import run_claude_existing, run_claude_hook_transform
from claude_late_binding import run_late_binding
from codex_existing import probe_interleaving, run_codex_existing
from codex_terminal import run_terminal
from order_handoff import ORDERS, Study, write


def run_case(study, host, scenario, *, revoke=False):
    label = host + "-" + ("revoked-at-call" if revoke else scenario)
    job = study.issue(label, host, 1)
    execute = run_codex_existing if host == "codex" else run_claude_existing
    native = study.invoke(job, host, label, revoke_in_flight=revoke,
                          adapter_override=partial(execute, scenario=scenario))
    route = native["existing_session"]
    reuse = scenario == "reuse"
    assert route["decision"] == ("reuse" if reuse else "fresh")
    assert route["selected_session_id"] == (native.get("thread_id") or native.get("session_id"))
    assert (route["selected_session_id"] == route["prior_session_id"]) == reuse
    assert route["prior_business_requests"] == (2 if reuse else 0)
    assert route["selected_model_requests"] == native["model_requests"] == 2
    assert route["prior_marker_in_selected_input"] is reuse

    accepted = None
    if revoke:
        assert native["result"]["status"] == "denied"
        assert study.submit(job, native) == "no verified tool result"
        assert study.counts() == {"consumed": 0, "artifact": 0}
    else:
        assert study.submit(job, native) == "current"
        assert study.submit(job, native) == "duplicate"
        accepted = study.accepted_result(job, native)
    with sqlite3.connect(study.db) as db:
        # The earlier personal turn and the Hook callbacks do not create another order dispatch.
        assert db.execute("SELECT COUNT(*) FROM dispatch").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    return {**study.summary(), "accepted_result": accepted}


def run_hook_reverification(study):
    original = study.issue("post-hook-order", "claude", 1)
    transformed = run_claude_hook_transform(study, original)
    # The first host returned its result and exited. A new execution owns its own Run.
    successor = study.issue("post-hook-reverification", "claude", 2, prior=original)
    clean = study.invoke(successor, "claude", "clean-read-after-hook")
    assert study.submit(successor, clean) == "current" and study.submit(successor, clean) == "duplicate"
    with sqlite3.connect(study.db) as db:
        assert db.execute("SELECT task_active FROM dispatch WHERE run=?", (original.run,)).fetchone() == (0,)
        assert db.execute("SELECT run FROM current_node").fetchone() == (successor.run,)
        assert db.execute("SELECT COUNT(*) FROM dispatch").fetchone() == (2,)
        assert set(db.execute("SELECT run FROM events")) == {(original.run,), (successor.run,)}
    return {"transformed": transformed, "reverification": study.summary(),
            "reverification_link": {"source_run": original.run, "successor_run": successor.run,
                                    "reason": transformed["proof_rejection"],
                                    "node_attempt": original.contract["attempt"]},
            "accepted_result": study.accepted_result(successor, clean)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--codex", required=True)
    parser.add_argument("--claude", required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir()
    orders = output / "orders"
    subprocess.run([sys.executable, ORDERS / "run.py", orders], check=True, stdout=subprocess.DEVNULL)
    cases = {}
    for host, scenarios in (("codex", ("reuse", "history-revoked", "expanded-catalog", "unknown-provenance", "unshared-turn")),
                            ("claude", ("reuse", "history-revoked", "unknown-hook"))):
        for scenario in scenarios:
            key = host + "-" + scenario
            study = Study(output / key, orders, args.codex, args.claude)
            cases[key] = run_case(study, host, scenario)
        key = host + "-revoked-at-call"
        study = Study(output / key, orders, args.codex, args.claude)
        cases[key] = run_case(study, host, "reuse", revoke=True)
    study = Study(output / "codex-tui", orders, args.codex, None)
    job = study.issue("member-tui-order", "codex", 1)
    native = study.invoke(job, "codex", "takeover-live-TUI", adapter_override=run_terminal)
    assert study.submit(job, native) == "current" and study.submit(job, native) == "duplicate"
    cases["codex-tui"] = {**study.summary(), "accepted_result": study.accepted_result(job, native)}
    late = Study(output / "claude-late-binding", orders, None, args.claude)
    cases["claude-late-binding"] = run_late_binding(late)
    # Keep diagnostic traffic and the intentionally transformed output identifiable separately.
    interleaving = probe_interleaving(args.codex)
    study = Study(output / "claude-transform", orders, None, args.claude)
    transform_control = run_hook_reverification(study)
    write(output / "summary.json", {"cases": cases, "concurrent_input": interleaving,
                                    "post_hook_result": transform_control})
    for key, value in cases.items():
        route = value["cases"][0]["native"]["existing_session"]
        print(key, route["decision"], value["counts"])


if __name__ == "__main__":
    main()
