"""Regression checks for one source's derivative permission within a proposal."""
from pathlib import Path
import unittest

from contribution import Denied, Evidence, Review, TEAM


FIXTURES = Path(__file__).resolve().parents[3] / "docs/research/topic-03a/fixtures"


class SourceWithdrawal(unittest.TestCase):
    def setUp(self):
        self.evidence = Evidence(FIXTURES)
        self.review = Review(self.evidence)
        self.proposal = self.review.submit("author", "分别核对区域与跨区账号的订单集合。")
        self.review.authorize("steward", self.proposal, "project:orders")
        self.review.authorize("steward", self.proposal)
        self.review.release("reviewer", self.proposal, 1)

    def withdraw(self, actor="author", source="C1", audience=TEAM, reason="撤回该来源的派生使用"):
        self.review.revoke_source(actor, self.proposal, source, audience, reason)

    def test_one_source_steward_stops_team_distribution_and_preserves_evidence(self):
        pins = self.evidence.pins()
        blobs = self.evidence.blobs.copy()
        delivered = self.review.dispatch("team_reader", self.proposal, "existing-run")
        other_grant = self.review.grant_key(self.proposal, "project:orders")
        self.withdraw()
        self.assertEqual(self.review.state(self.proposal), "review_required")
        with self.assertRaises(Denied):
            self.review.fetch("team_reader", self.proposal)
        self.assertIn(other_grant, self.review.grants)
        self.assertEqual(self.evidence.pins(), pins)
        self.assertEqual(self.evidence.blobs, blobs)
        self.assertEqual(self.evidence.read("reviewer", pins[0])["candidate"], "C1")
        self.assertEqual(self.review.dispatches[("existing-run", delivered["asset"])], delivered)
        decision = self.review.decisions[-1]
        self.assertEqual((decision["actor"], decision["source"], decision["audience"]),
                         ("author", "C1", TEAM))

    def test_unknown_unrelated_or_unmanaged_source_is_rejected(self):
        self.evidence.stewards["unrelated"] = {"author"}
        for actor, source in (("team_reader", "C1"), ("author", "C2"),
                              ("author", "missing"), ("author", "unrelated")):
            with self.subTest(actor=actor, source=source):
                with self.assertRaises(Denied):
                    self.withdraw(actor=actor, source=source)
                self.assertEqual(self.review.state(self.proposal), "active")

    def test_current_source_stewardship_is_required(self):
        self.evidence.stewards["C1"].remove("author")
        with self.assertRaises(Denied):
            self.withdraw()
        self.assertEqual(self.review.state(self.proposal), "active")

    def test_withdrawal_requires_matching_audience_grant_and_reason(self):
        grants = self.review.grants.copy()
        for audience, reason in (("team:other", "撤回"), (TEAM, " ")):
            with self.subTest(audience=audience, reason=reason):
                with self.assertRaises(Denied):
                    self.withdraw(audience=audience, reason=reason)
                self.assertEqual(self.review.grants, grants)
        self.withdraw(audience="project:orders")
        self.assertIn(self.review.grant_key(self.proposal, TEAM), self.review.grants)
        self.assertNotIn(self.review.grant_key(self.proposal, "project:orders"), self.review.grants)
        self.assertEqual(self.review.state(self.proposal), "active")
        self.review.fetch("team_reader", self.proposal)

    def test_reauthorization_waits_for_independent_review(self):
        original = self.review.fetch("team_reader", self.proposal)
        self.withdraw()
        with self.assertRaises(Denied):
            self.review.authorize("steward", self.proposal)
        self.review.reopen("reviewer", self.proposal)
        self.review.authorize("steward", self.proposal)
        with self.assertRaises(Denied):
            self.review.fetch("team_reader", self.proposal)
        with self.assertRaises(Denied):
            self.review.release("author", self.proposal, 1)
        self.review.release("reviewer", self.proposal, 1)
        self.assertEqual(self.review.fetch("team_reader", self.proposal), original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
