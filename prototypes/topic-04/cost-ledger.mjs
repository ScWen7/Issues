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

export function normalizeRuntimeCreditObservation(input) {
  if (!["qoder", "codebuddy"].includes(input?.provider)) {
    throw new Error("unsupported Credits runtime provider");
  }
  if (!Number.isFinite(input.credits) || !input.observedAt) {
    return {
      provider: input.provider,
      source: "runtime",
      sourceNamespace: input.memberId ?? "member-unresolved",
      nativeRequestId: input.eventId ?? null,
      runId: input.runId ?? null,
      memberId: input.memberId ?? null,
      metric: "credits_consumed",
      unit: input.provider === "qoder" ? "qoder_credit" : "codebuddy_credit",
      value: null,
      status: "unknown",
      unknownReason: "runtime_did_not_report_credits",
      observedAt: input.observedAt ?? null
    };
  }
  return {
    source: "runtime",
    sourceNamespace: input.memberId ?? "member-unresolved",
    nativeRequestId: input.eventId ?? null,
    provider: input.provider,
    runId: input.runId ?? null,
    attributionStatus: input.runId ? "runtime_run_binding" : "runtime_event_unallocated",
    memberId: input.memberId ?? null,
    metric: "credits_consumed",
    unit: input.provider === "qoder" ? "qoder_credit" : "codebuddy_credit",
    value: input.credits,
    eventAt: input.eventAt ?? null,
    observedAt: input.observedAt,
    attributes: {
      modelTier: input.modelTier ?? null,
      operation: input.operation ?? null,
      sessionId: input.sessionId ?? null,
      turnId: input.turnId ?? null
    },
    currency: null,
    trustRank: 3,
    status: "observed"
  };
}

export function normalizeQoderSdkMessage(message, binding = {}) {
  const sessionId = binding.sessionId ?? message?.session_id ?? null;
  const base = {
    provider: "qoder",
    source: "qoder-agent-sdk",
    sourceNamespace: binding.hostNamespace ?? "qoder-local-runtime",
    sessionId,
    runId: binding.runId ?? null,
    memberId: binding.memberId ?? null
  };
  if (message?.type === "assistant") {
    const usage = message.message?.usage;
    if (!Number.isFinite(usage?.credits)) {
      return {
        ...base,
        nativeRequestId: message.uuid ?? null,
        metric: "credits_consumed",
        unit: "qoder_credit",
        value: null,
        status: "unknown",
        unknownReason: "qoder_sdk_assistant_message_has_no_credits",
        billable: usage?.billable ?? null
      };
    }
    return {
      ...base,
      nativeRequestId: message.uuid ?? null,
      metric: "credits_consumed",
      unit: "qoder_credit",
      value: usage.credits,
      originalCredits: Number.isFinite(usage.original_credits) ? usage.original_credits : null,
      billable: typeof usage.billable === "boolean" ? usage.billable : null,
      model: message.message?.model ?? null,
      observedAt: message.timestamp ?? null,
      status: "observed",
      scope: "model_request"
    };
  }
  if (message?.type === "result") {
    if (!Number.isFinite(message.total_credits)) {
      return {
        ...base,
        nativeRequestId: message.uuid ?? null,
        metric: "session_total_credits",
        unit: "qoder_credit",
        value: null,
        status: "unknown",
        unknownReason: "qoder_sdk_result_has_no_total_credits",
        scope: "session_snapshot"
      };
    }
    return {
      ...base,
      nativeRequestId: message.uuid ?? null,
      metric: "session_total_credits",
      unit: "qoder_credit",
      value: message.total_credits,
      modelUsage: message.modelUsage ?? null,
      observedAt: message.timestamp ?? null,
      status: "observed",
      scope: "session_snapshot"
    };
  }
  return null;
}

export function normalizeCodeBuddyUsageUpdate(message, binding = {}) {
  if (message?.type !== "system" || message.subtype !== "usage_update") return null;
  const metadata = message._meta?.["codebuddy.ai/turnUsage"];
  if (!metadata || metadata.version !== 1 || metadata.scope !== "turn") return null;
  const sessionId = message.session_id ?? binding.sessionId ?? null;
  const requestId = metadata.requestId ?? message._requestId ?? null;
  const common = {
    provider: "codebuddy",
    source: "codebuddy-stream-json",
    sourceNamespace: binding.hostNamespace ?? "codebuddy-local-runtime",
    sessionId,
    requestId,
    runId: binding.runId ?? null,
    memberId: binding.memberId ?? null
  };
  if (metadata.kind === "stage" && metadata.stage?.id) {
    const stage = metadata.stage;
    return {
      ...common,
      nativeRequestId: stage.id,
      metric: "credits_consumed",
      unit: "codebuddy_credit",
      value: Number.isFinite(stage.credits) ? stage.credits : null,
      status: Number.isFinite(stage.credits) ? "observed" : "unknown",
      unknownReason: Number.isFinite(stage.credits) ? null : "codebuddy_stage_has_no_credits",
      model: stage.model ?? null,
      stageSource: stage.source ?? null,
      messageId: stage.messageId ?? null,
      observedAt: message.timestamp ?? null,
      scope: "turn_stage",
      kind: "stage"
    };
  }
  if (metadata.kind === "snapshot") {
    return {
      ...common,
      nativeRequestId: requestId,
      metric: "turn_total_credits",
      unit: "codebuddy_credit",
      value: Number.isFinite(metadata.total?.credits) ? metadata.total.credits : null,
      status: Number.isFinite(metadata.total?.credits) && metadata.total?.creditStatus !== "unknown"
        ? "observed" : "unknown",
      unknownReason: Number.isFinite(metadata.total?.credits) ? null : "codebuddy_snapshot_has_no_credits",
      stages: Array.isArray(metadata.stages) ? metadata.stages : [],
      observedAt: message.timestamp ?? null,
      scope: "turn_snapshot",
      kind: "snapshot"
    };
  }
  return null;
}

export function reconcileCodeBuddyTurn(events) {
  const stages = new Map();
  let snapshot = null;
  for (const event of events) {
    if (event?.provider !== "codebuddy" || event?.unit !== "codebuddy_credit") continue;
    if (event.kind === "stage" && event.nativeRequestId) {
      stages.set(event.nativeRequestId, event);
    } else if (event.kind === "snapshot") {
      snapshot = event;
      if (Array.isArray(event.stages)) {
        for (const stage of event.stages) {
          if (!stage?.id) continue;
          stages.set(stage.id, {
            ...event,
            nativeRequestId: stage.id,
            metric: "credits_consumed",
            value: Number.isFinite(stage.credits) ? stage.credits : null,
            status: Number.isFinite(stage.credits) ? "observed" : "unknown",
            kind: "stage",
            model: stage.model ?? null,
            stageSource: stage.source ?? null
          });
        }
      }
    }
  }
  const rows = [...stages.values()];
  const allKnown = rows.length > 0 && rows.every((row) => row.status === "observed" && Number.isFinite(row.value));
  const stageTotal = allKnown ? rows.reduce((sum, row) => sum + row.value, 0) : null;
  const snapshotTotal = snapshot?.status === "observed" ? snapshot.value : null;
  return {
    status: snapshotTotal !== null || allKnown ? "observed" : "unknown",
    totalCredits: snapshotTotal ?? stageTotal,
    totalSource: snapshotTotal !== null ? "terminal_snapshot" : (allKnown ? "stage_sum_provisional" : null),
    stages: rows,
    snapshot: snapshot ?? null
  };
}

export function creditsUnavailable(provider, runId, reason = "runtime_usage_unavailable") {
  if (!["qoder", "codebuddy"].includes(provider)) throw new Error("unsupported Credits runtime provider");
  return {
    provider,
    runId: runId ?? null,
    metric: "credits_consumed",
    unit: provider === "qoder" ? "qoder_credit" : "codebuddy_credit",
    value: null,
    status: "unknown",
    unknownReason: reason
  };
}

export function aggregateRunCosts(entries, runIds, targetUnit = "USD") {
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
