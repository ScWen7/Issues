import test from "node:test";
import assert from "node:assert/strict";
import {
  reconcileObservations, deltaFromCumulative, aggregateRunCosts,
  normalizeRuntimeCreditObservation, creditsUnavailable,
  normalizeQoderSdkMessage, normalizeCodeBuddyUsageUpdate, reconcileCodeBuddyTurn
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

test("Qoder runtime-reported Credits retain native unit and Run binding", () => {
  const usage = normalizeRuntimeCreditObservation({
    provider: "qoder", credits: 12.5, observedAt: "2026-11-15T00:00:05Z",
    eventId: "runtime-event-1", memberId: "member-1", runId: "run-1",
    modelTier: "Ultimate", operation: "Agent", sessionId: "session-1", turnId: "turn-1"
  });
  assert.equal(usage.unit, "qoder_credit");
  assert.equal(usage.value, 12.5);
  assert.equal(usage.runId, "run-1");
  assert.equal(usage.source, "runtime");
});

test("CodeBuddy runtime-reported Credits remain separate from Qoder Credits", () => {
  const usage = normalizeRuntimeCreditObservation({
    provider: "codebuddy", credits: 30, observedAt: "2026-11-15T01:00:00Z",
    memberId: "member-2", runId: "run-2", sessionId: "session-2"
  });
  assert.equal(usage.unit, "codebuddy_credit");
  assert.equal(usage.value, 30);
  assert.equal(usage.runId, "run-2");
});

test("Credits remain unknown when runtime does not report them", () => {
  const qoder = creditsUnavailable("qoder", "run-q");
  const codebuddy = normalizeRuntimeCreditObservation({
    provider: "codebuddy", observedAt: "2026-11-15T01:00:00Z", runId: "run-c"
  });
  assert.equal(qoder.status, "unknown");
  assert.equal(qoder.value, null);
  assert.equal(qoder.unknownReason, "runtime_usage_unavailable");
  assert.equal(codebuddy.status, "unknown");
  assert.equal(codebuddy.value, null);
  assert.equal(codebuddy.unknownReason, "runtime_did_not_report_credits");
});

test("Credits are not converted to money or inferred from subscription quota", () => {
  const usage = normalizeRuntimeCreditObservation({
    provider: "qoder", credits: 20, observedAt: "2026-11-15T01:00:00Z"
  });
  assert.equal(usage.currency, null);
  assert.equal(usage.unit, "qoder_credit");
  assert.equal(usage.amount, undefined);
});

test("Qoder and CodeBuddy Credits cannot be mixed", () => {
  const qoder = normalizeRuntimeCreditObservation({ provider: "qoder", credits: 20, observedAt: "2026-11-15T01:00:00Z" });
  const codebuddy = normalizeRuntimeCreditObservation({ provider: "codebuddy", credits: 20, observedAt: "2026-11-15T01:00:00Z" });
  assert.notEqual(qoder.unit, codebuddy.unit);
  assert.notEqual(qoder.provider, codebuddy.provider);
});

test("Qoder SDK request-level Credits are taken from Assistant message usage", () => {
  const event = normalizeQoderSdkMessage({
    type: "assistant", uuid: "assistant-req-1", session_id: "q-session",
    message: { model: "qoder-model", usage: { credits: 4.25, original_credits: 5, billable: true } }
  }, { runId: "run-q", memberId: "member-1" });
  assert.equal(event.value, 4.25);
  assert.equal(event.originalCredits, 5);
  assert.equal(event.billable, true);
  assert.equal(event.unit, "qoder_credit");
  assert.equal(event.runId, "run-q");
  assert.equal(event.scope, "model_request");
});

test("Qoder SDK missing request Credits remain unknown and are not zero", () => {
  const event = normalizeQoderSdkMessage({
    type: "assistant", uuid: "assistant-no-credits",
    message: { usage: { input_tokens: 120 } }
  });
  assert.equal(event.status, "unknown");
  assert.equal(event.value, null);
});

test("Qoder SDK Result total is a session snapshot, not an additive request", () => {
  const event = normalizeQoderSdkMessage({
    type: "result", uuid: "result-1", session_id: "q-session",
    total_credits: 9.5, modelUsage: { "q-model": { credits: 9.5 } }
  }, { runId: "run-q" });
  assert.equal(event.metric, "session_total_credits");
  assert.equal(event.scope, "session_snapshot");
  assert.equal(event.value, 9.5);
});

test("CodeBuddy usage_update stage events are keyed by session, request and stage", () => {
  const event = normalizeCodeBuddyUsageUpdate({
    type: "system", subtype: "usage_update", uuid: "frame-1",
    session_id: "cb-session", _requestId: "request-1",
    _meta: { "codebuddy.ai/turnUsage": {
      version: 1, scope: "turn", kind: "stage", requestId: "request-1",
      stage: { id: "model:message-1", source: "model", messageId: "message-1", model: "model-x", credits: 2.5 }
    } }
  }, { runId: "run-cb" });
  assert.equal(event.nativeRequestId, "model:message-1");
  assert.equal(event.value, 2.5);
  assert.equal(event.unit, "codebuddy_credit");
  assert.equal(event.runId, "run-cb");
});

test("CodeBuddy same stage corrections overwrite instead of double-counting", () => {
  const mk = (credits, frame) => normalizeCodeBuddyUsageUpdate({
    type: "system", subtype: "usage_update", uuid: frame, session_id: "s", _requestId: "r",
    _meta: { "codebuddy.ai/turnUsage": {
      version: 1, scope: "turn", kind: "stage", requestId: "r",
      stage: { id: "model:m1", source: "model", credits }
    } }
  });
  const result = reconcileCodeBuddyTurn([mk(2.5, "f1"), mk(3, "f2")]);
  assert.equal(result.stages.length, 1);
  assert.equal(result.totalCredits, 3);
  assert.equal(result.totalSource, "stage_sum_provisional");
});

test("CodeBuddy terminal snapshot replaces stage accumulation and is not added twice", () => {
  const stage = normalizeCodeBuddyUsageUpdate({
    type: "system", subtype: "usage_update", session_id: "s", _requestId: "r",
    _meta: { "codebuddy.ai/turnUsage": {
      version: 1, scope: "turn", kind: "stage", requestId: "r",
      stage: { id: "model:m1", source: "model", credits: 2.5 }
    } }
  });
  const snapshot = normalizeCodeBuddyUsageUpdate({
    type: "system", subtype: "usage_update", session_id: "s", _requestId: "r",
    _meta: { "codebuddy.ai/turnUsage": {
      version: 1, scope: "turn", kind: "snapshot", requestId: "r",
      total: { credits: 2.5, creditStatus: "known" },
      stages: [{ id: "model:m1", source: "model", credits: 2.5 }]
    } }
  });
  const result = reconcileCodeBuddyTurn([stage, snapshot]);
  assert.equal(result.totalCredits, 2.5);
  assert.equal(result.totalSource, "terminal_snapshot");
});

test("CodeBuddy stage without Credits remains unknown even when tokens exist", () => {
  const event = normalizeCodeBuddyUsageUpdate({
    type: "system", subtype: "usage_update", session_id: "s", _requestId: "r",
    _meta: { "codebuddy.ai/turnUsage": {
      version: 1, scope: "turn", kind: "stage", requestId: "r",
      stage: { id: "model:m1", usage: { input_tokens: 100 }, source: "model" }
    } }
  });
  assert.equal(event.status, "unknown");
  assert.equal(event.value, null);
  assert.equal(reconcileCodeBuddyTurn([event]).status, "unknown");
});

test("CodeBuddy different requests in the same session remain separate turns", () => {
  const make = (requestId, stageId, credits) => normalizeCodeBuddyUsageUpdate({
    type: "system", subtype: "usage_update", session_id: "s", _requestId: requestId,
    _meta: { "codebuddy.ai/turnUsage": {
      version: 1, scope: "turn", kind: "stage", requestId,
      stage: { id: stageId, credits, source: "model" }
    } }
  });
  const first = reconcileCodeBuddyTurn([make("r1", "m1", 2)]);
  const second = reconcileCodeBuddyTurn([make("r2", "m2", 3)]);
  assert.equal(first.totalCredits, 2);
  assert.equal(second.totalCredits, 3);
});
