import test from "node:test";
import assert from "node:assert/strict";
import { createEvaluationRecord, gateDisposition, compareBenchmarkConfigs, assessImprovement } from "./evaluation.mjs";

const completeInput = {
  terminal: true,
  sourceRunId: "business-run-1",
  evaluationRunId: "evaluation-run-1",
  evaluator: "model-judge",
  scorerVersion: "judge-v3",
  coverage: { complete: true, missing: [] },
  dimensions: [
    { name: "correctness", score: 0.9, weight: 0.7, evidenceRefs: ["artifact:a2"] },
    { name: "maintainability", score: 0.8, weight: 0.3, evidenceRefs: ["diff:sha256"] }
  ]
};

const config = {
  sampleSetSha256: "samples-a",
  rubricSha256: "rubric-a",
  toolchainSha256: "tools-a",
  model: "model-a",
  effort: "high",
  scorerVersion: "judge-v3",
  aggregation: "mean-of-repeats",
  environmentSha256: "env-a",
  repeatCount: 3
};

test("non-terminal business Run defers evaluation", () => {
  assert.deepEqual(createEvaluationRecord({ ...completeInput, terminal: false }), {
    status: "deferred",
    reason: "source_run_not_terminal"
  });
});

test("evaluation is a separate Run and never mutates the source Run", () => {
  const sourceRun = { id: "business-run-1", status: "succeeded", verdict: null };
  const before = structuredClone(sourceRun);
  const evaluation = createEvaluationRecord(completeInput);
  assert.equal(evaluation.sourceRunId, sourceRun.id);
  assert.equal(evaluation.evaluationRunId, "evaluation-run-1");
  assert.equal(evaluation.status, "scored");
  assert.ok(Math.abs(evaluation.weightedScore - 0.87) < 1e-9);
  assert.deepEqual(sourceRun, before);
});

test("missing evidence yields inconclusive evaluation rather than a low score", () => {
  const evaluation = createEvaluationRecord({
    ...completeInput,
    coverage: { complete: false, missing: ["artifact:a3"] }
  });
  assert.equal(evaluation.status, "inconclusive");
  assert.equal(evaluation.weightedScore, null);
});

test("post-run evaluation is advisory unless an explicit SOP gate declares it", () => {
  const evaluation = createEvaluationRecord(completeInput);
  assert.equal(gateDisposition(evaluation, null), "advisory_only");
  assert.equal(gateDisposition(evaluation, { declared: false }), "advisory_only");
  assert.equal(gateDisposition(evaluation, {
    declared: true,
    sourceRunId: "business-run-1",
    scorerVersion: "judge-v3",
    minimumScore: 0.85
  }), "pass");
});

test("gate cannot consume evaluation for a different Run or scorer version", () => {
  const evaluation = createEvaluationRecord(completeInput);
  assert.equal(gateDisposition(evaluation, {
    declared: true,
    sourceRunId: "other-run",
    scorerVersion: "judge-v3",
    minimumScore: 0.5
  }), "inconclusive");
  assert.equal(gateDisposition(evaluation, {
    declared: true,
    sourceRunId: "business-run-1",
    scorerVersion: "judge-v2",
    minimumScore: 0.5
  }), "inconclusive");
});

test("benchmark comparison requires matching samples, rubric, tools, model and environment", () => {
  assert.deepEqual(compareBenchmarkConfigs(config, { ...config }), {
    comparable: true,
    differences: []
  });
  const result = compareBenchmarkConfigs(config, { ...config, model: "model-b", rubricSha256: "rubric-b" });
  assert.equal(result.comparable, false);
  assert.deepEqual(result.differences, ["rubricSha256", "model"]);
});

test("different repeat counts are not silently compared", () => {
  const result = compareBenchmarkConfigs(config, { ...config, repeatCount: 5 });
  assert.equal(result.comparable, false);
  assert.deepEqual(result.differences, ["repeatCount"]);
});

test("improvement is only proposed for review when comparable and within cost guardrail", () => {
  const baseline = { config, quality: 0.82, cost: 1 };
  const candidate = { config: { ...config }, quality: 0.88, cost: 1.05 };
  assert.deepEqual(assessImprovement({
    baseline, candidate, minimumQualityDelta: 0.03, maximumCostIncrease: 0.1
  }), {
    decision: "candidate_for_review",
    qualityDelta: 0.06,
    costDelta: 0.05
  });
});

test("improvement rejects quality regression, excess cost and incomparable configs", () => {
  const baseline = { config, quality: 0.82, cost: 1 };
  assert.equal(assessImprovement({
    baseline, candidate: { config, quality: 0.83, cost: 1 },
    minimumQualityDelta: 0.03, maximumCostIncrease: 0.1
  }).reason, "quality_improvement_below_threshold");
  assert.equal(assessImprovement({
    baseline, candidate: { config, quality: 0.9, cost: 1.2 },
    minimumQualityDelta: 0.03, maximumCostIncrease: 0.1
  }).reason, "cost_increase_above_threshold");
  assert.equal(assessImprovement({
    baseline, candidate: { config: { ...config, model: "model-b" }, quality: 0.9, cost: 0.8 },
    minimumQualityDelta: 0.03, maximumCostIncrease: 0.1
  }).decision, "not_comparable");
});
