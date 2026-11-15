"""Run a revision, scope, turnover and host-input case using the real order-export issue."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

from docx_fixture import Origin
from source_context import Assembly, Binding, Index, Pending


HERE = Path(__file__).resolve().parent
FIXTURES = HERE.parents[2] / "docs/research/topic-03a/fixtures"
MAIN, QA, PRIVATE = "order-prd", "validation-notes", "finance-private"
DEV, TEST = "order-developer", "order-verifier"
COMMON = "按 D2 导出当前可见订单；新增付款时间，未付款留空。引用代号 ORD-D2-COMMON。"
DEV_TEXT = "实现时对付款事件的时间戳做 Asia/Shanghai 转换。引用代号 ORD-DEV-TZ。"
OLD_DEV = "实现时使用旧版订单时间格式。引用代号 ORD-DEV-OLD。"
CHECK = "核验时逐项比对东区、西区和只读角色的可见订单。引用代号 ORD-QA-A2。"
SECRET = "财务项目独有的合成例外说明。引用代号 FIN-PRIVATE-ONLY。"
OPTIONAL = "在可选的后续体验检查中记录空列表文案。引用代号 ORD-OPTIONAL。"


def contract(dev, title="开发说明", extra=False):
    rows = [("required", "业务约定", COMMON), ("implementation", title, dev)]
    if extra:
        rows.insert(0, ("display", "界面", OPTIONAL))
    return rows


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read(path):
    return json.loads(path.read_bytes())


def run(out, codex):
    out.mkdir()
    c2 = read(FIXTURES / "order-export-c2.json")
    issue, node = c2["issue"], c2["node"]
    origin = Origin()
    origin.readers = {MAIN: {DEV, TEST}, QA: {TEST}, PRIVATE: {"finance"}}
    origin.publish(MAIN, 1, contract(OLD_DEV))
    origin.publish(QA, 1, [("acceptance", "独立核验", CHECK)])
    origin.publish(PRIVATE, 1, [("finance", "财务", SECRET)])
    index = Index()
    for source in (MAIN, QA, PRIVATE):
        index.refresh(source, origin, "09:00")
    bindings = {
        "dev": Binding(DEV, "orders", "developer", issue, "implement-order-export", "dev", 1),
        "check": Binding(TEST, "orders", "verifier", issue, node, "check", 2),
        "unrelated": Binding("finance", "finance", "reviewer", "unrelated", "finance-control", "unrelated", 1),
    }
    plans = {("orders", "developer"): ((MAIN, "required"), (MAIN, "implementation")),
             ("orders", "verifier"): ((MAIN, "required"), (QA, "acceptance")),
             ("finance", "reviewer"): ((PRIVATE, "finance"),)}
    assembly = Assembly(index, origin, bindings, {"orders": {DEV, TEST}, "finance": {"finance"}}, plans)
    controls = {}
    def reject(name, expected, error, action):
        try:
            action()
        except expected as exc:
            assert str(exc) == error, (name, exc)
            controls[name] = str(exc)
        else:
            raise AssertionError(name)
    search_results = {}

    def search(name, actor, run, query, expected):
        hits = assembly.lookup(actor, run, query)
        assert [hit["citation"]["heading"] for hit in hits] == expected, (name, hits)
        search_results[name] = [hit["citation"] for hit in hits]
        return hits

    missing = "required input unavailable"
    dev_old = assembly.queue(DEV, "dev")
    qa_old = assembly.queue(TEST, "check")
    assembly.deliver(DEV, "dev", dev_old, "before-change")
    assembly.deliver(TEST, "check", qa_old, "before-change")
    assert assembly.deliver("finance", "unrelated", assembly.queue("finance", "unrelated"), "control") == {"finance": SECRET}
    reject("wrong_member_run", Pending, missing, lambda: assembly.queue(DEV, "check"))
    reject("unknown_run", Pending, missing, lambda: assembly.queue(DEV, "unknown"))
    reject("cross_project_search", Pending, missing, lambda: assembly.lookup("finance", "dev", "订单"))
    plans["orders", "developer"] += ((QA, "required"),)
    reject("ambiguous_handoff_alias", Pending, "ambiguous section alias", lambda: assembly.queue(DEV, "dev"))
    plans["orders", "developer"] = plans["orders", "developer"][:-1]
    # Ordinary edit: the product owner changes just the development section; its stable ID survives a rename/move.
    origin.publish(MAIN, 2, contract(DEV_TEXT, "开发时区", extra=True))
    reject("latest_changed_before_sync", Pending, missing, lambda: assembly.queue(DEV, "dev"))
    origin.fail_page = (MAIN, 2)
    reject("partial_fetch", ConnectionError, "interrupted before next page", lambda: index.refresh(MAIN, origin, "09:10"))
    assert (index.revisions[MAIN], index.checked[MAIN], index.state[MAIN]) == (1, "09:00", "unconfirmed")
    origin.fail_page = None
    index.refresh(MAIN, origin, "09:11")
    dev = assembly.queue(DEV, "dev")
    qa = assembly.queue(TEST, "check")
    assert dev[0]["sha256"] == dev_old[0]["sha256"] and qa[1] == qa_old[1]
    assert dev[1]["heading"] == dev_old[1]["heading"] and dev[1]["sha256"] != dev_old[1]["sha256"]
    hits = search("renamed_developer_section", DEV, "dev", "开发时区", ["implementation"])
    assert hits[0]["excerpt"] == DEV_TEXT and hits[0]["title"] == "开发时区"
    search("verifier_cannot_search_developer_only_text", TEST, "check", "ORD-DEV-TZ", [])
    search("private_source_not_discoverable", DEV, "dev", "FIN-PRIVATE-ONLY", [])
    search("old_body_after_refresh", DEV, "dev", "ORD-DEV-OLD", [])
    search("optional_outside_plan", DEV, "dev", "ORD-OPTIONAL", [])
    search("verifier_order_query", TEST, "check", "订单", ["required", "acceptance"])
    reject("old_delivery_after_revision", Pending, "selected source changed",
           lambda: assembly.deliver(DEV, "dev", dev_old, "new-turn"))
    reject("old_verifier_queue_needs_new_document_revision", Pending, "selected source changed",
           lambda: assembly.deliver(TEST, "check", qa_old, "reused-qa-queue"))
    assert [c["sha256"] for c in qa] == [c["sha256"] for c in qa_old] and qa[0]["revision"] != qa_old[0]["revision"]
    changed_history = assembly.affected(MAIN, "implementation", dev_old[1]["sha256"])
    assert changed_history == [["dev", "before-change"]]
    developer = assembly.deliver(DEV, "dev", dev, "developer")
    verifier = assembly.deliver(TEST, "check", qa, "verifier")
    assert list(developer) == ["required", "implementation"] and list(verifier) == ["required", "acceptance"]
    assert "finance" not in developer.keys() | verifier.keys()
    assert index.state[MAIN] == "current" and index.checked[MAIN] == "09:11"

    def turn(step, run_key, selected, citations=()):
        return {"step": step, "binding": {**asdict(bindings[run_key]), "decision": "D2"},
                "selected": list(selected), "citations": list(citations)}

    plan = {"sections": {**developer, **verifier, "finance": SECRET, "old-dev": OLD_DEV, "display": OPTIONAL},
            "markers": {"required": "ORD-D2-COMMON", "implementation": "ORD-DEV-TZ", "acceptance": "ORD-QA-A2",
                        "finance": "FIN-PRIVATE-ONLY", "old-dev": "ORD-DEV-OLD", "display": "ORD-OPTIONAL"},
            "turns": [turn("developer", "dev", developer, dev), turn("verifier", "check", verifier, qa)]}
    # Bounded history experiment: the old thread is a synthetic counterfactual. Products start a clean thread.
    origin.readers[MAIN].remove(DEV)
    reject("recheck_queued_after_loss", Pending, missing, lambda: assembly.deliver(DEV, "dev", dev, "old-delivery"))
    reject("new_bundle_after_revocation", Pending, missing, lambda: assembly.queue(DEV, "dev"))
    search("no_snippet_after_read_revoked", DEV, "dev", "开发时区", [])
    search("other_member_keeps_access", TEST, "check", "ORD-D2-COMMON", ["required"])
    assert assembly.deliver(TEST, "check", qa, "after-developer-loss") == verifier
    plan["turns"].extend([turn("old_thread_after_revoke", "dev", []), turn("new_thread_after_revoke", "dev", [])])
    save(out / "plan.json", plan)
    subprocess.run([sys.executable, HERE / "observe_context.py", "--codex", codex, "--plan", out / "plan.json",
                    "--output", out / "host.json"], check=True)

    host = read(out / "host.json")
    for selection, observed in zip(plan["turns"], host["turns"], strict=True):
        expected = {(c["heading"], c["sha256"]) for c in selection["citations"]}
        received = {(o["ref"], o["sha256"]) for o in observed["observations"] if o["location"] == "current"}
        assert (selection["step"], selection["binding"], expected) == (observed["step"], observed["binding"], received)
        observed["current_citations"] = selection["citations"]

    # A cached queue also binds current project membership and time-limited access.
    assembly.members["orders"].remove(TEST)
    reject("project_member_removed_before_delivery", Pending, missing,
           lambda: assembly.deliver(TEST, "check", qa, "after-project-loss"))
    reject("project_member_removed_before_search", Pending, missing, lambda: assembly.lookup(TEST, "check", "订单"))
    assembly.members["orders"].add(TEST)
    origin.read_until[TEST, QA] = 20
    origin.minute = 19
    assert assembly.queue(TEST, "check") == qa
    origin.minute = 20
    reject("source_grant_expired_while_queued", Pending, missing, lambda: assembly.deliver(TEST, "check", qa, "expired"))
    search("only_other_document_after_grant_expired", TEST, "check", "订单", ["required"])
    del origin.read_until[TEST, QA]  # the fixture source restores the verifier's ongoing read right

    # Removing a block from a still-readable document differs from revoking document access.
    before_removal = index.snapshots[QA]["acceptance"]
    qa_pending = assembly.queue(TEST, "check")
    origin.publish(QA, 2, [("summary", "核验摘要", "用例列表已由维护者撤回。")])
    index.refresh(QA, origin, "10:00")
    reject("deleted_section", Pending, missing, lambda: assembly.deliver(TEST, "check", qa_pending, "after-delete"))
    impacted_qa = assembly.affected(QA, "acceptance", before_removal.sha)
    assert [r for r, _ in impacted_qa] == ["check", "check", "check"]
    del origin.current[QA]
    reject("withdrawn_source", FileNotFoundError, QA, lambda: index.refresh(QA, origin, "10:05"))
    assert index.state[QA] == "withdrawn"
    reject("withdrawn_cached_input", Pending, missing, lambda: assembly.queue(TEST, "check"))
    search("remaining_source_after_qa_withdrawal", TEST, "check", "订单", ["required"])
    search("removed_qa_section_no_snippet", TEST, "check", "ORD-QA-A2", [])
    origin.unknown.add(MAIN)
    search("uncertain_source_no_snippet", TEST, "check", "订单", [])
    reject("permission_check_unavailable", Pending, missing, lambda: assembly.queue(TEST, "check"))
    reject("unreachable_source", ConnectionError, "mock source temporarily unreachable",
           lambda: index.refresh(MAIN, origin, "10:10"))
    assert index.checked[MAIN] == "09:11" and index.state[MAIN] == "unconfirmed"
    origin.unknown.clear()

    def advance(source, revision, offset):
        if source == MAIN and offset == 0:
            origin.on_page = None
            origin.publish(MAIN, 3, contract(DEV_TEXT, "开发时区"))
    origin.on_page = advance
    reject("changed_while_paging", ValueError, "source advanced while reading",
           lambda: index.refresh(MAIN, origin, "10:15"))
    assert index.revisions[MAIN] == 2 and index.checked[MAIN] == "09:11"
    index.refresh(MAIN, origin, "10:16")
    assert index.revisions[MAIN] == 3 and index.checked[MAIN] == "10:16"

    stable = index.snapshots[MAIN].copy()
    index.refresh(MAIN, origin, "10:17")
    assert index.snapshots[MAIN] == stable and index.checked[MAIN] == "10:17"

    subprocess.run([sys.executable, HERE / "contribution.py", "--fixtures", FIXTURES,
                    "--output", out / "contribution.json"], check=True)
    summary = {"issue": issue, "subject": "synthetic authority and actors", "initial_citations": {"dev": dev_old, "qa": qa_old},
               "selected_citations": {"dev": dev, "qa": qa}, "changed_section_dependents": changed_history,
               "deleted_section_dependents": impacted_qa, "controls": controls,
               "search_results": search_results, "last_checked": index.checked, "source_states": index.state, "host": host, "contribution": read(out / "contribution.json")}
    save(out / "summary.json", summary)
    print(json.dumps({"source_controls": controls, "host_receipt": "host.json",
                      "contribution_receipt": "contribution.json", "summary": "summary.json"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="new directory for synthetic evidence")
    parser.add_argument("--codex", default="codex", help="path to the 0.144.6 executable")
    args = parser.parse_args()
    run(args.output.resolve(), args.codex)
