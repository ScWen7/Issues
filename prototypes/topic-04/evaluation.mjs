const REQUIRED_BENCHMARK_FIELDS = [
  "sampleSetSha256",
  "rubricSha256",
  "toolchainSha256",
  "model",
  "effort",
  "scorerVersion",
  "aggregation",
  "environmentSha256"
];

export function createEvaluationRecord(input) {
  if (!input.terminal) return { status: "deferred", reason: "source_run_not_terminal" };
  if (!input.sourceRunId || !input.evaluationRunId || input.sourceRunId === input.evaluationRunId) {
    throw new Error("evaluation requires a distinct evaluation Run");
  }
  const dimensions = input.dimensions ?? [];
  for (const dimension of dimensions) {
    if (!Number.isFinite(dimension.score) || dimension.score < 0 || dimension.score > 1) {
      throw new Error("dimension score must be between 0 and 1");
    }
    if (!Number.isFinite(dimension.weight) || dimension.weight <= 0) {
      throw new Error("dimension weight must be positive");
    }
  }
  const complete = input.coverage?.complete === true &&
    dimensions.length > 0 &&
    dimensions.every((dimension) => Array.isArray(dimension.evidenceRefs) && dimension.evidenceRefs.length > 0);
  const weightTotal = dimensions.reduce((sum, dimension) => sum + dimension.weight, 0);
  const weightedScore = complete
    ? dimensions.reduce((sum, dimension) => sum + dimension.score * dimension.weight, 0) / weightTotal
    : null;
  return {
    status: complete ? "scored" : "inconclusive",
    sourceRunId: input.sourceRunId,
    evaluationRunId: input.evaluationRunId,
    evaluator: input.evaluator,
    scorerVersion: input.scorerVersion,
    dimensions: dimensions.map((dimension) => ({ ...dimension })),
    coverage: { ...input.coverage },
    weightedScore,
    createdAt: input.createdAt ?? null
  };
}

export function gateDisposition(evaluation, gate) {
  if (!gate || gate.declared !== true) return "advisory_only";
  if (!evaluation || evaluation.status !== "scored") return "inconclusive";
  if (evaluation.sourceRunId !== gate.sourceRunId ||
      evaluation.scorerVersion !== gate.scorerVersion ||
      evaluation.weightedScore == null) return "inconclusive";
  return evaluation.weightedScore >= gate.minimumScore ? "pass" : "fail";
}

export function compareBenchmarkConfigs(left, right) {
  const differences = REQUIRED_BENCHMARK_FIELDS.filter((field) => left[field] !== right[field]);
  if (left.repeatCount !== right.repeatCount) differences.push("repeatCount");
  return {
    comparable: differences.length === 0,
    differences
  };
}

const rounded = (value) => Number.isFinite(value) ? Number(value.toFixed(6)) : value;

export function assessImprovement(input) {
  const comparison = compareBenchmarkConfigs(input.baseline.config, input.candidate.config);
  if (!comparison.comparable) return { decision: "not_comparable", differences: comparison.differences };
  const qualityDelta = input.candidate.quality - input.baseline.quality;
  const costDelta = input.baseline.cost === 0
    ? (input.candidate.cost === 0 ? 0 : Infinity)
    : (input.candidate.cost - input.baseline.cost) / input.baseline.cost;
  if (qualityDelta < input.minimumQualityDelta) {
    return { decision: "reject", reason: "quality_improvement_below_threshold", qualityDelta: rounded(qualityDelta), costDelta: rounded(costDelta) };
  }
  if (costDelta > input.maximumCostIncrease) {
    return { decision: "reject", reason: "cost_increase_above_threshold", qualityDelta: rounded(qualityDelta), costDelta: rounded(costDelta) };
  }
  return { decision: "candidate_for_review", qualityDelta: rounded(qualityDelta), costDelta: rounded(costDelta) };
}
