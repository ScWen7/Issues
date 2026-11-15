"""Reproduce the 3B proposal/review experiment with the 3A verification reports."""
import argparse
import hashlib
import json
from pathlib import Path
from typing import NamedTuple


REPORTS = {
    "C1": ("order-export-c1.json", "da022445c03fa787af994101f47cd8cfb777913f882a6b7aa32116a3493afcb1"),
    "C2": ("order-export-c2.json", "e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514"),
}
POINTER = "/checks/east/A2"
TOPIC = "export-scope-regression"
TEAM = "team:quality"


class Denied(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Denied(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


class SourcePin(NamedTuple):
    source: str
    sha256: str | None
    generation: int


class Evidence:
    def __init__(self, directory):
        self.blobs = {}
        self.revisions = {key: [] for key in REPORTS}
        self.readers = {key: {"steward", "author", "reviewer"} for key in REPORTS}
        self.stewards = {"C1": {"steward", "author"}, "C2": {"steward"}}
        for key, (filename, expected) in REPORTS.items():
            raw = (directory / filename).read_bytes()
            require(digest(raw) == expected, f"{key} report differs from the 3A fixture")
            self.replace("steward", key, raw)
        self.pins()

    def replace(self, actor, key, raw):
        require(actor in self.stewards[key], "source management permission required")
        sha = None
        if raw is not None:
            report = json.loads(raw)
            require(report["candidate"] == key and report["run"] == f"verify-{key}", "different run")
            sha = digest(raw)
            self.blobs[sha] = raw
        revisions = self.revisions[key]
        if not revisions or revisions[-1] != sha:
            revisions.append(sha)

    def heads(self):
        return tuple(SourcePin(key, self.revisions[key][-1], len(self.revisions[key])) for key in sorted(REPORTS))

    def pins(self):
        heads = self.heads()
        require(all(pin.sha256 for pin in heads), "source withdrawn")
        return heads

    def read(self, actor, pin):
        revisions = self.revisions[pin.source]
        require(actor in self.readers[pin.source] and revisions[-1] is not None, "source read denied")
        require(pin.sha256 and 1 <= pin.generation <= len(revisions)
                and revisions[pin.generation - 1] == pin.sha256, "unknown reference")
        return json.loads(self.blobs[pin.sha256])

    def verify_pair(self, actor, pins):
        c1, c2 = [self.read(actor, pin) for pin in pins]
        require(all(c1[k] == c2[k] for k in ("issue", "node", "rule", "verifier_sha256")), "different control")
        require(c1["commit"] != c2["commit"] and [c1["attempt"], c2["attempt"]] == [1, 2], "different attempts required")
        for report, a2, verdict in [(c1, False, "rework"), (c2, True, "pass")]:
            require(report["rule"] == "D2" and report["verdict"] == verdict and report["A2"] is a2
                    and report["checks"]["east"]["A2"] is a2 and report["A3"] is True, "evidence disagrees")
        east1, east2, west = [set(x) for x in (c1["checks"]["east"]["ids"], c2["checks"]["east"]["ids"],
                                              c1["checks"]["west"]["ids"])]
        for report in (c1, c2):
            require(report["checks"]["east"]["A3"] is True and report["checks"]["cross"]["A2"] is True
                    and set(report["checks"]["cross"]["ids"]) == east1, "cross-region control failed")
        require(bool(east1 & west) and not (east2 & west) and east1 - west == east2, "scope comparison failed")


class Review:
    """One study project, one named team, two reports and one regression topic."""
    def __init__(self, evidence):
        self.evidence = evidence
        self.publishers = {"author", "reviewer", "blind_reviewer"}
        self.members = self.publishers | {"team_reader", "author", "steward"}
        self.proposals = {}
        self.decisions = []
        self.grants = set()
        self.dispatches = {}

    def submit(self, actor, text):
        pins = self.evidence.pins()
        self.evidence.verify_pair(actor, pins)
        # Run identity and test locator remain stable through retries or refreshed report metadata.
        identity = fingerprint([TEAM, TOPIC, "order-export-verification", "verify-order-export",
                                [(f"verify-{pin.source}", POINTER) for pin in pins]])
        proposal = self.proposals.get(identity)
        if proposal is None:
            proposal = {"id": identity, "author": actor, "text": text, "revision": 1, "status": "draft",
                        "pins": pins, "asset": None, "retired": False}
            self.proposals[identity] = proposal
        return proposal

    def can_review(self, actor, p):
        require(actor in self.publishers and actor != p["author"], "independent team publisher required")
        self.evidence.verify_pair(actor, p["pins"])

    def record(self, actor, p, decision, reason, source=None, audience=None):
        entry = {"decision": decision, "actor": actor, "reason": reason,
                 "proposal": p["id"], "revision": p["revision"],
                 "body_sha256": digest(p["text"].encode()), "evidence": list(p["pins"])}
        if source is not None:
            entry.update(source=source, audience=audience)
        self.decisions.append(entry)

    def reject(self, actor, p, revision, reason):
        require(p["status"] == "draft" and revision == p["revision"] and reason.strip(), "draft revision required")
        self.can_review(actor, p)
        self.record(actor, p, "rejected", reason)
        p["status"] = "rejected"

    def revise(self, actor, p, text):
        require(actor == p["author"] and p["status"] == "rejected" and text != p["text"], "author revision required")
        pins = self.evidence.pins()
        self.evidence.verify_pair(actor, pins)
        p.update(text=text, revision=p["revision"] + 1, status="draft", pins=pins)

    def grant_key(self, p, audience):
        return p["id"], p["revision"], digest(p["text"].encode()), audience, p["pins"]

    def authorize(self, actor, p, audience=TEAM):
        for pin in p["pins"]:
            require(actor in self.evidence.stewards[pin.source], "derivative grant required on each source")
        self.evidence.verify_pair(actor, p["pins"])
        require(p["pins"] == self.evidence.pins() and p["status"] in ("draft", "rechecking"), "current evidence required")
        self.grants.add(self.grant_key(p, audience))
        self.record(actor, p, "authorized", audience)

    def revoke(self, actor, p, audience, reason):
        require(all(actor in self.evidence.stewards[pin.source] for pin in p["pins"]), "source stewardship required")
        key = self.grant_key(p, audience)
        require(key in self.grants and reason.strip(), "current derivative grant and reason required")
        self.grants.remove(key)
        if audience == TEAM and p["status"] == "released":
            p["status"] = "review_required"
        self.record(actor, p, "authorization_revoked", reason)

    def revoke_source(self, actor, p, source, audience, reason):
        require(any(pin.source == source for pin in p["pins"]), "source is not part of proposal")
        require(actor in self.evidence.stewards.get(source, ()), "source stewardship required")
        key = self.grant_key(p, audience)
        require(key in self.grants and reason.strip(), "current derivative grant and reason required")
        # A combined permission needs every source; withdrawing one invalidates this grant only.
        self.grants.remove(key)
        if audience == TEAM and p["status"] == "released":
            p["status"] = "review_required"
        self.record(actor, p, "source_authorization_revoked", reason, source, audience)

    def release(self, actor, p, revision):
        require(p["status"] in ("draft", "rechecking") and revision == p["revision"], "stale or closed review")
        self.can_review(actor, p)
        require(p["pins"] == self.evidence.pins(), "source changed during review")
        require(self.grant_key(p, TEAM) in self.grants, "grant does not cover team, text or evidence")
        if p["asset"] is None:
            p["asset"] = {"key": TOPIC, "scope": TEAM, "version": 1, "text": p["text"]}
            decision = "published"
        else:
            require(p["asset"]["text"] == p["text"], "changed text requires a new asset version")
            decision = "reaffirmed"
        p["status"] = "released"
        self.record(actor, p, decision, TEAM)

    def state(self, p):
        if p["retired"]:
            return "retired"
        if p["asset"] is None:
            return p["status"]
        if (p["status"] != "released" or self.evidence.heads() != p["pins"]
                or self.grant_key(p, TEAM) not in self.grants):
            return "review_required"
        return "active"

    def fetch(self, actor, p):
        require(actor in self.members and self.state(p) == "active", "team distribution denied")
        return dict(p["asset"])

    def dispatch(self, actor, p, run):
        asset = self.fetch(actor, p)
        receipt = {"dispatch": run, "version": asset["version"], "asset": asset["key"],
                   "body_sha256": digest(asset["text"].encode())}
        key = run, asset["key"]
        require(key not in self.dispatches or self.dispatches[key] == receipt, "run already pinned")
        self.dispatches[key] = receipt
        return dict(receipt)

    def audit(self, actor, p):
        for key in REPORTS:
            require(actor in self.evidence.readers[key], "project audit requires source access")
        return [entry for entry in self.decisions if entry["proposal"] == p["id"]]

    def reopen(self, actor, p):
        require(actor in self.publishers and self.state(p) == "review_required", "recheck required")
        pins = self.evidence.pins()
        self.evidence.verify_pair(actor, pins)
        p.update(pins=pins, status="rechecking")

    def retire(self, actor, p, reason):
        require(actor in self.publishers and actor != p["author"] and not p["retired"] and p["asset"] is not None
                and reason.strip(), "team retirement decision required")
        p.update(retired=True, status="retired")
        self.record(actor, p, "retired", reason)


def run(directory):
    checked = []

    def check(name, truth):
        if not truth:
            raise AssertionError(name)
        checked.append(name)

    def denied(name, action):
        try:
            action()
        except Denied:
            checked.append(name)
        else:
            raise AssertionError(name)

    e = Evidence(directory)
    r = Review(e)
    original = e.pins()
    private = e.read("author", original[0])
    sample = private["checks"]["west"]["ids"][0]
    p = r.submit("author", "验证失败的订单为 " + sample)
    identity = p["id"]
    check("same_execution_and_claim_deduplicated", r.submit("reviewer", "重复观察") is p and len(r.proposals) == 1)
    r.reject("reviewer", p, 1, "草稿含项目订单标识")
    denied("rejected_revision_cannot_publish", lambda: r.release("reviewer", p, 1))
    check("rejected_revision_not_overwritten_by_retry", r.submit("author", "再次提交")["status"] == "rejected")
    clean = "验证区域订单导出时，用普通区域账号和跨区账号分别导出。核对每份工作簿的订单集合，并单独验证付款时间列。"
    r.revise("author", p, clean)
    denied("stale_review_revision", lambda: r.release("reviewer", p, 1))
    denied("team_publisher_without_source_access", lambda: r.release("blind_reviewer", p, 2))
    denied("one_of_two_source_grants_insufficient", lambda: r.authorize("author", p))
    denied("team_release_requires_source_steward", lambda: r.release("reviewer", p, 2))
    r.authorize("steward", p, "project:orders")
    denied("project_grant_not_valid_for_team", lambda: r.release("reviewer", p, 2))
    r.authorize("steward", p)
    denied("team_author_cannot_self_publish", lambda: r.release("author", p, 2))
    denied("project_steward_lacks_team_publish", lambda: r.release("steward", p, 2))
    r.release("reviewer", p, 2)
    delivered = r.fetch("team_reader", p)
    issued = r.dispatch("team_reader", p, "study-run-before-source-change")
    check("repeated_dispatch_pins_one_version", r.dispatch("team_reader", p, issued["dispatch"]) == issued
          and len(r.dispatches) == 1)
    check("team_projection_contains_only_approved_copy", delivered == {
        "scope": TEAM, "key": TOPIC, "version": 1, "text": clean} and sample not in clean)
    denied("team_reader_cannot_export_project_ledger", lambda: r.audit("team_reader", p))
    denied("ordinary_team_reader_cannot_open_evidence", lambda: e.read("team_reader", original[0]))
    denied("outside_team_cannot_fetch", lambda: r.fetch("outsider", p))
    check("project_reviewer_resolves_original_evidence", e.read("reviewer", original[0]) == private)
    e.readers["C1"].remove("author")
    denied("revoked_individual_source_access", lambda: e.read("author", original[0]))
    check("reader_revocation_keeps_separately_licensed_derivative", r.fetch("team_reader", p) == delivered)
    r.revoke("steward", p, TEAM, "来源管理人撤回团队提炼稿授权")
    denied("withdrawn_derivative_grant_stops_new_dispatch", lambda: r.fetch("team_reader", p))
    denied("regrant_without_reopening_review", lambda: r.authorize("steward", p))
    r.reopen("reviewer", p)
    r.authorize("steward", p)
    denied("regrant_alone_cannot_restore_distribution", lambda: r.fetch("team_reader", p))
    denied("source_steward_cannot_reaffirm_after_regrant", lambda: r.release("steward", p, 2))
    r.release("reviewer", p, 2)

    raw = e.blobs[original[0].sha256]
    e.replace("steward", "C1", raw)
    check("repeated_source_head_preserves_live_review", e.pins() == original and r.fetch("team_reader", p) == delivered)
    for change, replacement in (("amended", raw + b" "), ("withdrawn", None)):
        before = e.pins()
        e.replace("steward", "C1", replacement)
        changed = e.heads()
        e.replace("steward", "C1", replacement)
        check(f"{change}_duplicate_head_deduplicated", e.heads() == changed)
        # Restore before any reviewer sees the intermediate state.
        e.replace("steward", "C1", raw)
        restored = e.pins()
        check(f"{change}_restored_digest_has_new_generation",
              restored[0].sha256 == before[0].sha256 and restored[0].generation == before[0].generation + 2
              and restored[1] == before[1])
        denied(f"{change}_then_restored_does_not_reactivate", lambda: r.fetch("team_reader", p))
        r.reopen("reviewer", p)
        denied(f"{change}_then_restored_requires_fresh_grant", lambda: r.release("reviewer", p, 2))
        r.authorize("steward", p)
        denied(f"{change}_then_restored_requires_independent_review", lambda: r.fetch("team_reader", p))
        r.release("reviewer", p, 2)
        check(f"{change}_then_restored_reaffirmed_at_same_version",
              r.fetch("team_reader", p) == delivered and r.decisions[-1]["evidence"] == list(restored))

    # This metadata-only amendment is an experiment. The checked-in 3A report stays immutable.
    e.replace("steward", "C1", e.blobs[original[0].sha256] + b"\n")
    denied("amended_evidence_stops_new_dispatch", lambda: r.fetch("team_reader", p))
    check("previously_delivered_digest_unchanged", r.dispatches[(issued["dispatch"], TOPIC)] == issued
          and issued["body_sha256"] == digest(delivered["text"].encode()))
    r.reopen("reviewer", p)
    denied("old_derivative_grant_cannot_reaffirm_changed_evidence", lambda: r.release("reviewer", p, 2))
    r.authorize("steward", p)
    r.release("reviewer", p, 2)
    check("same_asset_version_reaffirmed_with_new_evidence",
          r.fetch("team_reader", p) == delivered and r.decisions[-1]["evidence"] != list(original))
    contradicted = dict(private, verdict="pass")
    e.replace("steward", "C1", json.dumps(contradicted).encode())
    denied("contradictory_evidence_blocks_reaffirmation", lambda: r.reopen("reviewer", p))
    e.replace("steward", "C1", None)
    denied("withdrawn_source_blocks_historical_raw_read", lambda: e.read("reviewer", original[0]))
    denied("withdrawn_source_blocks_new_dispatch", lambda: r.fetch("team_reader", p))
    r.retire("reviewer", p, "来源撤回，证据对已失效")
    e.replace("steward", "C1", e.blobs[original[0].sha256])
    denied("restoration_does_not_resurrect_retired_asset", lambda: r.reopen("reviewer", p))
    denied("retired_asset_cannot_be_dispatched", lambda: r.fetch("team_reader", p))
    check("audit_preserves_rejection_and_initial_evidence",
          r.decisions[0]["decision"] == "rejected" and r.decisions[0]["evidence"] == list(original))
    return {"checks": checked, "team_projection_at_first_publication": delivered,
            "final_status": r.state(p), "previous_dispatch_receipt": issued,
            "project_audit": {"proposal_id": identity, "ledger": r.audit("reviewer", p),
                              "inputs": [{"report": REPORTS[pin.source][0], "run": f"verify-{pin.source}",
                                          "sha256": pin.sha256, "generation": pin.generation,
                                          "pointer": POINTER} for pin in original]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, help="defaults to the 3A report directory in this repository")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    fixtures = args.fixtures or Path(__file__).resolve().parents[3] / "docs/research/topic-03a/fixtures"
    result = json.dumps(run(fixtures), indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")
