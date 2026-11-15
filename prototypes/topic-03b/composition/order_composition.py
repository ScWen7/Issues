"""Exercise two order roles under full, tight, insufficient and conflicting selections."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
import subprocess
import sys

from selection import Contract, Material, select

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / "knowledge"), str(HERE.parent)]
import order_knowledge as knowledge
from asset_release import digest
from docx_fixture import Origin
from source_context import Assembly, Binding, Index

ORDERS = REPO / "prototypes/topic-03a/order-export"
FIXTURES = REPO / "docs/research/topic-03a/fixtures"
RULE = "d2-rule"
COMMON = "business-section"
EXTRA = "fast-export-v1"
CORRECTED = "fast-export-v2"
ROLES = {"developer": ("implement-order-export", knowledge.DEV, "export-workbook"),
         "verifier": ("verify-order-export", knowledge.TEST, "verify-workbook")}


def read(path):
    return json.loads(path.read_bytes())


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def context(c2):
    """Resolve existing D2 and the V0.2 source sections under current recipient rights."""
    origin = Origin()
    origin.readers = {knowledge.MAIN: {knowledge.DEV, knowledge.TEST}, knowledge.QA: {knowledge.TEST}}
    origin.publish(knowledge.MAIN, 2, knowledge.contract(knowledge.DEV_TEXT, "开发时区", extra=True))
    origin.publish(knowledge.QA, 1, [("acceptance", "独立核验", knowledge.CHECK)])
    index = Index()
    for source in origin.readers:
        index.refresh(source, origin, "before-dispatch")
    bindings = {r: Binding(person, "orders", r, c2["issue"], node, r, c2["attempt"])
                for r, (node, person, _) in ROLES.items()}
    plans = {("orders", "developer"): ((knowledge.MAIN, "required"), (knowledge.MAIN, "implementation")),
             ("orders", "verifier"): ((knowledge.MAIN, "required"), (knowledge.QA, "acceptance"))}
    assembly = Assembly(index, origin, bindings, {"orders": set(origin.readers[knowledge.MAIN])}, plans)
    return assembly


def catalog(sections):
    d2 = (HERE.parent / "rules/v2.md").read_bytes().decode()
    assert digest(d2.encode()) == c2_rule_digest()
    entries = [
        Material(RULE, "rule", d2, "按 D2 核对订单导出", "orders/order-export@2", (("payment-column", "include"),)),
        Material("developer-role", "role", "实现订单导出并交付工作簿，保留各账号的导出结果。职责代号 ROLE-BUILD。", "ROLE-BUILD", "orders/developer@1"),
        Material("verifier-role", "role", "独立检查候选工作簿，分别报告可见范围和付款时间两项结果。职责代号 ROLE-CHECK。", "ROLE-CHECK", "orders/verifier@1"),
        Material("build-orders", "skill", "依据可见范围生成含付款时间的五列工作簿；无权导出时返回拒绝。操作代号 XLSX-BUILD。",
                 "XLSX-BUILD", "orders/build-workbook@2", (("payment-column", "include"),), "export-workbook"),
        Material("inspect-orders", "skill", "读取实际 XLSX 核对账号范围、五列表头和付款时间，保留 A2 与 A3。操作代号 XLSX-CHECK。",
                 "XLSX-CHECK", "orders/inspect-workbook@2", (("payment-column", "include"),), "verify-workbook"),
        Material("build-playbook", "playbook", "先试含已付款与未付款的东区样本，再逐个账号导出留样。做法代号 HOW-BUILD。",
                 "HOW-BUILD", "team/export-method@1"),
        Material("check-playbook", "playbook", "可先比对普通区域与跨区账号的订单清单，再检查两个付款状态。做法代号 HOW-CHECK。",
                 "HOW-CHECK", "team/check-method@1"),
        Material(EXTRA, "skill", "快速导出沿用旧四列，省略付款时间列。操作代号 FAST-FOUR。", "FAST-FOUR",
                 "orders/fast-export@1", (("payment-column", "omit"),)),
        Material(CORRECTED, "skill", "快速导出的样本仍遵循现行五列并包含付款时间。操作代号 FAST-FIVE。", "FAST-FIVE",
                 "orders/fast-export@2", (("payment-column", "include"),)),
    ]
    shared = sections["developer"][0]
    assert sections["verifier"][0] == shared
    for ref, section, marker in [(COMMON, shared, "ORD-D2-COMMON"),
                                 ("developer-section", sections["developer"][1], "ORD-DEV-TZ"),
                                 ("verifier-section", sections["verifier"][1], "ORD-QA-A2")]:
        entries.append(Material(ref, "knowledge", section.body, marker,
                                f"{section.source}@{section.revision}#{section.heading}"))
    return {m.ref: m for m in entries}


def c2_rule_digest():
    evidence = read(REPO / "docs/research/topic-03b/fixtures/order-release.json")
    return evidence["selections"][1]["release"]["rule_sha"]


def repair_pin(actor, role, contract, materials, decision):
    """One authorized project repair under the existing, unchanged D2 decision."""
    if actor != "orders-maintainer":
        raise PermissionError("project publication and selection required")
    if decision != "D2" or EXTRA not in contract.required or CORRECTED in contract.required:
        raise ValueError("unexpected decision or predecessor")
    fixed = replace(contract, required=tuple(CORRECTED if r == EXTRA else r for r in contract.required))
    record = {"by": actor, "role": role, "decision": decision, "disposition": "replace incompatible project Skill",
              "prior": materials[EXTRA].source, "replacement": materials[CORRECTED].source,
              "old_sha256": materials[EXTRA].digest, "new_sha256": materials[CORRECTED].digest}
    return fixed, record


def prepare(c2, materials):
    cases, repairs, controls = [], [], []
    issued = {}
    pins = {ref: m.publication_digest for ref, m in materials.items()}
    for role, (node, actor, operation) in ROLES.items():
        skill = "build-orders" if role == "developer" else "inspect-orders"
        need = (RULE, COMMON, role + "-section", role + "-role", skill)
        method = "build-playbook" if role == "developer" else "check-playbook"
        basic = Contract(need, (method,), operation)
        conflicting = replace(basic, required=(*need, EXTRA))
        corrected, repair = repair_pin("orders-maintainer", role, conflicting, materials, "D2")
        repairs.append(repair)
        required_size = sum(materials[r].size for r in need)
        full_size = required_size + materials[method].size
        readable = {*need, method, EXTRA, CORRECTED}
        ops = {operation}
        rows = (
            ("full", basic, full_size),
            ("minimum", basic, required_size),
            ("too-small", basic, required_size - 1),
            ("required-conflict", conflicting, full_size + materials[EXTRA].size),
            ("corrected", corrected, full_size + materials[CORRECTED].size),
        )
        for label, contract, cap in rows:
            identifier = role + "-" + label
            binding = {"issue": c2["issue"], "node": node, "attempt": c2["attempt"], "run": "study-" + identifier,
                       "member": actor, "project": "orders", "role": role, "decision": c2["rule"], "candidate": "C2"}
            issued[binding["run"]] = (binding.copy(), contract, cap)
            result = select(issued, binding, actor, materials, pins, readable, ops)
            expected = {"full": [*need, method], "minimum": list(need), "too-small": [],
                        "required-conflict": [], "corrected": [*need, CORRECTED, method]}[label]
            assert result["selected"] == expected and (result["status"] == "ready") == bool(expected)
            if label == "minimum":
                assert result["used_bytes"] == cap and result["omitted"] == {method: "optional material exceeds remaining budget"}
            if label == "required-conflict":
                assert result["conflict"]["subject"] == "payment-column" and EXTRA in result["conflict"]["refs"]
            if label == "too-small":
                assert result["required_bytes"] == cap + 1
            cases.append({"id": identifier, "binding": binding, **result})
        # Exercise the full-work contract under alternate rights and source states.
        binding = cases[-len(rows)]["binding"]

        def probe(name, contract=basic, rights=readable, grants=ops, digests=pins, principal=actor,
                  catalog=materials, requested_changes=None):
            control_binding = {**binding, "run": f"control-{role}-{name}"}
            issued[control_binding["run"]] = (control_binding.copy(), contract, 4096)
            presented = {**control_binding, **(requested_changes or {})}
            result = select(issued, presented, principal, catalog, digests, rights, grants)
            controls.append({"role": role, "case": name, **result})
            return result

        assert probe("unknown-run", requested_changes={"run": "missing"})["reason"] == "dispatch access unavailable"
        assert probe("changed-dispatch", requested_changes={"project": "other", "attempt": 7})["reason"] == "dispatch access unavailable"
        assert probe("conflict-manifest-altered", conflicting,
                     catalog={**materials, EXTRA: replace(materials[EXTRA], claims=())})["reason"] == "required capability or material unavailable"
        access_tamper = {**materials, skill: replace(materials[skill], operation=None)}
        assert probe("operation-manifest-altered", catalog=access_tamper)["reason"] == "required capability or material unavailable"
        assert probe("wrong-principal", principal="unassigned")["reason"] == "dispatch access unavailable"
        assert probe("no-execution-grant", grants=set())["status"] == "blocked"
        assert probe("required-source-lost", rights=readable - {COMMON})["status"] == "blocked"
        assert probe("required-pin-mismatch", digests={**pins, skill: "old"})["status"] == "blocked"
        other_skill = "inspect-orders" if role == "developer" else "build-orders"
        alternate = replace(basic, optional=(other_skill, method))
        assert probe("role-does-not-grant-other-operation", alternate, rights=readable | {other_skill})["selected"] == [*need, method]
        assert probe("optional-no-read", rights=readable - {method})["selected"] == list(need)
        assert probe("duplicate-source-reference", replace(basic, optional=(COMMON, method, method)))["selected"] == [*need, method]
        assert probe("optional-conflicts-with-D2", replace(basic, optional=(EXTRA, method)))["omitted"] == {
            EXTRA: "conflicts with selected instruction"}
        assert probe("required-conflict-reversed", replace(conflicting, required=tuple(reversed(conflicting.required))))["status"] == "blocked"
        try:
            repair_pin(actor, role, conflicting, materials, "D2")
        except PermissionError:
            controls.append({"role": role, "case": "worker-cannot-change-pin", "status": "denied"})
        else:
            raise AssertionError("worker changed project pin")
    try:
        replace(materials[EXTRA], claims=(("payment-column", "include"), ("payment-column", "omit")))
    except ValueError as error:
        assert str(error) == "material declares incompatible values"
        controls.append({"case": "internally-inconsistent-release", "status": "denied"})
    else:
        raise AssertionError("ambiguous material admitted")
    return cases, repairs, controls, issued


def run_process(*args, cwd=None, allowed=(0,)):
    p = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)
    if p.returncode not in allowed:
        raise RuntimeError(f"{p.args[1]}: exit {p.returncode}: {p.stderr}")
    return p.returncode


def inspect_reports(out, c2, host):
    # The 3A fixture supplies fixed candidate worktrees and input data, independently of the model reply.
    source = out / "orders"
    run_process(ORDERS / "run.py", source)
    checkout = source / "worktree-C2"
    c1_path = source / "C1/report.json"
    assert c1_path.read_bytes() == (FIXTURES / "order-export-c1.json").read_bytes()
    assert (source / "C2/report.json").read_bytes() == (FIXTURES / "order-export-c2.json").read_bytes()
    assert digest((ORDERS / "verify.py").read_bytes()) == c2["verifier_sha256"]
    receipts = {}
    by_id = {r["id"]: r for r in host["cases"]}
    for label in ("full", "minimum", "corrected"):
        dev, qa = (by_id[f"{r}-{label}"] for r in ("developer", "verifier"))
        assert dev["status"] == qa["status"] == "ready"
        build_run, verify_run = "script-export-" + label, "script-verify-" + label
        location = out / label
        location.mkdir()
        exits = {}
        for role in ("east", "west", "cross", "viewer"):
            exits[role] = run_process(checkout / "exporter.py", role, location / (role + ".xlsx"), cwd=checkout, allowed=(0, 3))
        write(location / "export-exits.json", exits)
        binding = read(source / "C2/binding.json")
        assert binding["issue"] == qa["binding"]["issue"] and binding["candidate"] == dev["binding"]["candidate"]
        write(location / "binding.json", {**binding, "run": verify_run})
        run_process(ORDERS / "verify.py", location)
        report = read(location / "report.json")
        assert {**report, "run": c2["run"]} == c2
        receipts[label] = {"developer_turn": dev["turn_id"], "verifier_turn": qa["turn_id"],
                           "developer_dispatch": dev["binding"]["run"], "verifier_dispatch": qa["binding"]["run"],
                           "producer_run": build_run, "verification_run": report["run"],
                           "execution_source": "research harness, separate Python processes",
                           "producer_sha256": digest((checkout / "exporter.py").read_bytes()),
                           "verifier_sha256": report["verifier_sha256"], "report_sha256": digest((location / "report.json").read_bytes()),
                           "artifacts": report["artifacts"], "candidate_commit": report["commit"], "exits": exits,
                           "A2": report["A2"], "A3": report["A3"], "verdict": report["verdict"]}
    # The same pinned verifier independently rechecks the C1 negative control.
    old = out / "cross-region-control"
    shutil.copytree(source / "C1", old)
    (old / "report.json").unlink()
    original = read(old / "binding.json")
    write(old / "binding.json", {**original, "run": "control-recheck-C1"})
    run_process(ORDERS / "verify.py", old)
    report = read(old / "report.json")
    assert {**report, "run": original["run"]} == read(c1_path) and report["verdict"] == "rework"
    return receipts, {k: report[k] for k in ("candidate", "commit", "A2", "A3", "run", "verdict")}


def execute(out, codex):
    out.mkdir()
    c2 = read(FIXTURES / "order-export-c2.json")
    from observe_composition import run_host
    assembly = context(c2)
    sections = {r: assembly.select(person, r) for r, (_, person, _) in ROLES.items()}
    materials = catalog(sections)
    cases, repairs, controls, issued = prepare(c2, materials)
    pins = {ref: m.publication_digest for ref, m in materials.items()}
    access = {}
    for role, (_, actor, operation) in ROLES.items():
        base = next(c for c in cases if c["id"] == role + "-full")
        access[actor] = (set(base["selected"]) | {EXTRA, CORRECTED}, {operation})
        label = role + ("-source-revoked" if role == "developer" else "-tool-revoked")
        binding = {**base["binding"], "run": "study-" + label}
        cases.append({**base, "id": label, "binding": binding})
        _, contract, cap = issued[base["binding"]["run"]]
        issued[binding["run"]] = (binding.copy(), contract, cap)
    finals = []
    def recheck(case):
        binding = case["binding"]
        actor, role = binding["member"], binding["role"]
        rights, operations = access[actor]
        if case["id"] == "developer-source-revoked":
            assembly.origin.readers[knowledge.MAIN].remove(actor)
        if case["id"] == "verifier-tool-revoked":
            operations.remove("verify-workbook")
        citations = tuple(s.cite() for s in sections[role])
        try:
            current = assembly.select(actor, role)
            valid = tuple(s.cite() for s in current) == citations
        except knowledge.Pending:
            valid = False
        if valid:
            result = select(issued, binding, actor, materials, pins, rights, operations)
        else:
            result = {"status": "blocked", "selected": [], "used_bytes": 0, "reason": "source selection no longer available"}
        if result["status"] == "ready" and result["selected"] != case["selected"]:
            result = {"status": "blocked", "selected": [], "used_bytes": 0, "reason": "queued selection changed"}
        final = {**case, **result}
        finals.append(final)
        return final

    plan = {"materials": {k: asdict(m) for k, m in materials.items()}, "cases": cases}
    host = run_host(codex, plan, before_dispatch=recheck)
    # This replay plan is the authorized test operator's fixture after the final checks.
    write(out / "plan.json", {**plan, "cases": finals})
    write(out / "host.json", host)
    assert len(finals) == 12
    assert all(c["status"] == "ready" for c in cases[-2:]) and all(c["status"] == "blocked" for c in finals[-2:])
    assert finals[-2]["reason"] == "source selection no longer available"
    assert finals[-1]["reason"] == "required capability or material unavailable"
    for case, actual in zip(finals, host["cases"], strict=True):
        assert all(actual[k] == case[k] for k in ("id", "binding", "status", "selected"))
        assert actual["observed_sha256"] == {ref: materials[ref].digest for ref in case["selected"]}
        assert actual["requests_after"] - actual["requests_before"] == int(case["status"] == "ready")
    receipts, control = inspect_reports(out, c2, host)
    citations = {role: [s.cite() for s in value] for role, value in sections.items()}
    summary = {"material_versions": {ref: {"source": m.source, "sha256": m.digest, "publication_sha256": m.publication_digest, "body_bytes": m.size,
                                           "kind": m.kind, "claims": m.claims} for ref, m in materials.items()},
               "source_sections": citations, "dispatched_cases": finals, "project_repairs": repairs,
               "changed_after_queue": [{"id": c["id"], "queued": "ready", "queued_refs": c["selected"],
                                        "final": f["status"], "reason": f["reason"]} for c, f in zip(cases[-2:], finals[-2:])],
               "selection_controls": controls, "host": host, "verified_candidates": receipts, "C1_control": control}
    write(out / "summary.json", summary)
    print(json.dumps({"scenarios": len(cases), "selection_controls": len(controls), "host_requests": host["requests"],
                      "C2_checks": len(receipts), "C1": control["verdict"]}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path, help="new evidence directory")
    ap.add_argument("--codex", default="codex")
    args = ap.parse_args()
    execute(args.output.resolve(), args.codex)
