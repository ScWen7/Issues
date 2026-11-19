import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import {
  evaluateOrderExport,
  consumeEvaluationByWorkOwner,
  routeFinding,
  linkPriorKnowledgeContribution
} from "./order-evaluation-closure.mjs";

const fixture = (name) => {
  const url = new URL(`../../docs/research/topic-03a/fixtures/order-export-${name.toLowerCase()}.json`, import.meta.url);
  const raw = readFileSync(fileURLToPath(url));
  return {
    report: JSON.parse(raw.toString("utf8")),
    sha256: createHash("sha256").update(raw).digest("hex")
  };
};

test("C1 evaluation records a high-severity authorization-scope Finding with exact evidence", () => {
  const { report, sha256 } = fixture("C1");
  const result = evaluateOrderExport(report, sha256);
  assert.equal(result.evaluation.status, "scored");
  assert.equal(result.evaluation.sourceRunId, "verify-C1");
  assert.equal(result.evaluation.evaluationRunId, "evaluation:verify-C1");
  assert.equal(result.evaluation.weightedScore, 0.3);
  assert.equal(result.observed.a2Pass, false);
  assert.equal(result.observed.a3Pass, true);
  assert.deepEqual(result.observed.eastLeaks, ["B-201"]);
  assert.equal(result.findings.length, 1);
  assert.equal(result.findings[0].severity, "high");
  assert.equal(result.findings[0].rootCause.status, "unknown");
  assert.ok(result.findings[0].evidenceRefs.some((ref) => ref.includes(sha256)));
});

test("C2 evaluation finds both D2 checks satisfied and does not invent a Finding", () => {
  const { report, sha256 } = fixture("C2");
  const result = evaluateOrderExport(report, sha256);
  assert.equal(result.evaluation.status, "scored");
  assert.equal(result.evaluation.sourceRunId, "verify-C2");
  assert.equal(result.evaluation.weightedScore, 1);
  assert.equal(result.observed.a2Pass, true);
  assert.equal(result.observed.a3Pass, true);
  assert.deepEqual(result.findings, []);
});

test("post-run evaluation is advisory and cannot become a gate by score alone", () => {
  const { report, sha256 } = fixture("C2");
  const result = evaluateOrderExport(report, sha256);
  assert.equal(result.gateDisposition, "advisory_only");
});

test("an explicitly declared gate requires the exact source Run and scorer version", async () => {
  const { report, sha256 } = fixture("C2");
  const result = evaluateOrderExport(report, sha256);
  const { gateDisposition } = await import("./evaluation.mjs");
  assert.equal(gateDisposition(result.evaluation, {
    declared: true,
    sourceRunId: "verify-C2",
    scorerVersion: "order-export-review-v1",
    minimumScore: 0.95
  }), "pass");
  assert.equal(gateDisposition(result.evaluation, {
    declared: true,
    sourceRunId: "verify-C1",
    scorerVersion: "order-export-review-v1",
    minimumScore: 0.1
  }), "inconclusive");
});

test("a non-terminal source Run defers evaluation", async () => {
  const { createEvaluationRecord } = await import("./evaluation.mjs");
  assert.deepEqual(createEvaluationRecord({
    terminal: false,
    sourceRunId: "verify-C1",
    evaluationRunId: "evaluation:verify-C1"
  }), { status: "deferred", reason: "source_run_not_terminal" });
});

test("missing role evidence makes the evaluation inconclusive, not a failure", () => {
  const { report, sha256 } = fixture("C2");
  delete report.checks.viewer;
  const result = evaluateOrderExport(report, sha256);
  assert.equal(result.evaluation.status, "inconclusive");
  assert.equal(result.evaluation.weightedScore, null);
  assert.deepEqual(result.findings, []);
});

test("tampered source report bytes are rejected before evaluation", () => {
  const { report, sha256 } = fixture("C1");
  assert.throws(() => evaluateOrderExport(report, `0${sha256.slice(1)}`), /digest mismatch/);
});

test("B may return C1 for rework but the decision does not mutate Run or Evaluation", () => {
  const { report, sha256 } = fixture("C1");
  const result = evaluateOrderExport(report, sha256);
  const decision = consumeEvaluationByWorkOwner({
    evaluation: result.evaluation,
    findingIds: result.findings.map((finding) => finding.id),
    actorRole: "issue_accountable_member",
    decision: "return_for_rework"
  });
  assert.equal(decision.decision, "return_for_rework");
  assert.equal(decision.issueCompletion, "unchanged");
  assert.equal(decision.sourceRunMutation, "none");
  assert.equal(decision.evaluationMutation, "none");
});

test("C2 may be forwarded to business acceptance but Evaluation does not accept the Issue", () => {
  const { report, sha256 } = fixture("C2");
  const result = evaluateOrderExport(report, sha256);
  const decision = consumeEvaluationByWorkOwner({
    evaluation: result.evaluation,
    findingIds: [],
    actorRole: "issue_accountable_member",
    decision: "forward_to_business_acceptance"
  });
  assert.equal(decision.decision, "forward_to_business_acceptance");
  assert.equal(decision.issueCompletion, "unchanged");
});

test("an Agent or evaluator cannot impersonate the Issue accountable member", () => {
  const { report, sha256 } = fixture("C1");
  const result = evaluateOrderExport(report, sha256);
  assert.throws(() => consumeEvaluationByWorkOwner({
    evaluation: result.evaluation,
    findingIds: result.findings.map((finding) => finding.id),
    actorRole: "evaluator",
    decision: "return_for_rework"
  }), /only the Issue accountable member/);
});

test("a single current-work Finding routes to B without creating asset proposals", () => {
  const { report, sha256 } = fixture("C1");
  const finding = evaluateOrderExport(report, sha256).findings[0];
  const routes = routeFinding(finding, ["current_work"]);
  assert.deepEqual(routes.map((route) => route.owner), ["B"]);
  assert.equal(routes[0].status, "issue_action_requested");
  assert.equal(routes[0].releaseCreated, false);
});

test("one evidence-backed Finding may create separate A and C triage paths, never a merged release", () => {
  const finding = {
    id: "finding:synthetic:missing-regression-method",
    evidenceRefs: ["run:verify-C1", "run:verify-C2", "evidence:reports-c1-c2"]
  };
  const routes = routeFinding(finding, ["knowledge", "harness"]);
  assert.deepEqual(routes.map((route) => route.owner), ["A", "C"]);
  assert.equal(routes[0].sourceFindingId, routes[1].sourceFindingId);
  assert.notEqual(routes[0].target, routes[1].target);
  assert.ok(routes.every((route) => route.status === "proposal_for_owner_triage"));
  assert.ok(routes.every((route) => route.releaseCreated === false && route.adoptionChanged === false));
});

test("E links the existing A contribution by exact C1/C2 evidence and respects its retired state", () => {
  const url = new URL("../../docs/research/topic-03b/fixtures/project-knowledge.json", import.meta.url);
  const contribution = JSON.parse(readFileSync(fileURLToPath(url), "utf8"));
  const linked = linkPriorKnowledgeContribution(
    contribution,
    "da022445c03fa787af994101f47cd8cfb777913f882a6b7aa32116a3493afcb1",
    "e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514"
  );
  assert.equal(linked.proposalId, "b506b31bbe5da5e1ee898bee7edbe51996d10b441c61d4cc46cdaae72dfbdea5");
  assert.equal(linked.assetKey, "export-scope-regression");
  assert.equal(linked.historicalStatus, "retired");
  assert.equal(linked.nextAction, "knowledge_owner_review_required");
  assert.equal(linked.newKnowledgeReleaseCreated, false);
});

test("a Finding without evidence cannot be routed into knowledge or Harness publication", () => {
  assert.throws(() => routeFinding({ id: "finding:no-evidence", evidenceRefs: [] }, ["knowledge", "harness"]), /requires stable identity and evidence/);
});
