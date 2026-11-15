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
      const ordered = [...evidence].sort((a, b) =>
        (b.trustRank ?? 0) - (a.trustRank ?? 0)
      );
      const chosen = ordered[0];
      const conflict = ordered.some((item) =>
        item.value !== chosen.value || item.currency !== chosen.currency
      );
      return {
        key,
        runId: chosen.runId ?? null,
        metric: chosen.metric,
        unit: chosen.unit,
        value: conflict ? null : chosen.value,
        currency: conflict ? null : (chosen.currency ?? null),
        status: conflict ? "needs_review" : "reconciled",
        evidence: evidence.map((item) => ({
          source: item.source,
          value: item.value,
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

export function aggregateRunCosts(entries, runIds) {
  const selected = new Set(runIds);
  const unique = new Map();
  for (const entry of entries) {
    if (!selected.has(entry.runId) || entry.status !== "reconciled") continue;
    unique.set(entry.key, entry);
  }
  return [...unique.values()].reduce((sum, entry) => sum + (entry.amount ?? 0), 0);
}
