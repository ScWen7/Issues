"""Check successor dispatch identity using the real order verifier and local authority."""
from contextlib import closing
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from order_handoff import ADMISSION, ORDERS, Study
from order_tool import inspect


class Reverification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generated = tempfile.TemporaryDirectory()
        cls.addClassCleanup(generated.cleanup)
        cls.orders = Path(generated.name) / "orders"
        subprocess.run([sys.executable, ORDERS / "run.py", cls.orders], check=True,
                       stdout=subprocess.DEVNULL)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.study = Study(Path(temporary.name) / "study", self.orders, None, None)

    def test_same_member_reverification_gets_new_authority_and_preserves_attempt(self):
        old = self.study.issue("original", "claude", 1)
        new = self.study.issue("reverification", "claude", 2, prior=old)
        self.assertEqual((old.member, old.runtime, old.contract), (new.member, new.runtime, new.contract))
        with closing(ADMISSION.connect(self.study.db)) as db:
            self.assertEqual(db.execute("SELECT run FROM current_node").fetchone()[0], new.run)
            self.assertEqual([tuple(row) for row in db.execute("SELECT run,task_active FROM dispatch ORDER BY run")],
                             [(old.run, 0), (new.run, 1)])
            self.assertEqual(db.execute("SELECT COUNT(DISTINCT token_hash) FROM leases").fetchone()[0], 2)
        profiles = [json.loads(Path(r.providers["project_orders"]["args"][-1]).read_text()) for r in (old, new)]
        self.assertEqual(inspect(profiles[0], {"candidate": "C2"})["status"], "denied")
        result = inspect(profiles[1], {"candidate": "C2"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual((result["report"]["run"], result["report"]["attempt"]), (new.run, old.contract["attempt"]))

    def test_reverification_still_checks_the_current_dispatch_owner(self):
        old = self.study.issue("original", "claude", 1)
        self.study.issue("reverification", "claude", 2, prior=old)
        with self.assertRaisesRegex(ValueError, "dispatch owner changed"):
            self.study.issue("stale-reverification", "claude", 2, prior=old)
        with closing(ADMISSION.connect(self.study.db)) as db:
            self.assertEqual(db.execute("SELECT run FROM current_node").fetchone()[0], "reverification")
            self.assertEqual(db.execute("SELECT COUNT(*) FROM dispatch").fetchone()[0], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
