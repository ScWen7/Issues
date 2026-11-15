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
});

test("same native ID in different namespaces is not merged", () => {
  const result = reconcileObservations([
    { source: "a", sourceNamespace: "profile-A", nativeRequestId: "req-1", metric: "input_tokens", unit: "token", value: 10 },
    { source: "b", sourceNamespace: "profile-B", nativeRequestId: "req-1", metric: "input_tokens", unit: "token", value: 10 }
  ]);
  assert.equal(result.entries.length, 2);
});

test("conflicting observations remain unresolved rather than selecting arrival winner", () => {
  const result = reconcileObservations([
    { source: "daemon", sourceNamespace: "codex:A", nativeRequestId: "req-2", metric: "output_tokens", unit: "token", value: 30, trustRank: 2 },
    { source: "otel", sourceNamespace: "codex:A", nativeRequestId: "req-2", metric: "output_tokens", unit: "token", value: 31, trustRank: 2 }
  ]);
  assert.equal(result.entries[0].status, "needs_review");
  assert.equal(result.entries[0].value, null);
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

test("Run aggregation deduplicates reused entries across parent and child references", () => {
  const entries = [
    { key: "request-1", runId: "run-a", status: "reconciled", amount: 0.04 },
    { key: "request-2", runId: "run-b", status: "reconciled", amount: 0.02 },
    { key: "request-1", runId: "run-a", status: "reconciled", amount: 0.04 }
  ];
  assert.equal(aggregateRunCosts(entries, ["run-a", "run-b", "run-a"]), 0.06);
});

test("unknown and conflicting entries do not silently enter money totals", () => {
  const entries = [
    { key: "ok", runId: "run-a", status: "reconciled", amount: 0.04 },
    { key: "unknown", runId: "run-a", status: "unknown", amount: 99 },
    { key: "review", runId: "run-a", status: "needs_review", amount: 88 }
  ];
  assert.equal(aggregateRunCosts(entries, ["run-a"]), 0.04);
});
