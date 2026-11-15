import test from "node:test";
import assert from "node:assert/strict";
import { reconcileObservations, deltaFromCumulative, aggregateRunCosts } from "./cost-ledger.mjs";

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
  const result = reconcileObservations([
    { source: "import", metric: "cost", unit: "usd", value: 0.03 }
  ]);
  assert.equal(result.unlinked.length, 1);
  assert.equal(result.entries.length, 0);
});

test("cumulative snapshots produce a delta only inside the same measured scope", () => {
  const result = deltaFromCumulative(
    { model: "m1", metric: "input_tokens", unit: "token", value: 100, sequence: 1 },
    { model: "m1", metric: "input_tokens", unit: "token", value: 145, sequence: 2 }
  );
  assert.deepEqual(result, { value: 45, status: "measured", reason: null });
});

test("missing baseline, model change, reset and out-of-order snapshots remain unknown", () => {
  assert.equal(deltaFromCumulative(null, { model: "m1", metric: "input", unit: "token", value: 3, sequence: 1 }).status, "unknown");
  assert.equal(deltaFromCumulative({ model: "m1", metric: "input", unit: "token", value: 3, sequence: 1 }, { model: "m2", metric: "input", unit: "token", value: 5, sequence: 2 }).reason, "scope_changed");
  assert.equal(deltaFromCumulative({ model: "m1", metric: "input", unit: "token", value: 10, sequence: 1 }, { model: "m1", metric: "input", unit: "token", value: 2, sequence: 2 }).reason, "counter_reset");
  assert.equal(deltaFromCumulative({ model: "m1", metric: "input", unit: "token", value: 3, sequence: 2 }, { model: "m1", metric: "input", unit: "token", value: 5, sequence: 1 }).reason, "out_of_order");
});

test("Run aggregation deduplicates identical references", () => {
  const entries = [
    { key: "request-1", runId: "run-a", status: "reconciled", amount: 0.04, currency: "USD" },
    { key: "request-2", runId: "run-b", status: "reconciled", amount: 0.02, currency: "USD" },
    { key: "request-1", runId: "run-a", status: "reconciled", amount: 0.04, currency: "USD" }
  ];
  assert.equal(aggregateRunCosts(entries, ["run-a", "run-b", "run-a"]), 0.06);
});

test("unknown, conflicting and ownership-conflicted entries do not enter money totals", () => {
  const entries = [
    { key: "ok", runId: "run-a", status: "reconciled", amount: 0.04, currency: "USD" },
    { key: "unknown", runId: "run-a", status: "unknown", amount: 99, currency: "USD" },
    { key: "review", runId: "run-a", status: "needs_review", amount: 88, currency: "USD" },
    { key: "collision", runId: "run-a", status: "reconciled", amount: 0.1, currency: "USD" },
    { key: "collision", runId: "run-b", status: "reconciled", amount: 0.1, currency: "USD" }
  ];
  assert.equal(aggregateRunCosts(entries, ["run-a", "run-b"]), 0.04);
});

test("a post-hook successor Run has its own additive cost while the rejected Run remains auditable", () => {
  const entries = [
    { key: "original-request", runId: "post-hook-order", status: "reconciled", amount: 0.03, currency: "USD" },
    { key: "successor-request", runId: "post-hook-reverification", status: "reconciled", amount: 0.02, currency: "USD" }
  ];
  assert.equal(aggregateRunCosts(entries, ["post-hook-order", "post-hook-reverification"]), 0.05);
  assert.equal(aggregateRunCosts(entries, ["post-hook-reverification"]), 0.02);
});
