"""Replay two scoped releases against real XLSX candidates and one actual Codex thread."""
import argparse
from contextlib import closing
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

from openpyxl import load_workbook

from asset_release import Catalog, digest


HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "topic-03a"
ISSUE = "order-export-verification"
NODE = "verify-order-export"


def load_admission():
    spec = importlib.util.spec_from_file_location("admission", PREVIOUS / "result-admission/test_admission.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def read_json(path):
    return json.loads(path.read_bytes())


def materialize(catalog, selection, target):
    rule, script = catalog.prepare(selection)
    target.mkdir()
    (target / "rule.md").write_bytes(rule)
    (target / "verify.py").write_bytes(script)
    write_json(target / "selection.json", asdict(selection))


def verify(workspace, material, selection, catalog):
    catalog.prepare(selection)  # Recheck the pin and withdrawal at this fixture’s launch point.
    script = material / "verify.py"
    if digest((material / "rule.md").read_bytes()) != selection.release.rule_sha:
        raise ValueError("prepared Rule changed before start")
    if digest(script.read_bytes()) != selection.release.script_sha:
        raise ValueError("prepared Script changed before start")
    output = workspace / "report.json"
    output.unlink(missing_ok=True)
    subprocess.run([sys.executable, "-I", script, workspace], cwd=material, check=True)
    result = read_json(output)
    if result["verifier_sha256"] != selection.release.script_sha or result["rule"] != selection.release.decision:
        raise ValueError("report does not identify the selected verifier and contract")
    return result


def test_rejection(action, exc, message):
    try:
        action()
    except exc as error:
        if str(error) == message:
            return message
        raise
    raise AssertionError(f"expected rejection: {message}")


def exercise(out, codex):
    out.mkdir(exist_ok=False)
    catalog = Catalog({"team": {"standards"}, "orders": {"order-owner", "project-maintainer"}},
                      {"orders": "team", "inventory": "team"})
    r1, r2 = [(HERE / "rules" / f"v{n}.md").read_bytes() for n in (1, 2)]
    s1 = (HERE / "verify_d1.py").read_bytes()
    s2 = (PREVIOUS / "order-export/verify.py").read_bytes()
    def publish_team():
        return catalog.publish("standards", "team", "v1", "D1", "team/order-export@1", r1, s1, None)
    def publish_project(actor="order-owner", version="v2", rule=r2, expected=None):
        return catalog.publish(actor, "orders", version, "D2", "orders/order-export@2", rule, s2, expected)
    publish_team()
    old = catalog.select("orders", "sop-before-D2", "D1")
    checks = {"unauthorized_publish": test_rejection(lambda: publish_project("author"), PermissionError, "publish scope")}
    release = publish_project()
    if publish_project(actor="project-maintainer") != release or release.published_by != "order-owner":
        raise AssertionError("publication replay changed the release")
    checks["same_version_changed"] = test_rejection(lambda: publish_project(rule=r2 + b"extra"), ValueError,
                                                    "version content or provenance changed")
    checks["stale_pointer"] = test_rejection(lambda: publish_project(version="v3"), ValueError,
                                             "publication head changed")
    if catalog.select("orders", old.instance, "D1") != old:
        raise AssertionError("an active instance lost its original selection")
    checks["in_flight_change"] = test_rejection(lambda: catalog.select("orders", old.instance, "D2"), ValueError,
                                               "successor instance required")
    new = catalog.select("orders", "sop-after-D2", "D2")
    other = catalog.select("inventory", "other-project", "D1")
    assert new.release == release and old.release == other.release and other.reason == "team default"
    checks["cross_project"] = test_rejection(lambda: catalog.select("inventory", "outside-D2", "D2"), ValueError,
                                             "required release unavailable for this decision")
    materialize(catalog, old, out / "R1")
    materialize(catalog, new, out / "R2")
    # Produce the unchanged 3A candidates and the independent reference report.
    orders = out / "orders"
    subprocess.run([sys.executable, PREVIOUS / "order-export/run.py", orders], check=True, stdout=subprocess.DEVNULL)
    live = out / "C2-independent-check"
    shutil.copytree(orders / "C2", live)
    def binding(selection, run, attempt):
        return {"issue": ISSUE, "node": NODE, "instance": selection.instance, "run": run, "attempt": attempt,
                "expected_rule_sha": selection.release.rule_sha}
    before = binding(old, "observe-before-D2", 1)
    current = binding(new, "verify-C2", 2)
    stages = ("open_with_R1", "same_thread_after_R2_write", "same_thread_with_explicit_R2")
    bindings = dict(zip(stages, (before, current, current), strict=True))
    write_json(out / "turn-bindings.json", bindings)
    host = out / "host.json"
    subprocess.run([sys.executable, HERE / "observe_rule.py", "--codex", codex, "--r1", out / "R1/rule.md",
                    "--r2", out / "R2/rule.md", "--bindings", out / "turn-bindings.json", "--output", host], check=True)
    observations = read_json(host)
    assert observations["rule_sha256"] == {"R1": old.release.rule_sha, "R2": new.release.rule_sha}
    turns = observations["turns"]
    assert [turn["step"] for turn in turns] == list(stages)

    def authorize_check(turn):
        # This scenario's execution contract calls for the new decision in this turn.
        if turn["binding"] != current or turn["binding"]["expected_rule_sha"] != new.release.rule_sha:
            raise ValueError("turn binding mismatch")
        if not any(item["rule_sha256"] == new.release.rule_sha and item["occurrence"] == "current_submission"
                   for item in turn["materials_in_model_request"]):
            raise ValueError("current Rule input unconfirmed")
    checks["stale_turn"] = test_rejection(lambda: authorize_check(turns[1]), ValueError,
                                         "current Rule input unconfirmed")
    authorize_check(turns[2])
    results = {"C2_D2": verify(live, out / "R2", new, catalog)}

    # Negative control derived from C2. This is a separate D1 sample; preserve the genuine C2.
    four = out / "four-column-control"
    shutil.copytree(live, four)
    for path in four.glob("*.xlsx"):
        workbook = load_workbook(path)
        workbook["Orders"].delete_cols(5)
        workbook.save(path)
        workbook.close()
    bind = {"issue": ISSUE, "node": NODE, "candidate": "four-column-control", "run": "control-d1",
            "attempt": 1, "rule": "D1", "input_origin_commit": results["C2_D2"]["commit"]}
    write_json(four / "binding.json", bind)
    results["four_D1"] = verify(four, out / "R1", old, catalog)
    write_json(four / "binding.json", {**bind, "rule": "D2", "run": "control-d2", "attempt": 2})
    results["four_D2"] = verify(four, out / "R2", new, catalog)
    assert [(r["A2"], r["A3"], r["verdict"]) for r in results.values()] == [
        (True, True, "pass"), (True, True, "pass"), (True, False, "rework")]

    c2 = results["C2_D2"]
    raw = (live / "report.json").read_bytes()
    assert raw == (PREVIOUS.parents[1] / "docs/research/topic-03a/fixtures/order-export-c2.json").read_bytes()
    admission = load_admission()
    dbpath = out / "admission.db"
    with closing(admission.connect(dbpath)) as db, db:
        db.executescript(admission.SCHEMA)
        # The expected verifier comes from the selected release. Identity, candidate and
        # Grant come from the pre-existing Dispatch fixture, independently of the report.
        db.execute("INSERT INTO dispatch VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   ("verify-C2", ISSUE, NODE, 2, "C2", new.release.decision, admission.COMMITS[1],
                    "verifier", 1, 1, 1, 3, new.release.script_sha))
        db.execute("INSERT INTO delegation VALUES(?,?,?,?,?)", (ISSUE, NODE, 3, 1, "submit-report"))
        db.execute("INSERT INTO current_node VALUES(?,?,?)", (ISSUE, NODE, "verify-C2"))
        for name in admission.FILES:
            db.execute("INSERT INTO required_artifact VALUES(?,?)", ("verify-C2", name))
            admission.supply_file(db, "verify-C2", name, live / name)
    def submit(payload):
        return admission.admit(dbpath, "verifier", "verify-C2", payload, digest(payload))
    wrong = json.dumps({**c2, "verifier_sha256": old.release.script_sha}).encode()
    checks["old_verifier_on_C2"] = submit(wrong)
    assert checks["old_verifier_on_C2"] == "verifier mismatch"
    assert [submit(raw), submit(raw)] == ["current", "duplicate"]
    with closing(admission.connect(dbpath)) as db:
        assert db.execute("SELECT count(*) FROM consumed").fetchone()[0] == 1

    saved = catalog.content[new.release.script_sha]
    catalog.content[new.release.script_sha] = s1
    checks["damaged_material"] = test_rejection(lambda: catalog.prepare(new), ValueError, "material digest mismatch")
    catalog.content[new.release.script_sha] = saved
    catalog.withdraw("order-owner", "orders", "v2")
    checks["withdrawn_pin"] = test_rejection(lambda: verify(live, out / "R2", new, catalog), PermissionError, "withdrawn before execution")
    checks["no_implicit_downgrade"] = test_rejection(lambda: catalog.select("orders", "after-withdrawal", "D2"),
                                                    ValueError, "required release unavailable for this decision")
    assert catalog.withdrawn["orders", "v2"] == "order-owner"
    summary = {"withdrawn_by": catalog.withdrawn["orders", "v2"], "selections": [asdict(old), asdict(new), asdict(other)], "host": observations["host"],
               "observed_turns": turns, "checks": checks, "results": {
                   name: {k: report[k] for k in ("rule", "run", "candidate", "A2", "A3", "verdict", "verifier_sha256")}
                   for name, report in results.items()}, "admission": ["current", "duplicate"],
               "consumed": 1, "C2_report_sha256": digest(raw)}
    write_json(out / "summary.json", summary)
    print(json.dumps({"verdicts": {n: r["verdict"] for n, r in results.items()}, "codex_requests": len(turns),
                      "C2_consumed": 1, "negative_controls": checks, "summary": str(out / "summary.json")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="a new directory for the experiment")
    parser.add_argument("--codex", default="codex", help="Codex 0.144.6 executable")
    args = parser.parse_args()
    exercise(args.output.resolve(), args.codex)
