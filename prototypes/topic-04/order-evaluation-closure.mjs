import { createEvaluationRecord, gateDisposition } from "./evaluation.mjs";

const ALLOWED_EAST_ORDERS = new Set(["A-101", "A-102"]);
const EXPECTED_REPORT_SHA = {
  C1: "da022445c03fa787af994101f47cd8cfb777913f882a6b7aa32116a3493afcb1",
  C2: "e9c93051c5b844cf23aa89061eed967c5a2267e846e26b37ece7275f194bd514"
};

export function evaluateOrderExport(report, reportSha256) {
  if (!report || !["C1", "C2"].includes(report.candidate)) {
    throw new Error("unsupported order-export candidate");
  }
  if (reportSha256 !== EXPECTED_REPORT_SHA[report.candidate]) {
    throw new Error("source report digest mismatch");
  }
  const east = report.checks?.east;
  const west = report.checks?.west;
  const cross = report.checks?.cross;
  const viewer = report.checks?.viewer;
  const artifacts = report.artifacts ?? [];
  const coverageComplete = Boolean(
    east && west && cross && viewer &&
    artifacts.length === 3 &&
    report.verifier_sha256 &&
    [east, west, cross].every((check) => check.exit === 0 && check.workbook === true)
  );
  const eastLeaks = (east?.ids ?? []).filter((id) => !ALLOWED_EAST_ORDERS.has(id));
  const a2Pass = east?.A2 === true && west?.A2 === true &&
    cross?.A2 === true && viewer?.A2 === true && eastLeaks.length === 0;
  const a3Pass = east?.A3 === true && west?.A3 === true && cross?.A3 === true &&
    viewer?.exit === 3 && viewer?.workbook === false;

  const dimensions = [
    {
      name: "authorization_scope",
      score: a2Pass ? 1 : 0,
      weight: 0.7,
      evidenceRefs: [
        `source-report:${report.candidate}@${reportSha256}`,
        `artifact:east.xlsx@${artifacts.find((item) => item.name === "east.xlsx")?.sha256 ?? "missing"}`
      ]
    },
    {
      name: "workbook_correctness",
      score: a3Pass ? 1 : 0,
      weight: 0.3,
      evidenceRefs: [
        `source-report:${report.candidate}@${reportSha256}`,
        `verifier@${report.verifier_sha256}`,
        ...artifacts.map((item) => `artifact:${item.name}@${item.sha256}`)
      ]
    }
  ];
  const evaluation = createEvaluationRecord({
    terminal: true,
    sourceRunId: report.run,
    evaluationRunId: `evaluation:${report.run}`,
    evaluator: "deterministic-order-export-reviewer",
    scorerVersion: "order-export-review-v1",
    coverage: {
      complete: coverageComplete && dimensions.every((dimension) => dimension.evidenceRefs.every((ref) => !ref.endsWith("@missing"))),
      missing: coverageComplete ? [] : ["role_checks_or_artifact_manifest"]
    },
    dimensions
  });

  const findings = [];
  if (evaluation.status === "scored" && !a2Pass) {
    findings.push({
      id: `finding:${report.candidate}:east-scope-leak`,
      sourceIssueId: report.issue,
      sourceRunId: report.run,
      candidateId: report.candidate,
      category: "candidate_defect",
      severity: "high",
      observedFact: "East-region export contains an order outside the east-region allowlist.",
      leakedOrderIds: eastLeaks,
      rootCause: { status: "unknown", hypothesis: null },
      evidenceRefs: dimensions[0].evidenceRefs,
      suggestedTargets: ["current_work"]
    });
  }
  return {
    evaluation,
    gateDisposition: gateDisposition(evaluation, null),
    findings,
    observed: { a2Pass, a3Pass, eastLeaks }
  };
}

export function consumeEvaluationByWorkOwner({ evaluation, findingIds, actorRole, decision }) {
  if (actorRole !== "issue_accountable_member") {
    throw new Error("only the Issue accountable member may consume the evaluation as a work decision");
  }
  if (!evaluation || evaluation.status !== "scored") {
    throw new Error("inconclusive evaluation cannot drive a work decision");
  }
  const allowed = new Set(["return_for_rework", "forward_to_business_acceptance"]);
  if (!allowed.has(decision)) throw new Error("unsupported Issue decision");
  if (!Array.isArray(findingIds)) throw new Error("findingIds must be explicit");
  if (decision === "return_for_rework" && findingIds.length === 0) {
    throw new Error("rework decision requires at least one Finding");
  }
  return {
    issueId: "order-export-verification",
    sourceRunId: evaluation.sourceRunId,
    evaluationRunId: evaluation.evaluationRunId,
    findingIds: [...findingIds],
    decidedByRole: actorRole,
    decision,
    issueCompletion: "unchanged",
    sourceRunMutation: "none",
    evaluationMutation: "none"
  };
}

export function routeFinding(finding, targets) {
  if (!finding?.id || !Array.isArray(finding.evidenceRefs) || finding.evidenceRefs.length === 0) {
    throw new Error("Finding requires stable identity and evidence");
  }
  const owners = {
    current_work: "B",
    knowledge: "A",
    harness: "C",
    runtime: "D",
    evaluation: "E"
  };
  const uniqueTargets = [...new Set(targets)];
  if (uniqueTargets.some((target) => !owners[target])) throw new Error("unknown Finding target");
  return uniqueTargets.map((target) => ({
    sourceFindingId: finding.id,
    owner: owners[target],
    target,
    status: target === "current_work" ? "issue_action_requested" : "proposal_for_owner_triage",
    releaseCreated: false,
    adoptionChanged: false,
    sourceFindingPreserved: true
  }));
}
