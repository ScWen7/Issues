import test from "node:test";
import assert from "node:assert/strict";
import {
  reconcileObservations, deltaFromCumulative, aggregateRunCosts,
  normalizeQoderUsage, normalizeCodeBuddyUsage, convertCreditsToMoney
} from "./cost-ledger.mjs";

test("deduplicates multiple observers of one native request but retains evidence", () => {
  const result = reconcileObservations([
    { source: "hook", sourceNamespace: "codex:profile-A", nativeRequestId: "req-1", metric: "input_tokens", unit: "token", value: 120, runId: "run-1", trustRank: 1 },
    { source: "daemon", sourceNamespace: "codex:profile-A", nativeRequestId: "req-1", metric: "input_tokens", unit: "token", value: 120, runId: "run-1", trustRank: 2 }
  ]);
  assert.equal(result.entries.length, 1);
  assert.equal(result.entries[0].value, 120);
  assert.equal(result.entries[0].evidence.length, 2);
  assert.equal(result.entries[0].selectedSource, "daemon");
});

test("same native ID in different namespaces is not merged", () => {
  const result = reconcileObservations([
    { source: "a", sourceNamespace: "profile-A", nativeRequestId: "req-1", metric: "input_tokens", unit: "token", value: 10 },
    { source: "b", sourceNamespace: "profile-B", nativeRequestId: "req-1", metric: "input_tokens", unit: "token", value: 10 }
  ]);
  assert.equal(result.entries.length, 2);
});

test("equal-rank conflicting observations remain unresolved", () => {
  const result = reconcileObservations([
    { source: "daemon", sourceNamespace: "codex:A", nativeRequestId: "req-2", metric: "output_tokens", unit: "token", value: 30, runId: "run-1", trustRank: 2 },
    { source: "otel", sourceNamespace: "codex:A", nativeRequestId: "req-2", metric: "output_tokens", unit: "token", value: 31, runId: "run-1", trustRank: 2 }
  ]);
  assert.equal(result.entries[0].status, "needs_review");
  assert.equal(result.entries[0].value, null);
});

test("highest-ranked evidence supersedes lower-ranked disagreement but preserves it", () => {
  const result = reconcileObservations([
    { source: "transcript", sourceNamespace: "claude:A", nativeRequestId: "msg-1", metric: "input_tokens", unit: "token", value: 10, runId: "run-1", trustRank: 1 },
    { source: "provider", sourceNamespace: "claude:A", nativeRequestId: "msg-1", metric: "input_tokens", unit: "token", value: 12, runId: "run-1", trustRank: 3 }
  ]);
  assert.equal(result.entries[0].status, "reconciled");
  assert.equal(result.entries[0].value, 12);
  assert.equal(result.entries[0].evidence.length, 2);
});

test("equal-rank disagreement about Run ownership is not attributed", () => {
  const result = reconcileObservations([
    { source: "a", sourceNamespace: "codex:A", nativeRequestId: "req-3", metric: "cost", unit: "usd", value: 0.1, runId: "run-a", trustRank: 2 },
    { source: "b", sourceNamespace: "codex:A", nativeRequestId: "req-3", metric: "cost", unit: "usd", value: 0.1, runId: "run-b", trustRank: 2 }
  ]);
  assert.equal(result.entries[0].status, "needs_review");
  assert.equal(result.entries[0].runId, null);
});

test("missing native identity is left unlinked", () => {
  const result = reconcileObservations([{ source: "import", metric: "cost", unit: "usd", value: 0.03 }]);
  assert.equal(result.unlinked.length, 1);
  assert.equal(result.entries.length, 0);
});

test("cumulative snapshots produce a delta only inside the same measured scope", () => {
  assert.deepEqual(deltaFromCumulative(
    { model: "m1", metric: "input_tokens", unit: "token", value: 100, sequence: 1 },
    { model: "m1", metric: "input_tokens", unit: "token", value: 145, sequence: 2 }
  ), { value: 45, status: "measured", reason: null });
});

test("missing baseline, model change, reset and out-of-order snapshots remain unknown", () => {
  assert.equal(deltaFromCumulative(null, { model: "m1", metric: "input", unit: "token", value: 3, sequence: 1 }).status, "unknown");
  assert.equal(deltaFromCumulative({ model: "m1", metric: "input", unit: "token", value: 3, sequence: 1 }, { model: "m2", metric: "input", unit: "token", value: 5, sequence: 2 }).reason, "scope_changed");
  assert.equal(deltaFromCumulative({ model: "m1", metric: "input", unit: "token", value: 10, sequence: 1 }, { model: "m1", metric: "input", unit: "token", value: 2, sequence: 2 }).reason, "counter_reset");
  assert.equal(deltaFromCumulative({ model: "m1", metric: "input", unit: "token", value: 3, sequence: 2 }, { model: "m1", metric: "input", unit: "token", value: 5, sequence: 1 }).reason, "out_of_order");
});

test("Run aggregation deduplicates identical money entries only in requested currency", () => {
  const entries = [
    { key: "request-1", runId: "run-a", status: "reconciled", amount: 0.04, currency: "USD" },
    { key: "request-2", runId: "run-b", status: "reconciled", amount: 0.02, currency: "USD" },
    { key: "request-1", runId: "run-a", status: "reconciled", amount: 0.04, currency: "USD" },
    { key: "request-3", runId: "run-b", status: "reconciled", amount: 5, currency: "CREDIT" }
  ];
  assert.equal(aggregateRunCosts(entries, ["run-a", "run-b", "run-a"], "USD"), 0.06);
});

test("a post-hook successor Run has its own additive cost while the rejected Run remains auditable", () => {
  const entries = [
    { key: "original-request", runId: "post-hook-order", status: "reconciled", amount: 0.03, currency: "USD" },
    { key: "successor-request", runId: "post-hook-reverification", status: "reconciled", amount: 0.02, currency: "USD" }
  ];
  assert.equal(aggregateRunCosts(entries, ["post-hook-order", "post-hook-reverification"], "USD"), 0.05);
  assert.equal(aggregateRunCosts(entries, ["post-hook-reverification"], "USD"), 0.02);
});

test("Qoder event normalization uses stable eventId and preserves mutable finishAt", () => {
  const first = normalizeQoderUsage({
    eventId: "evt-1", timestamp: 1000, beginAt: "2026-11-15T00:00:01Z",
    finishAt: "2026-11-15T00:00:05Z", memberId: "member-1",
    source: "CLI", operation: "Agent", modelTier: "Ultimate", credits: 12.5, cost: 10
  }, { organizationId: "org-1", runId: "run-1" });
  const update = normalizeQoderUsage({
    eventId: "evt-1", timestamp: 1000, beginAt: "2026-11-15T00:00:01Z",
    finishAt: "2026-11-15T00:00:08Z", memberId: "member-1",
    source: "CLI", operation: "Agent", modelTier: "Ultimate", credits: 12.5, cost: 10
  }, { organizationId: "org-1", runId: "run-1" });
  assert.equal(first.nativeRequestId, update.nativeRequestId);
  assert.equal(first.finishAt, "2026-11-15T00:00:05Z");
  assert.equal(update.finishAt, "2026-11-15T00:00:08Z");
  assert.equal(first.unit, "qoder_credit");
  assert.equal(first.value, 12.5);
  assert.equal(first.billingAdjustedCredits, 10);
});

test("Qoder refunds or reversals remain signed credit observations", () => {
  const refund = normalizeQoderUsage({
    eventId: "evt-refund", beginAt: "2026-11-15T00:00:01Z",
    credits: -2, cost: -2
  }, { organizationId: "org-1" });
  assert.equal(refund.value, -2);
});

test("CodeBuddy Credits remain distinct from Qoder Credits and support unattributed statements", () => {
  const usage = normalizeCodeBuddyUsage({
    credits: 30, observedAt: "2026-11-15T01:00:00Z",
    memberId: "member-2", plan: "Team", packageType: "shared-team", mode: "Agent"
  });
  assert.equal(usage.unit, "codebuddy_credit");
  assert.equal(usage.nativeRequestId, null);
  assert.equal(usage.attributionStatus, "member_period_statement");
  assert.equal(usage.runId, null);
});

test("credits cannot be converted to money without a versioned provider-specific rate", () => {
  const usage = normalizeCodeBuddyUsage({
    credits: 30, observedAt: "2026-11-15T01:00:00Z", memberId: "member-2"
  });
  assert.equal(convertCreditsToMoney(usage, null).status, "unpriced");
  const priced = convertCreditsToMoney(usage, {
    provider: "codebuddy", unit: "codebuddy_credit",
    moneyPerCredit: 0.01, currency: "USD",
    validFrom: "2026-01-01T00:00:00Z", sourceRef: "invoice:123", version: "rate-v1"
  });
  assert.equal(priced.status, "estimated");
  assert.equal(priced.amount, 0.3);
});

test("Qoder and CodeBuddy credits cannot be mixed by unit conversion", () => {
  const qoder = normalizeQoderUsage({ eventId: "q1", credits: 20 }, { organizationId: "org-1" });
  const codebuddy = normalizeCodeBuddyUsage({ credits: 20, observedAt: "2026-11-15T01:00:00Z" });
  assert.notEqual(qoder.unit, codebuddy.unit);
  assert.notEqual(qoder.provider, codebuddy.provider);
});
