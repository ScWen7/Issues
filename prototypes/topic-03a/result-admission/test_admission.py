"""Design experiment: ingest the real C1 and C2 reports with atomic node consumption."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest


FIXTURES = Path(__file__).resolve().parents[3] / "docs/research/topic-03a/fixtures"
ISSUE = "order-export-verification"
NODE = "verify-order-export"
SLOT = "verification-report"
VERIFIER = "f7edf54a17140b44e6fa0d070e1eef4be39c50bfa99f509fa560445a8bfd8f9c"
FILES = ("east.xlsx", "west.xlsx", "cross.xlsx")
# Trusted dispatch fixture: these values pre-exist submission of any report.
COMMITS = ("6880625de52ceb834e3e60b07cd8748c4ad79058", "005e558ad99a6def3f4dbb2c7a1ec56e71553bf7")
SCHEMA = """
CREATE TABLE dispatch (
    run TEXT PRIMARY KEY, issue TEXT, node TEXT, attempt INTEGER, candidate TEXT, rule TEXT,
    git_commit TEXT, agent TEXT, task_active INTEGER, runtime_ok INTEGER, visible INTEGER, grant_revision INTEGER, verifier TEXT
);
CREATE TABLE delegation (issue TEXT, node TEXT, revision INTEGER, active INTEGER, action TEXT, PRIMARY KEY(issue, node));
CREATE TABLE current_node (issue TEXT, node TEXT, run TEXT, PRIMARY KEY(issue, node));
CREATE TABLE receipt (
    run TEXT, slot TEXT, sha256 TEXT, payload BLOB, placement TEXT, PRIMARY KEY(run, slot)
);
CREATE TABLE consumed (
    issue TEXT, node TEXT, attempt INTEGER, run TEXT, verdict TEXT, PRIMARY KEY(issue, node, attempt)
);
CREATE TABLE required_artifact (run TEXT, name TEXT, PRIMARY KEY(run, name));
CREATE TABLE supplied (run TEXT, name TEXT, bytes INTEGER, digest TEXT, PRIMARY KEY(run, name));
CREATE TABLE artifact (run TEXT, name TEXT, bytes INTEGER, digest TEXT, PRIMARY KEY(run, name));
CREATE TABLE artifact_reader (member TEXT, run TEXT, name TEXT, PRIMARY KEY(member, run, name));
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def supply_file(db, run, name, path):
    # Receiving adapter reads immutable candidate bytes independently of the report.
    data = path.read_bytes()
    db.execute("INSERT OR REPLACE INTO supplied VALUES(?,?,?,?)", (run, name, len(data), sha(data)))


def qualify(db, dispatch, report):
    if report.get("verifier_sha256") != dispatch["verifier"]:
        return "verifier mismatch", {}
    verdict = report.get("verdict")
    declared = report.get("artifacts")
    if verdict not in ("pass", "rework", "fail", "human") or not isinstance(declared, list):
        return "invalid report", {}
    if verdict == "pass" and (report.get("A2") is not True or report.get("A3") is not True):
        return "checks failed", {}
    required = {r[0] for r in db.execute("SELECT name FROM required_artifact WHERE run=?", (dispatch["run"],))}
    received = {r["name"]: (r["bytes"], r["digest"]) for r in
                db.execute("SELECT * FROM supplied WHERE run=?", (dispatch["run"],))}
    declared_names = set()
    verified = {}
    for item in declared:
        if not isinstance(item, dict):
            return "invalid report", {}
        name, size, digest = item.get("name"), item.get("bytes"), item.get("sha256")
        if (not isinstance(name, str) or name not in required or name in declared_names
                or type(size) is not int or size < 0 or not isinstance(digest, str) or len(digest) != 64
                or any(ch not in "0123456789abcdef" for ch in digest)):
            return "invalid artifact descriptor", {}
        declared_names.add(name)
        if name in received:
            if received[name] != (size, digest):
                return "attachment mismatch", {}
            verified[name] = (size, digest)
    if verdict == "pass":
        if declared_names != required:
            return "required artifact omitted", {}
        if verified.keys() != required:
            return "waiting for attachments", {}
    return "qualified", verified


def admit(path, principal, source_run, payload, expected_sha, start=None):
    # The fixture supplies principal and source_run from the authenticated channel.
    # Both the declared digest and the report itself are submitted data.
    digest = sha(payload)
    if digest != expected_sha:
        return "digest mismatch"
    try:
        report = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return "invalid report"
    if not isinstance(report, dict):
        return "invalid report"
    with closing(connect(path)) as db, db:
        if start is not None:
            start.wait(timeout=5)  # each worker already owns an independent open connection
        db.execute("BEGIN IMMEDIATE")
        dispatch = db.execute("SELECT * FROM dispatch WHERE run=?", (source_run,)).fetchone()
        if (not dispatch or dispatch["agent"] != principal or not dispatch["task_active"]
                or not dispatch["runtime_ok"] or not dispatch["visible"]):
            return "access withdrawn"
        issue, node = dispatch["issue"], dispatch["node"]
        grant = db.execute("SELECT * FROM delegation WHERE issue=? AND node=?", (issue, node)).fetchone()
        if (not grant or not grant["active"] or grant["revision"] != dispatch["grant_revision"]
                or grant["action"] != "submit-report"):
            return "outside delegation"
        fields = ("run", "issue", "node", "attempt", "candidate", "rule")
        if any(report.get(key) != dispatch[key] for key in fields) or report.get("commit") != dispatch["git_commit"]:
            return "dispatch mismatch"
        prior = db.execute("SELECT sha256, placement FROM receipt WHERE run=? AND slot=?", (source_run, SLOT)).fetchone()
        if prior and prior["sha256"] != digest:
            return "conflicting report"
        if prior and prior["placement"] != "pending":
            return "duplicate"
        status, refs = qualify(db, dispatch, report)
        if status == "waiting for attachments" and not prior:
            db.execute("INSERT INTO receipt VALUES(?,?,?,?,?)", (source_run, SLOT, digest, payload, "pending"))
        if status != "qualified":
            return status
        current = db.execute("SELECT run FROM current_node WHERE issue=? AND node=?", (issue, node)).fetchone()
        placement = "current" if current and current["run"] == source_run else "historical"
        if prior:
            db.execute("UPDATE receipt SET placement=? WHERE run=? AND slot=?", (placement, source_run, SLOT))
        else:
            db.execute("INSERT INTO receipt VALUES(?,?,?,?,?)", (source_run, SLOT, digest, payload, placement))
        db.executemany("INSERT INTO artifact VALUES(?,?,?,?)", [(source_run, name, size, h) for name, (size, h) in refs.items()])
        if placement == "current":
            db.execute("INSERT INTO consumed VALUES(?,?,?,?,?)", (issue, node, dispatch["attempt"], source_run, report["verdict"]))
        return placement


def authorized_reference(path, member, run, name):
    # Access is attached to one delivery, including the reporting run and artifact name.
    with closing(connect(path)) as db:
        row = db.execute("""
            SELECT a.digest FROM artifact a JOIN artifact_reader r USING(run, name)
            JOIN supplied s ON s.run=a.run AND s.name=a.name AND s.bytes=a.bytes AND s.digest=a.digest
            WHERE r.member=? AND a.run=? AND a.name=?
        """, (member, run, name)).fetchone()
        return row["digest"] if row else None


class ReportAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generated = tempfile.TemporaryDirectory()
        cls.addClassCleanup(generated.cleanup)
        cls.outputs = Path(generated.name) / "export"
        generator = Path(__file__).resolve().parents[1] / "order-export/run.py"
        subprocess.run([sys.executable, generator, cls.outputs], check=True, stdout=subprocess.DEVNULL)
        for candidate in ("C1", "C2"):
            fixed = FIXTURES / f"order-export-{candidate.lower()}.json"
            if fixed.read_bytes() != (cls.outputs / candidate / "report.json").read_bytes():
                raise AssertionError("new workbooks did not reproduce the fixed report")

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "results.sqlite"
        self.raw = {key: (FIXTURES / f"order-export-{key.lower()}.json").read_bytes() for key in ("C1", "C2")}
        with closing(connect(self.db)) as db, db:
            db.executescript(SCHEMA)
            for attempt, commit in enumerate(COMMITS, start=1):
                candidate = f"C{attempt}"
                db.execute("INSERT INTO dispatch VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ("verify-" + candidate, ISSUE, NODE, attempt, candidate, "D2", commit, "verifier", 1, 1, 1, 3, VERIFIER))
                run = "verify-" + candidate
                for name in FILES:
                    db.execute("INSERT INTO required_artifact VALUES(?,?)", (run, name))
                    supply_file(db, run, name, self.outputs / candidate / name)
            db.execute("INSERT INTO delegation VALUES(?,?,?,?,?)", (ISSUE, NODE, 3, 1, "submit-report"))
            db.execute("INSERT INTO current_node VALUES(?,?,?)", (ISSUE, NODE, "verify-C2"))

    def submit(self, candidate, start=None):
        payload = self.raw[candidate]
        return admit(self.db, "verifier", "verify-" + candidate, payload, sha(payload), start)

    def snapshot(self):
        with closing(connect(self.db)) as db:
            return tuple(db.execute("SELECT count(*) FROM " + table).fetchone()[0]
                         for table in ("receipt", "consumed", "artifact"))

    def test_concurrent_same_bytes_consumed_once(self):
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.submit, "C2", barrier) for _ in range(2)]
            self.assertCountEqual([future.result() for future in futures], ["current", "duplicate"])
        self.assertEqual(self.snapshot(), (1, 1, 3))
        with closing(connect(self.db)) as db:
            self.assertEqual(tuple(db.execute("SELECT run, verdict FROM consumed").fetchone()), ("verify-C2", "pass"))
            self.assertEqual(db.execute("SELECT payload FROM receipt").fetchone()[0], self.raw["C2"])

    def test_different_digest_same_slot_cannot_replace_original(self):
        self.assertEqual(self.submit("C2"), "current")
        other = self.raw["C2"] + b"\n"  # still valid JSON, different bytes and valid digest
        self.assertEqual(admit(self.db, "verifier", "verify-C2", other, sha(other)), "conflicting report")
        with closing(connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT payload FROM receipt").fetchone()[0], self.raw["C2"])
        self.assertEqual(self.snapshot(), (1, 1, 3))

    def test_genuine_old_candidate_retained_without_consumption(self):
        self.assertEqual(self.submit("C2"), "current")
        self.assertEqual(self.submit("C1"), "historical")
        self.assertEqual(self.submit("C1"), "duplicate")
        self.assertEqual(self.snapshot(), (2, 1, 6))
        with closing(connect(self.db)) as db:
            old = db.execute("SELECT payload FROM receipt WHERE placement='historical'").fetchone()
            self.assertEqual(json.loads(old[0])["verdict"], "rework")

    def test_current_access_scope_and_grant_rechecked(self):
        statements = (
            ("UPDATE dispatch SET task_active=0", "access withdrawn"),
            ("UPDATE dispatch SET runtime_ok=0", "access withdrawn"),
            ("UPDATE dispatch SET visible=0", "access withdrawn"),
            ("UPDATE delegation SET revision=4", "outside delegation"),
            ("UPDATE delegation SET active=0", "outside delegation"),
            ("UPDATE delegation SET action='comment'", "outside delegation"),
        )
        for sql, outcome in statements:
            with self.subTest(sql=sql):
                with closing(connect(self.db)) as db, db:
                    db.execute(sql)
                self.assertEqual(self.submit("C2"), outcome)
                self.assertEqual(self.snapshot(), (0, 0, 0))
                with closing(connect(self.db)) as db, db:
                    db.execute("UPDATE dispatch SET task_active=1, runtime_ok=1, visible=1")
                    db.execute("UPDATE delegation SET revision=3, active=1, action='submit-report'")
        data = self.raw["C2"]
        self.assertEqual(admit(self.db, "other", "verify-C2", data, sha(data)), "access withdrawn")
        self.assertEqual(self.submit("C2"), "current")
        with closing(connect(self.db)) as db, db:
            db.execute("UPDATE delegation SET active=0")
        self.assertEqual(self.submit("C2"), "outside delegation")
        self.assertEqual(self.snapshot(), (1, 1, 3))

    def test_content_hash_validated_before_persistence(self):
        self.assertEqual(admit(self.db, "verifier", "verify-C2", self.raw["C2"], sha(self.raw["C1"])), "digest mismatch")
        self.assertEqual(self.snapshot(), (0, 0, 0))

    def test_bytes_from_another_dispatch_rejected_even_with_valid_digest(self):
        data = self.raw["C1"]
        self.assertEqual(admit(self.db, "verifier", "verify-C2", data, sha(data)), "dispatch mismatch")
        self.assertEqual(self.snapshot(), (0, 0, 0))

    def changed(self, candidate, transform):
        report = json.loads(self.raw[candidate])
        transform(report)
        body = json.dumps(report).encode()
        return admit(self.db, "verifier", "verify-" + candidate, body, sha(body))

    def test_pass_requires_named_artifacts_in_its_manifest(self):
        self.assertEqual(self.changed("C2", lambda report: report["artifacts"].pop()), "required artifact omitted")
        self.assertEqual(self.snapshot(), (0, 0, 0))

    def test_late_attachment_resolves_pending_receipt_and_consumes_once(self):
        with closing(connect(self.db)) as db, db:
            db.execute("DELETE FROM supplied WHERE run='verify-C2' AND name='east.xlsx'")
        self.assertEqual(self.submit("C2"), "waiting for attachments")
        self.assertEqual(self.submit("C2"), "waiting for attachments")
        self.assertEqual(self.snapshot(), (1, 0, 0))
        with closing(connect(self.db)) as db, db:
            supply_file(db, "verify-C2", "east.xlsx", self.outputs / "C2/east.xlsx")
        barrier = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.submit, "C2", barrier) for _ in range(2)]
            self.assertCountEqual([f.result() for f in futures], ["current", "duplicate"])
        self.assertEqual(self.snapshot(), (1, 1, 3))

    def test_attachment_verified_against_independently_observed_size_and_digest(self):
        original = (self.outputs / "C2/east.xlsx").read_bytes()
        for altered in (original + b"x", b"0" + original[1:]):
            with self.subTest(size=len(altered)):
                path = self.db.parent / "replacement.xlsx"
                path.write_bytes(altered)
                with closing(connect(self.db)) as db, db:
                    supply_file(db, "verify-C2", "east.xlsx", path)
                self.assertEqual(self.submit("C2"), "attachment mismatch")
                self.assertEqual(self.snapshot(), (0, 0, 0))

    def test_verifier_version_must_match_dispatch(self):
        self.assertEqual(self.changed("C2", lambda r: r.update(verifier_sha256="0" * 64)), "verifier mismatch")
        self.assertEqual(self.snapshot(), (0, 0, 0))

    def test_pass_with_a_failed_business_check_is_not_consumed(self):
        for criterion in ("A2", "A3"):
            with self.subTest(criterion=criterion):
                self.assertEqual(self.changed("C2", lambda r: r.update({criterion: False})), "checks failed")
                self.assertEqual(self.snapshot(), (0, 0, 0))

    def test_rework_preserves_failure_and_only_the_available_evidence(self):
        with closing(connect(self.db)) as db, db:
            db.execute("DELETE FROM supplied WHERE run='verify-C1' AND name='east.xlsx'")
            db.execute("UPDATE current_node SET run='verify-C1'")
        self.assertEqual(self.submit("C1"), "current")
        self.assertEqual(self.snapshot(), (1, 1, 2))
        with closing(connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT verdict FROM consumed").fetchone()[0], "rework")
            self.assertEqual(db.execute("SELECT payload FROM receipt").fetchone()[0], self.raw["C1"])

    def test_same_content_retains_delivery_specific_access(self):
        self.assertEqual(self.submit("C1"), "historical")
        self.assertEqual(self.submit("C2"), "current")
        with closing(connect(self.db)) as db, db:
            # C1's eastern file actually contains all orders; C2's authorized cross-region file has the same bytes.
            rows = db.execute("SELECT digest FROM artifact WHERE (run=? AND name=?) OR (run=? AND name=?)",
                              ("verify-C1", "east.xlsx", "verify-C2", "cross.xlsx")).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][0], rows[1][0])
            digest = rows[0][0]
            db.execute("INSERT INTO artifact_reader VALUES('cross-operator', 'verify-C2', 'cross.xlsx')")
        self.assertEqual(authorized_reference(self.db, "cross-operator", "verify-C2", "cross.xlsx"), digest)
        self.assertIsNone(authorized_reference(self.db, "cross-operator", "verify-C1", "east.xlsx"))
        self.assertIsNone(authorized_reference(self.db, "eastern-operator", "verify-C2", "cross.xlsx"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
