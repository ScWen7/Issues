#!/usr/bin/env python3
"""Contract-level Recall isolation experiment; deliberately not a search-engine implementation.

It models provider candidates, then applies authorization and scope filtering before
serializing any candidate metadata. The experiment validates the product contract,
not ranking quality, indexing freshness, or a production connector.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures" / "two-project-recall.json"


def tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", value.lower()))


def authorized(principal: dict, item: dict) -> bool:
    scope = item["scope"]
    if scope["kind"] == "team":
        return scope["id"] in principal["teams"]
    if scope["kind"] == "project":
        return scope["id"] in principal["projects"]
    return False


def lexical_score(query: str, item: dict) -> int:
    q = tokens(query)
    text = " ".join([item["title"], item["claim"], *item["terms"]])
    return len(q & tokens(text))


def knowledge_recall(query: str, principal: dict, corpus: dict) -> list[dict]:
    """Return only authorized formal Knowledge candidates.

    Important ordering: authorization/scope filtering occurs before ranking and
    before any candidate fields are serialized to the caller.
    """
    visible = [item for item in corpus["knowledge"] if authorized(principal, item) and item.get("distribution_status", "active") == "active"]
    ranked = [(lexical_score(query, item), item) for item in visible]
    ranked = [(score, item) for score, item in ranked if score > 0]
    ranked.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "scope": item["scope"],
            "revision": item["revision"],
            "release": item["release"],
            "claim": item["claim"],
            "conditions": item["conditions"],
            "limitations": item["limitations"],
            "evidence": [
                {
                    "id": ev["id"],
                    "readable": ev["readable_by"](principal),
                }
                for ev in item["evidence"]
            ],
        }
        for _, item in ranked
    ]



def recall_with_projection(query: str, principal: dict, corpus: dict, projection_state: str) -> dict:
    """Model coverage semantics separately from authoritative Release eligibility."""
    if projection_state in {"Unavailable", "Failed"}:
        return {"coverage": projection_state, "hits": []}
    hits = knowledge_recall(query, principal, corpus)
    if projection_state in {"Pending", "Building", "Stale"}:
        return {"coverage": "Partial / Stale", "hits": hits}
    return {"coverage": "Complete", "hits": hits}

def source_search(query: str, principal: dict, corpus: dict) -> list[str]:
    # Independent provider. It never shares the Knowledge Recall corpus/output.
    return [
        source["id"]
        for source in corpus["sources"]
        if source["project"] in principal["projects"]
        and lexical_score(query, {
            "title": source["title"], "claim": source["summary"], "terms": source["terms"]
        }) > 0
    ]


def code_retrieval(query: str, principal: dict, corpus: dict) -> list[str]:
    return [
        code["id"]
        for code in corpus["code"]
        if code["project"] in principal["projects"]
        and lexical_score(query, {
            "title": code["title"], "claim": code["summary"], "terms": code["terms"]
        }) > 0
    ]


def harness_resolution(principal: dict, corpus: dict) -> list[str]:
    return [
        item["id"] for item in corpus["harness"]
        if item["team"] in principal["teams"]
        and item["published"]
        and item["id"] in principal["adopted_harness"]
    ]


def load_fixture() -> dict:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # Attach policy functions only at runtime; the fixture remains plain JSON.
    for item in raw["knowledge"]:
        for evidence in item["evidence"]:
            allowed_projects = set(evidence.get("readable_projects", []))
            allowed_teams = set(evidence.get("readable_teams", []))
            evidence["readable_by"] = lambda p, ps=allowed_projects, ts=allowed_teams: (
                bool(ps.intersection(p["projects"])) or bool(ts.intersection(p["teams"]))
            )
    return raw


def run() -> dict:
    corpus = load_fixture()
    a = {"id": "member-a", "teams": ["engineering"], "projects": ["project-a"], "adopted_harness": []}
    b = {"id": "member-b", "teams": ["engineering"], "projects": ["project-b"], "adopted_harness": []}
    outsider = {"id": "outsider", "teams": [], "projects": [], "adopted_harness": []}
    b_adopter = {**b, "adopted_harness": ["H1"]}

    checks: dict[str, bool] = {}

    a_hits = knowledge_recall("regional export permissions", a, corpus)
    b_hits = knowledge_recall("regional data export permissions", b, corpus)
    outsider_hits = knowledge_recall("order export regional permissions", outsider, corpus)
    b_org_hits = knowledge_recall("organization tree authorization", b, corpus)
    no_hit = knowledge_recall("quantum compiler satellite telemetry", b, corpus)

    ids = lambda rows: [row["id"] for row in rows]
    checks["A_finds_team_and_own_project_knowledge"] = {"T1", "A1"}.issubset(set(ids(a_hits)))
    checks["B_finds_team_and_own_project_knowledge"] = {"T1", "B1"}.issubset(set(ids(b_hits)))
    checks["B_never_receives_A_project_knowledge"] = "A1" not in ids(b_hits)
    checks["outsider_receives_no_private_knowledge"] = outsider_hits == []
    checks["B_specific_query_prefers_own_business_rule"] = ids(b_org_hits) == ["B1"]
    checks["no_hit_is_empty_knowledge_result"] = no_hit == []

    # No private metadata, title, evidence ID or source pointer may leak through
    # the returned candidate envelope, not merely the full body.
    serialized_b = json.dumps(b_hits, ensure_ascii=False)
    forbidden = ["A1", "A-S1", "C1", "C2", "order-8472", "Project A"]
    checks["B_result_has_no_A_private_metadata"] = all(x not in serialized_b for x in forbidden)
    checks["team_claim_is_generalized"] = all(
        x not in next(row for row in b_hits if row["id"] == "T1")["claim"]
        for x in ["order-8472", "Project A", "C1", "C2"]
    )

    t1 = next(row for row in b_hits if row["id"] == "T1")
    checks["team_knowledge_visible_without_origin_evidence"] = (
        t1["evidence"] and all(not ev["readable"] for ev in t1["evidence"])
    )

    # Distinct providers remain distinct; B gets only its own sources/code.
    b_sources = source_search("regional data export", b, corpus)
    b_code = code_retrieval("regional export module", b, corpus)
    checks["B_source_search_returns_only_B_sources"] = b_sources == ["B-S1"]
    checks["B_code_retrieval_returns_only_B_code"] = b_code == ["B-C1"]
    checks["A_source_not_in_knowledge_recall"] = "A-S1" not in ids(a_hits)
    checks["B_source_not_in_knowledge_recall"] = "B-S1" not in ids(b_hits)

    checks["harness_not_returned_by_knowledge_recall"] = "H1" not in ids(b_hits)
    checks["unadopted_harness_not_resolved"] = harness_resolution(b, corpus) == []
    checks["adopted_harness_resolved_by_capability_path"] = harness_resolution(b_adopter, corpus) == ["H1"]

    # Revocation simulation: source-origin evidence is revoked for future reads.
    revoked = {**b, "teams": []}
    revoked_hits = knowledge_recall("regional data export permissions", revoked, corpus)
    checks["team_membership_revocation_removes_future_recall"] = "T1" not in ids(revoked_hits)
    revoked_corpus = {**corpus, "knowledge": [
        {**item, "distribution_status": "paused"} if item["id"] == "T1" else item
        for item in corpus["knowledge"]
    ]}
    grant_revoked_hits = knowledge_recall("regional data export permissions", b, revoked_corpus)
    checks["source_derivation_revocation_pauses_future_team_recall"] = "T1" not in ids(grant_revoked_hits) and "B1" in ids(grant_revoked_hits)
    checks["project_B_knowledge_remains_with_project_membership"] = "B1" in ids(b_hits)

    # Release authority and Recall projection freshness are separate dimensions.
    paused_release_corpus = {**corpus, "knowledge": [
        {**item, "distribution_status": "paused"} if item["id"] == "T1" else item
        for item in corpus["knowledge"]
    ]}
    stale_after_pause = recall_with_projection(
        "regional data export permissions", b, paused_release_corpus, "Stale"
    )
    unavailable = recall_with_projection(
        "quantum compiler satellite telemetry", b, corpus, "Unavailable"
    )
    stale_no_hit = recall_with_projection(
        "quantum compiler satellite telemetry", b, corpus, "Stale"
    )
    complete_no_hit = recall_with_projection(
        "quantum compiler satellite telemetry", b, corpus, "Current"
    )
    checks["paused_release_blocked_even_when_projection_stale"] = "T1" not in ids(stale_after_pause["hits"])
    checks["unavailable_projection_not_reported_as_no_match"] = unavailable["coverage"] == "Unavailable"
    checks["stale_projection_not_reported_as_complete_no_match"] = stale_no_hit["coverage"] == "Partial / Stale"
    checks["complete_current_no_hit_is_distinguished"] = complete_no_hit["coverage"] == "Complete" and complete_no_hit["hits"] == []
    checks["projection_failure_does_not_change_release_authority"] = all(
        item.get("distribution_status", "active") == "active" for item in corpus["knowledge"]
    )
    checks["projection_current_is_not_release_authority"] = (
        "T1" not in ids(knowledge_recall(
            "regional data export permissions", b, paused_release_corpus
        ))
    )

    # Scope filtering happens before serialization: no result envelope for A1.
    checks["unauthorized_candidate_not_serialized"] = "A1" not in json.dumps(b_hits)

    failed = [name for name, ok in checks.items() if not ok]
    return {
        "experiment": "two-project-recall-contract",
        "mode": "contract-level deterministic provider simulation",
        "not_claimed": [
            "production search quality",
            "semantic retrieval quality",
            "real connector authorization",
            "real Codex/Claude/Qoder/CodeBuddy host delivery",
            "actual knowledge use by an Agent",
        ],
        "checks_passed": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed": failed,
        "checks": checks,
        "observations": {
            "project_a_knowledge": ids(a_hits),
            "project_b_knowledge": ids(b_hits),
            "outsider_knowledge": ids(outsider_hits),
            "project_b_org_query": ids(b_org_hits),
            "project_b_sources": b_sources,
            "project_b_code": b_code,
            "project_b_harness_without_adoption": harness_resolution(b, corpus),
            "project_b_harness_with_adoption": harness_resolution(b_adopter, corpus),
            "project_b_no_hit": ids(no_hit),
            "stale_after_release_pause": {"coverage": stale_after_pause["coverage"], "hits": ids(stale_after_pause["hits"])},
            "unavailable_projection": unavailable["coverage"],
            "stale_projection_no_hit": stale_no_hit["coverage"],
            "complete_projection_no_hit": complete_no_hit["coverage"],
        },
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(1 if result["failed"] else 0)
