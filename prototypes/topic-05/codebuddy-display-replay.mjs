// Run with Node 24.22.x and a checkout of Multica fdfbfcd5.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { registerHooks } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { reconcileCodeBuddyTurn } from "../topic-04/cost-ledger.mjs";

const checkout = process.argv[2];
if (!checkout) {
  throw new Error("Usage: node codebuddy-display-replay.mjs /path/to/multica");
}

function verifiedSource(path, expectedHash) {
  const file = readFileSync(path);
  assert.equal(createHash("sha256").update(file).digest("hex"), expectedHash, String(path));
  return file.toString("utf8");
}

function upstream(path, hash) {
  const absolute = resolve(checkout, path);
  verifiedSource(absolute, hash);
  return pathToFileURL(absolute).href;
}

const utilsURL = upstream("packages/views/runtimes/utils.ts", "caf669a15470c140124545f3b1bbdf1d405fa7a391c8606fa52901362650f421");
const timelineURL = upstream("packages/views/issues/components/issue-run-timeline.ts", "e01e8820d5ddd252697872e5fd3d2bd86465ab9096e621f11afc63e4dff2f303");
const labelsURL = upstream("packages/views/issues/components/task-run-labels.ts", "c8198533fc7fc5cd318655f8dd3f8d86046e2ac6149629d76191aab113bcca06");

// No browser state or custom prices. UI-only label helpers fail if accidentally called.
const emptyPrices = "data:text/javascript,export const getCustomPricing = () => undefined";
const unusedLabel = "data:text/javascript," + encodeURIComponent(
  "const unused = () => { throw new Error('UI-only dependency called') }; " +
  "export { unused as useT, unused as providerDisplayName, unused as stripMentionMarkdown };"
);
const imports = new Map([
  ["@multica/core/runtimes/custom-pricing-store", emptyPrices],
  ["../../runtimes/utils", utilsURL],
  ["./task-run-labels", labelsURL],
  ["../../i18n", unusedLabel],
  ["@multica/core/runtimes", unusedLabel],
  ["../utils/strip-mention-markdown", unusedLabel],
]);
const hooks = registerHooks({
  resolve(specifier, context, nextResolve) {
    const url = imports.get(specifier);
    return url ? { url, shortCircuit: true } : nextResolve(specifier, context);
  },
});
const { summarizeTaskUsage, summarizeTaskUsageAcross, formatSpend } = await import(utilsURL);
const { buildRunTimeline } = await import(timelineURL);
hooks.deregister();

const receiptURL = new URL("../../artifacts/topic-04/mac-20261115-0350/codebuddy-receipt.jsonl", import.meta.url);
const receipt = verifiedSource(receiptURL, "3fb235e4f8756d7a0c18bfc403df6694ece17c9ab2b70c2e0902b506da6a6613");
const records = receipt.trim().split("\n").map(line => JSON.parse(line));
assert.deepEqual(records.map(r => r.scope), ["turn_stage", "turn_snapshot", "result_snapshot"]);
assert.ok(records[0].run_id && records[0].session_id && records[0].request_id && records[0].stage_id);
for (const record of records) {
  assert.equal(record.run_id, records[0].run_id);
  assert.equal(record.session_id, records[0].session_id);
  assert.equal(record.request_id, records[0].request_id);
  assert.equal(record.unit, "codebuddy_credit");
  assert.equal(record.provider, "codebuddy");
  assert.equal(record.credit_status, "known");
  assert.equal(record.value, 0.69);
}
// The archived JSONL is the probe's allow-listed projection, not raw stream-json.
// Reconciliation takes one Run/Session/Turn and retains only the current Stage.
const events = records.map(r => ({
  provider: r.provider, unit: r.unit, value: r.value, status: "observed",
  kind: r.scope === "turn_stage" ? "stage" : "snapshot",
  nativeRequestId: r.stage_id ?? r.request_id, model: r.model,
}));
function usageSlice(provider, model, fields) {
  return { provider, model, input_tokens: 0, output_tokens: 0,
    cache_read_tokens: 0, cache_write_tokens: 0, ...fields };
}

const realRunId = records[0].run_id;
let replayRows;
for (const copies of [1, 3]) {
  const turn = reconcileCodeBuddyTurn(Array.from({ length: copies }, () => events).flat());
  assert.equal(turn.stages.length, 1);
  assert.equal(turn.stages[0].nativeRequestId, records[0].stage_id);
  assert.equal(turn.stages[0].value, turn.totalCredits);
  const micros = Math.round(turn.totalCredits * 1e6);
  assert.equal(micros, 690000);
  replayRows = [usageSlice("codebuddy", turn.stages[0].model, { credits_micros: micros })];
}

const display = summary => summary === null ? null :
  formatSpend(summary, (value, provider) => `${provider} ${value} Credits`);
const realRun = summarizeTaskUsage(replayRows);
assert.equal(display(realRun), "codebuddy 0.69 Credits");
assert.equal(display(summarizeTaskUsageAcross([replayRows])), display(realRun));

const other = [usageSlice("qoder_cloud", "fixture-only", { credits_micros: 2000000 })];
const mixed = summarizeTaskUsageAcross([replayRows, other]);
assert.deepEqual([...mixed.credits], [["codebuddy", 0.69], ["qoder_cloud", 2]]);

const zeroRows = [usageSlice("codebuddy", "fixture-only", { credits_micros: 0 })];
const tokenRows = [usageSlice("codebuddy", "fixture-unpriced-model", { input_tokens: 24 })];
const zero = summarizeTaskUsage(zeroRows);
const tokens = summarizeTaskUsage(tokenRows);
assert.equal(display(zero), "codebuddy 0 Credits");
assert.equal(tokens.tokens, 24);
assert.equal(tokens.credits.size, 0);
assert.equal(display(tokens), "$0.00");
assert.equal(summarizeTaskUsage([]), null);
assert.equal(summarizeTaskUsageAcross([undefined, []]), null);

function asTask(id, usage) {
  return {
    id, agent_id: "fixture-agent", status: "completed", usage,
    created_at: "2026-11-15T03:52:00Z", started_at: "2026-11-15T03:52:00Z",
    completed_at: "2026-11-15T03:52:34Z",
  };
}

const now = Date.parse("2026-11-15T03:53:00Z");
const timeline = buildRunTimeline([asTask(realRunId, replayRows), asTask("other", other)], now);
assert.deepEqual([...timeline.totalCredits], [...mixed.credits]);

const controls = [asTask("zero", zeroRows), asTask("token", tokenRows), asTask("missing", undefined)];
const coverage = buildRunTimeline(controls, now);
const knownCredits = coverage.runs.filter(r => r.usage?.credits.has("codebuddy")).length;
assert.equal(coverage.pricedCount, 2);
assert.equal(knownCredits, 1);
assert.equal(coverage.runs.length, 3);
assert.equal(display(summarizeTaskUsageAcross(controls.map(t => t.usage))), display(zero));

console.log(JSON.stringify({
  receiptFrames: records.length, replayCopies: 3, stageCount: 1,
  creditsMicros: replayRows[0].credits_micros, run: display(realRun),
  mixedIssue: display(mixed), timelineCredits: Object.fromEntries(timeline.totalCredits),
  explicitZero: display(zero), tokenOnly: { tokens: tokens.tokens, spendLabel: display(tokens) },
  missingRunSummary: summarizeTaskUsage(undefined),
  coverage: { eligibleRuns: coverage.runs.length, timelinePricedCount: coverage.pricedCount, runsWithCodeBuddyCredits: knownCredits },
}, null, 2));
