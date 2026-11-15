"""Exercise the same order capability in two native hosts and admit its evidence once."""
import argparse
from contextlib import closing
from dataclasses import dataclass
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys

from order_tool import HERE, PERSONAL, PROJECT, SCHEMA, TABLES, TOOL, VERIFIER, encoded, inspect, sha

sys.path.insert(0, str(HERE.parent))
from order_release import load_admission

ADMISSION = load_admission()
ROOT = HERE.parents[2]
ORDERS = ROOT / "prototypes/topic-03a/order-export"
FIXTURES = ROOT / "docs/research/topic-03a/fixtures"


def write(path, obj):
    path.write_text(json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n")


def read(path):
    return json.loads(path.read_bytes())


def frozen_contract(candidate):
    ref = read(FIXTURES / f"order-export-{candidate.lower()}.json")
    keys = ("issue", "node", "attempt", "candidate", "rule", "commit", "artifacts", "verifier_sha256")
    return {**{k: ref[k] for k in keys}, "provider": PROJECT, "tool": TOOL,
            "schema_sha256": sha(encoded(SCHEMA)), "service_sha256": sha((HERE / "order_tool.py").read_bytes())}


@dataclass
class Run:
    run: str
    member: str
    runtime: str
    epoch: int
    contract: dict
    providers: dict

    def binding(self):
        return {"run": self.run, "member": self.member, "runtime": self.runtime, "epoch": self.epoch,
                **{k: self.contract[k] for k in ("issue", "node", "attempt", "candidate", "rule", "commit")},
                "contract_sha256": sha(encoded(self.contract))}


class Study:
    def __init__(self, root, orders, codex, claude):
        self.root, self.orders = root, orders
        root.mkdir()
        self.db = root / "authority.sqlite"
        self.results = self.db  # Share one transaction for native-tool authority and the existing 3A dispatcher.
        self.binaries = {"codex": codex, "claude": claude}
        self.observations, self.decisions = [], []
        self.allowed_launch = {}
        with sqlite3.connect(self.db) as conn:
            conn.executescript(TABLES)
        with closing(ADMISSION.connect(self.results)) as conn, conn:
            conn.executescript(ADMISSION.SCHEMA)
            conn.execute("""CREATE TABLE host_proof(receipt TEXT PRIMARY KEY, run TEXT NOT NULL, call_id TEXT NOT NULL,
                         host TEXT NOT NULL, session TEXT NOT NULL, turn TEXT NOT NULL, value_hash TEXT NOT NULL,
                         UNIQUE(host, session, turn, call_id))""")

    def credentials(self, run, member, runtime, epoch):
        providers = {}
        credential_hash = None
        for alias, service in [("project_orders", PROJECT), ("personal_orders", PERSONAL)]:
            token = secrets.token_urlsafe(24)
            profile = {"run": run, "member": member, "runtime": runtime, "epoch": epoch, "service": service,
                       "token": token, "authority": str(self.db), "artifacts": str(self.orders)}
            file = self.root / f"{run}-{alias}.json"
            file.touch(mode=0o600, exist_ok=False)
            write(file, profile)
            providers[alias] = {"command": sys.executable, "args": [str(HERE / "order_tool.py"), str(file)]}
            if service == PROJECT:
                credential_hash = sha(token.encode())
        return providers, credential_hash

    def issue(self, run, host, epoch, candidate="C2", prior=None):
        member = {"codex": "order-member-A", "claude": "order-member-B"}[host]
        runtime = "member-runtime-" + host
        contract = frozen_contract(candidate)
        if prior is not None:
            assert prior.contract == contract and prior.epoch + 1 == epoch and prior.run != run
        else:
            assert epoch == 1
        providers, credential_hash = self.credentials(run, member, runtime, epoch)
        record = Run(run, member, runtime, epoch, contract, providers)
        issue, node = contract["issue"], contract["node"]
        with closing(ADMISSION.connect(self.results)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            current = conn.execute("SELECT run FROM current_node WHERE issue=? AND node=?", (issue, node)).fetchone()
            if (current[0] if current else None) != (prior.run if prior else None):
                raise ValueError("dispatch owner changed")
            if prior:
                conn.execute("UPDATE leases SET active=0 WHERE run=?", (prior.run,))
                conn.execute("UPDATE dispatch SET task_active=0 WHERE run=?", (prior.run,))
            conn.execute("INSERT INTO leases VALUES(?,?,?,?,?,?,1)",
                         (run, member, runtime, epoch, encoded(contract).decode(), credential_hash))
            conn.execute("INSERT INTO dispatch VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                         (run, issue, node, contract["attempt"], candidate, contract["rule"], contract["commit"],
                          member, 1, 1, 1, epoch, contract["verifier_sha256"]))
            conn.execute("INSERT OR REPLACE INTO current_node VALUES(?,?,?)", (issue, node, run))
            conn.execute("INSERT OR REPLACE INTO delegation VALUES(?,?,?,?,?)", (issue, node, epoch, 1, "submit-report"))
            for name in ADMISSION.FILES:
                conn.execute("INSERT INTO required_artifact VALUES(?,?)", (run, name))
                ADMISSION.supply_file(conn, run, name, self.orders / candidate / name)
        self.allowed_launch[run] = sha(encoded(record.providers["project_orders"]))
        return record

    def revoke(self, record):
        with sqlite3.connect(self.db) as conn:
            conn.execute("UPDATE leases SET active=0 WHERE run=?", (record.run,))
            conn.execute("UPDATE dispatch SET task_active=0 WHERE run=?", (record.run,))

    def interface(self, launch):
        # Independent stdio discovery of this exact launch profile; no model or tool call.
        messages = [
            {"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26",
             "capabilities": {}, "clientInfo": {"name": "order-discovery", "version": "1"}}},
            {"method": "notifications/initialized"},
            {"id": 2, "method": "tools/list", "params": {}},
        ]
        wire = b"".join(encoded({"jsonrpc": "2.0", **m}) + b"\n" for m in messages)
        completed = subprocess.run([launch["command"], *launch["args"]], input=wire, capture_output=True,
                                   check=True, timeout=10)
        hello, catalog = [json.loads(line) for line in completed.stdout.splitlines()]
        assert hello["id"] == 1 and catalog["id"] == 2
        return hello["result"]["serverInfo"]["name"], catalog["result"]["tools"]

    def invoke(self, record, host, label, *, missing=False, revoke_in_flight=False, collision=False, schema_drift=False, personal_request=False,
               adapter_override=None):
        from codex_tool import run_codex
        from claude_tool import run_claude
        assert record.runtime == "member-runtime-" + host
        servers = dict(record.providers)
        if missing:
            del servers["project_orders"]
        if collision:
            # Member already owns this alias. Check its actual launch target before passing any config to a host.
            servers["project_orders"] = servers["personal_orders"]
        if "project_orders" in servers and sha(encoded(servers["project_orders"])) != self.allowed_launch[record.run]:
            self.observations.append({"id": label, "binding": record.binding(), "placement": "preflight",
                                      "reason": "project alias bound to different launch target", "model_requests": 0})
            return None

        if "project_orders" in servers:
            path = Path(servers["project_orders"]["args"][-1])
            original_profile = path.read_bytes()
            try:
                if schema_drift:
                    write(path, {**json.loads(original_profile), "interface": "incompatible"})
                provider, entries = self.interface(servers["project_orders"])
                matched = [t for t in entries if t["name"] == record.contract["tool"]]
                if (provider != record.contract["provider"] or len(matched) != 1 or
                        sha(encoded(matched[0])) != record.contract["schema_sha256"] or
                        sha((HERE / "order_tool.py").read_bytes()) != record.contract["service_sha256"]):
                    self.observations.append({"id": label, "binding": record.binding(), "placement": "preflight",
                                              "reason": "provider or interface changed", "model_requests": 0})
                    return None
            finally:
                if schema_drift:
                    path.write_bytes(original_profile)
        case = {"id": label, "binding": record.binding(), "servers": servers, "expected_server": "project_orders",
                "tool": TOOL, "expected_input_schema": SCHEMA["inputSchema"], "arguments": {"candidate": record.contract["candidate"]}}
        if personal_request:
            case["model_request_server"] = "personal_orders"
        with sqlite3.connect(self.db) as conn:
            start = conn.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
        hook = (lambda: self.revoke(record)) if revoke_in_flight else None
        adapter = adapter_override or (run_codex if host == "codex" else run_claude)
        actual = adapter(self.binaries[host], case, before_call=hook)
        with sqlite3.connect(self.db) as conn:
            events = conn.execute("SELECT receipt,service,run,outcome,result_hash FROM events WHERE seq>? ORDER BY seq",
                                  (start,)).fetchall()
        if missing:
            assert actual["status"] == "blocked" and actual["model_requests"] == 0 and not events
        elif personal_request:
            assert actual["model_requests"] == 2 and not events and actual["result"]["status"] == "host_rejected"
        else:
            value = actual["result"]
            assert actual["status"] == "completed" and actual["model_requests"] == 2 and actual["call_id"]
            assert actual["arguments"] == case["arguments"] and actual["selected_tool"] and len(events) == 1
            digest_on_wire = actual.get("result_sha256", actual.get("result_text_sha256"))
            assert digest_on_wire == sha(encoded(value))
            if events[0] != (value["receipt"], PROJECT, record.run, value["status"], digest_on_wire):
                raise ValueError("service receipt differs from native tool result")
            if revoke_in_flight:
                assert value.keys() == {"receipt", "status"} and value["status"] == "denied"
            else:
                report = value["report"]
                assert value["provider"] == PROJECT and value["status"] == "ok" and report["run"] == record.run
                expected = read(FIXTURES / f"order-export-{record.contract['candidate'].lower()}.json")
                assert {**report, "run": expected["run"]} == expected
            native_session = actual.get("thread_id") or actual["session_id"]
            native_turn = actual.get("turn_id") or actual["prompt_id"]
            with sqlite3.connect(self.db) as conn:
                conn.execute("INSERT INTO host_proof VALUES(?,?,?,?,?,?,?)",
                             (value["receipt"], record.run, actual["call_id"], host, native_session, native_turn, digest_on_wire))
        self.observations.append({"id": label, "host": host, "binding": record.binding(), "native": actual,
                                  "service_events": [{"receipt": receipt, "service": service, "run": run, "outcome": outcome,
                                                      "result_sha256": h} for receipt, service, run, outcome, h in events]})
        return actual

    def submit(self, record, actual):
        value = actual["result"]
        proof = (record.run, actual["call_id"], sha(encoded(value)))
        with sqlite3.connect(self.db) as conn:
            verified = conn.execute("SELECT run,call_id,value_hash FROM host_proof WHERE receipt=?",
                                    (value.get("receipt"),)).fetchone()
        if value.get("status") != "ok" or verified != proof:
            disposition = "no verified tool result"
        else:
            raw = encoded(value["report"])
            disposition = ADMISSION.admit(self.results, record.member, record.run, raw, sha(raw))
        self.decisions.append({"source_run": record.run, "call_id": actual["call_id"], "disposition": disposition})
        return disposition

    def counts(self):
        with closing(ADMISSION.connect(self.results)) as conn:
            return {table: conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in ("consumed", "artifact")}

    def accepted_result(self, record, actual):
        """Read the persisted result back, tracing its bytes to the native call and the node."""
        value = actual["result"]
        report = value["report"]
        with closing(ADMISSION.connect(self.db)) as conn:
            proof, = conn.execute("""
                SELECT p.run, p.host, p.session, p.turn, p.call_id, p.receipt, e.service, e.result_hash
                FROM host_proof p JOIN events e ON p.receipt=e.receipt AND p.run=e.run AND p.value_hash=e.result_hash
                WHERE p.receipt=? AND e.outcome='ok'""", (value["receipt"],))
            receipt, = conn.execute("SELECT run,slot,sha256,payload,placement FROM receipt")
            consumed, = conn.execute("SELECT issue,node,attempt,run,verdict FROM consumed")
            artifacts = [dict(row) for row in conn.execute(
                "SELECT name,bytes,digest AS sha256 FROM artifact WHERE run=? ORDER BY name", (record.run,))]
        assert (proof["run"], proof["call_id"], proof["service"]) == (record.run, actual["call_id"], PROJECT)
        assert proof["result_hash"] == sha(encoded(value))
        assert tuple(receipt) == (record.run, ADMISSION.SLOT, sha(encoded(report)), encoded(report), "current")
        assert dict(consumed) == {key: report[key] for key in ("issue", "node", "attempt", "run", "verdict")}
        assert artifacts == sorted(record.contract["artifacts"], key=lambda item: item["name"])
        assert self.counts() == {"consumed": 1, "artifact": len(ADMISSION.FILES)}
        return {"call": dict(proof), "slot": receipt["slot"], "report_sha256": receipt["sha256"],
                "placement": receipt["placement"], "consumed": dict(consumed), "artifacts": artifacts}

    def summary(self):
        return {"cases": self.observations, "admission": self.decisions, "counts": self.counts()}


def recover_blocked(study, origin_host, replacement_host, blocker):
    """An otherwise authorized owner hands off immediately after a single capability failure."""
    original = study.issue("original-" + origin_host, origin_host, 1)
    if blocker == "missing":
        blocked = study.invoke(original, origin_host, "project-tool-missing", missing=True)
        assert blocked["status"] == "blocked" and blocked["model_requests"] == 0
        assert blocked["configured_catalog"].get("personal_orders") == [TOOL]
        assert blocked["reason"] == "required project tool unavailable" and blocked["call_id"] is None
    elif blocker == "alias-collision":
        assert study.invoke(original, origin_host, "project-alias-points-to-personal", collision=True) is None
        observed = study.observations[-1]
        assert observed["placement"] == "preflight" and observed["model_requests"] == 0
        assert observed["reason"] == "project alias bound to different launch target"
    else:
        raise ValueError("unknown capability blocker")

    with closing(ADMISSION.connect(study.db)) as conn:
        before = {table: conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                  for table in ("events", "host_proof", "receipt", "consumed", "artifact")}
        assert not any(before.values())
        owner, = conn.execute("SELECT run FROM current_node")
        assert owner["run"] == original.run
        assert conn.execute("SELECT active FROM leases WHERE run=?", (original.run,)).fetchone()[0] == 1
    replacement = study.issue("replacement-" + replacement_host, replacement_host, 2, prior=original)
    with closing(ADMISSION.connect(study.db)) as conn:
        prior, current = conn.execute("""
            SELECT l.run,l.member,l.runtime,l.epoch,l.active,l.token_hash,l.contract,d.task_active
            FROM leases l JOIN dispatch d USING(run) ORDER BY l.epoch""")
        assert prior["run"] == original.run and current["run"] == replacement.run
        assert [prior["active"], prior["task_active"], current["active"], current["task_active"]] == [0, 0, 1, 1]
        assert all(prior[key] != current[key] for key in ("run", "member", "runtime", "token_hash"))
        assert current["epoch"] == prior["epoch"] + 1 and prior["contract"] == current["contract"]
        owner, = conn.execute("SELECT issue,node,run FROM current_node")
        assert tuple(owner) == (original.contract["issue"], original.contract["node"], replacement.run)
    actual = study.invoke(replacement, replacement_host, "replacement-project-tool")
    assert study.submit(replacement, actual) == "current"
    assert study.submit(replacement, actual) == "duplicate"
    return {**study.summary(), "before_handoff": before, "accepted_result": study.accepted_result(replacement, actual)}


def run(out, codex, claude):
    out.mkdir()
    orders = out / "orders"
    subprocess.run([sys.executable, ORDERS / "run.py", orders], check=True, stdout=subprocess.DEVNULL)
    for candidate in ("C1", "C2"):
        assert (orders / candidate / "report.json").read_bytes() == (FIXTURES / f"order-export-{candidate.lower()}.json").read_bytes()

    forward = Study(out / "forward", orders, codex, claude)
    a = forward.issue("original-codex", "codex", 1)
    original = forward.invoke(a, "codex", "codex-with-personal-namesake")
    assert forward.counts()["consumed"] == 0  # Hold delivery; the read-only call already happened.
    forward.invoke(a, "codex", "codex-alias-collision", collision=True)
    assert forward.invoke(a, "codex", "codex-schema-changed", schema_drift=True) is None
    forward.invoke(a, "codex", "codex-only-personal-leaf", missing=True)
    forward.invoke(a, "codex", "codex-request-personal-tool", personal_request=True)
    denied = forward.invoke(a, "codex", "codex-revoked-after-discovery", revoke_in_flight=True)
    assert forward.submit(a, denied) == "no verified tool result"
    b = forward.issue("replacement-claude", "claude", 2, prior=a)
    try:
        forward.issue("stale-takeover", "claude", 2, prior=a)
    except ValueError as exc:
        assert str(exc) == "dispatch owner changed"
        with sqlite3.connect(forward.db) as conn:
            assert conn.execute("SELECT run FROM leases WHERE active=1").fetchall() == [(b.run,)]
            assert conn.execute("SELECT run FROM dispatch WHERE run=?", ("stale-takeover",)).fetchone() is None
    else:
        raise AssertionError("a stale predecessor replaced the current owner")
    replacement = forward.invoke(b, "claude", "claude-replacement-with-personal-namesake")
    for label, target, proof, expected in [
            ("previous result relabeled", b, original, "no verified tool result"),
            ("unmodified late result", a, original, "access withdrawn"),
            ("replacement", b, replacement, "current"), ("delivery replay", b, replacement, "duplicate")]:
        assert forward.submit(target, proof) == expected, label
    assert forward.counts() == {"consumed": 1, "artifact": 3}

    reverse = Study(out / "reverse", orders, codex, claude)
    b1 = reverse.issue("original-claude", "claude", 1)
    reverse.invoke(b1, "claude", "claude-alias-collision", collision=True)
    assert reverse.invoke(b1, "claude", "claude-schema-changed", schema_drift=True) is None
    reverse.invoke(b1, "claude", "claude-only-personal-leaf", missing=True)
    reverse.invoke(b1, "claude", "claude-request-personal-tool", personal_request=True)
    d = reverse.invoke(b1, "claude", "claude-revoked-after-discovery", revoke_in_flight=True)
    assert reverse.submit(b1, d) == "no verified tool result"
    a2 = reverse.issue("replacement-codex", "codex", 2, prior=b1)
    returned = reverse.invoke(a2, "codex", "codex-replacement")
    assert reverse.submit(a2, returned) == "current" and reverse.submit(a2, returned) == "duplicate"
    assert reverse.counts() == {"consumed": 1, "artifact": 3}

    baseline = Study(out / "negative", orders, codex, claude)
    prior = None
    for epoch, host in enumerate(("codex", "claude"), 1):
        r = baseline.issue("control-" + host, host, epoch, candidate="C1", prior=prior)
        prior = r
        obs = baseline.invoke(r, host, host + "-C1")
        assert (obs["result"]["report"]["A2"], obs["result"]["report"]["A3"], obs["result"]["report"]["verdict"]) == (False, True, "rework")
    assert baseline.submit(r, obs) == "current"

    # Probe the authority independently of the host model: session/run identities come from the server-side profile.
    p = read(Path(b.providers["project_orders"]["args"][-1]))
    negatives = {}
    for label, profile, args in (("wrong-candidate", p, {"candidate": "C1"}),
                                ("wrong-member", {**p, "member": a.member}, {"candidate": "C2"}),
                                ("old-epoch", {**p, "epoch": 1}, {"candidate": "C2"}),
                                ("other-credential", {**p, "token": "wrong"}, {"candidate": "C2"}),
                                ("extra-model-field", p, {"candidate": "C2", "run": a.run})):
        value = inspect(profile, args)
        assert value.keys() == {"receipt", "status"} and value["status"] == "denied"
        negatives[label] = value["status"]
    altered = out / "modified-workbooks"
    shutil.copytree(orders / "C2", altered / "C2")
    shutil.copy2(orders / "C1/east.xlsx", altered / "C2/east.xlsx")
    drift = inspect({**p, "artifacts": str(altered)}, {"candidate": "C2"})
    assert drift.keys() == {"receipt", "status"} and drift["status"] == "invalid_artifacts"
    negatives["changed-candidate-bytes"] = drift["status"]
    recoveries = {
        "missing": recover_blocked(Study(out / "missing", orders, codex, claude), "codex", "claude", "missing"),
        "alias-collision": recover_blocked(Study(out / "alias-collision", orders, codex, claude),
                                          "claude", "codex", "alias-collision"),
    }
    report = {"hosts": {"codex": "0.144.6", "claude": "2.1.325"}, "contract": frozen_contract("C2"),
              "forward": {**forward.summary(), "accepted_result": forward.accepted_result(b, replacement)},
              "reverse": {**reverse.summary(), "accepted_result": reverse.accepted_result(a2, returned)},
              "blocked_recovery": recoveries,
              "C1_control": baseline.summary(), "authority_controls": negatives, "stale_takeover": "dispatch owner changed"}
    write(out / "summary.json", report)
    print(json.dumps({"C2_forward": forward.counts(), "C2_reverse": reverse.counts(), "C1": "rework",
                      "blocked_recovery": {reason: evidence["counts"] for reason, evidence in recoveries.items()},
                      "cases": sum(len(x.observations) for x in (forward, reverse, baseline))
                               + sum(len(evidence["cases"]) for evidence in recoveries.values())}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path, help="new directory for the synthetic evidence")
    ap.add_argument("--codex", default="codex")
    ap.add_argument("--claude", default="claude")
    args = ap.parse_args()
    run(args.output.resolve(), args.codex, args.claude)
