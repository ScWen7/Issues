const keyOf = (o) => {
  if (!o.nativeRequestId || !o.sourceNamespace || !o.metric || !o.unit) return null;
  return [o.sourceNamespace, o.nativeRequestId, o.metric, o.unit].join("|");
};

export function reconcileObservations(observations) {
  const groups = new Map();
  const unlinked = [];
  for (const observation of observations) {
    const key = keyOf(observation);
    if (!key) {
      unlinked.push({ ...observation, disposition: "unlinked" });
      continue;
    }
    const group = groups.get(key) ?? [];
    group.push(observation);
    groups.set(key, group);
  }
  return {
    entries: [...groups].map(([key, evidence]) => {
      const highestRank = Math.max(...evidence.map((item) => item.trustRank ?? 0));
      const authoritative = evidence.filter((item) => (item.trustRank ?? 0) === highestRank);
      const chosen = authoritative[0];
      const conflict = authoritative.some((item) =>
        item.value !== chosen.value ||
        item.currency !== chosen.currency ||
        item.runId !== chosen.runId
      );
      return {
        key,
        runId: conflict ? null : (chosen.runId ?? null),
        provider: chosen.provider ?? null,
        metric: chosen.metric,
        unit: chosen.unit,
        value: conflict ? null : chosen.value,
        currency: conflict ? null : (chosen.currency ?? null),
        status: conflict ? "needs_review" : "reconciled",
        selectedSource: conflict ? null : (chosen.source ?? null),
        evidence: evidence.map((item) => ({
          source: item.source,
          runId: item.runId ?? null,
          value: item.value,
          currency: item.currency ?? null,
          trustRank: item.trustRank ?? 0,
          observedAt: item.observedAt ?? null
        }))
      };
    }),
    unlinked
  };
}

export function deltaFromCumulative(previous, current) {
  if (!previous || !current) return { value: null, status: "unknown", reason: "missing_baseline" };
  if (previous.model !== current.model || previous.metric !== current.metric || previous.unit !== current.unit) {
    return { value: null, status: "unknown", reason: "scope_changed" };
  }
  if (current.sequence <= previous.sequence) return { value: null, status: "unknown", reason: "out_of_order" };
  if (current.value < previous.value) return { value: null, status: "unknown", reason: "counter_reset" };
  return { value: current.value - previous.value, status: "measured", reason: null };
}

export function normalizeQoderUsage(event, identity = {}) {
  if (!event?.eventId || !Number.isFinite(event.credits)) {
    throw new Error("Qoder usage requires stable eventId and numeric credits");
  }
  return {
    source: "qoder-enterprise-usage-api",
    sourceNamespace: identity.organizationId ?? "qoder-org-unresolved",
    nativeRequestId: event.eventId,
    provider: "qoder",
    runId: identity.runId ?? null,
    attributionStatus: identity.runId ? "explicit_run_binding" : "member_event_unallocated",
    memberId: event.memberId ?? event.userId ?? null,
    metric: "credits_consumed",
    unit: "qoder_credit",
    value: event.credits,
    eventAt: event.beginAt ?? (event.timestamp ? new Date(event.timestamp).toISOString() : null),
    finishAt: event.finishAt ?? null,
    attributes: {
      source: event.source ?? null,
      operation: event.operation ?? null,
      modelTier: event.modelTier ?? null
    },
    billingAdjustedCredits: Number.isFinite(event.cost) ? event.cost : null,
    currency: null,
    trustRank: 3
  };
}

export function normalizeCodeBuddyUsage(input) {
  if (!Number.isFinite(input?.credits) || !input.observedAt) {
    throw new Error("CodeBuddy usage requires observed Credits and observation time");
  }
  return {
    source: "codebuddy-account-usage",
    sourceNamespace: input.teamId ?? input.memberId ?? "codebuddy-account-unresolved",
    nativeRequestId: input.eventId ?? null,
    provider: "codebuddy",
    runId: input.runId ?? null,
    memberId: input.memberId ?? null,
    metric: "credits_consumed",
    unit: "codebuddy_credit",
    value: input.credits,
    eventAt: input.eventAt ?? null,
    observedAt: input.observedAt,
    attributes: {
      plan: input.plan ?? null,
      packageType: input.packageType ?? null,
      mode: input.mode ?? null
    },
    currency: null,
    trustRank: input.eventId ? 2 : 1,
    attributionStatus: input.runId ? "explicit_run_binding" : (input.eventId ? "provider_event_unallocated" : "member_period_statement")
  };
}

export function normalizeQoderPackage(pkg, identity = {}) {
  if (!pkg?.id || !Number.isFinite(pkg.limitValue) ||
      !Number.isFinite(pkg.usedValue) || !Number.isFinite(pkg.remainingValue) || !pkg.unit) {
    throw new Error("Qoder package requires id, numeric quota fields and unit");
  }
  return {
    provider: "qoder",
    organizationId: identity.organizationId ?? null,
    packageId: pkg.id,
    source: pkg.source ?? null,
    status: pkg.status ?? null,
    unit: pkg.unit,
    limit: pkg.limitValue,
    used: pkg.usedValue,
    remaining: pkg.remainingValue,
    activatedAt: pkg.activatedAt ?? pkg.createdAt ?? null,
    expiresAt: pkg.expiresAt ?? null,
    observedAt: identity.observedAt ?? null,
    recordType: "quota_snapshot"
  };
}

export function bindUsageToRun(usage, binding) {
  if (!usage || !binding?.runId || !binding.evidenceRef || !binding.method) {
    return { ...usage, runId: null, attributionStatus: "unallocated" };
  }
  return {
    ...usage,
    runId: binding.runId,
    attributionStatus: "explicitly_attributed",
    attributionEvidence: binding.evidenceRef,
    attributionMethod: binding.method
  };
}

export function convertCreditsToMoney(usage, conversion) {
  if (!usage || !conversion ||
      conversion.provider !== usage.provider ||
      conversion.unit !== usage.unit ||
      !Number.isFinite(conversion.moneyPerCredit) ||
      !conversion.currency ||
      !conversion.validFrom ||
      !conversion.sourceRef) {
    return { amount: null, currency: null, status: "unpriced" };
  }
  if (usage.eventAt && usage.eventAt < conversion.validFrom) {
    return { amount: null, currency: null, status: "rate_not_applicable" };
  }
  if (conversion.validUntil && usage.eventAt && usage.eventAt >= conversion.validUntil) {
    return { amount: null, currency: null, status: "rate_not_applicable" };
  }
  return {
    amount: usage.value * conversion.moneyPerCredit,
    currency: conversion.currency,
    status: "estimated",
    conversionSource: conversion.sourceRef,
    conversionVersion: conversion.version ?? null
  };
}

export function aggregateRunCosts(entries, runIds, targetUnit) {
  const selected = new Set(runIds);
  const byKey = new Map();
  const conflicted = new Set();
  for (const entry of entries) {
    if (!selected.has(entry.runId) || entry.status !== "reconciled" ||
        entry.amount == null || entry.currency !== targetUnit) continue;
    const prior = byKey.get(entry.key);
    if (!prior) {
      byKey.set(entry.key, entry);
      continue;
    }
    if (prior.runId !== entry.runId || prior.amount !== entry.amount || prior.currency !== entry.currency) {
      conflicted.add(entry.key);
    }
  }
  return [...byKey].reduce((sum, [key, entry]) =>
    conflicted.has(key) ? sum : sum + entry.amount, 0);
}
