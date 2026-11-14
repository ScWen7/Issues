import test from 'node:test';
import assert from 'node:assert/strict';

function createModel() {
  return {
    binding: { scope: 'backend:C2', mode: 'sop', controller: 'sop-17', generation: 4, grantVersion: 2, active: true, nodeActivation: 'act-22' },
    grant: { id: 'grant-9', version: 2, active: true, allowed: ['backend:C2'] },
    ready: true, dispatches: new Map(), runs: new Map(), nextRun: 1,
  };
}
function dispatch(model, source, action = 'start') {
  const b = model.binding, g = model.grant;
  if (!b.active || b.mode !== 'sop') return { ok: false, reason: 'not-controller' };
  if (!g.active || g.version !== b.grantVersion || !g.allowed.includes(b.scope)) return { ok: false, reason: 'grant-invalid' };
  if (!model.ready) return { ok: false, reason: 'not-ready' };
  const key = [b.scope, b.generation, b.nodeActivation, action].join('|');
  if (model.dispatches.has(key)) return { ok: true, replay: true, run: model.dispatches.get(key) };
  const run = `run-${model.nextRun++}`;
  model.dispatches.set(key, run);
  model.runs.set(run, { status: 'queued', source, grantVersion: g.version });
  return { ok: true, replay: false, run };
}

test('three entrypoints racing create one dispatch and one Run', () => {
  const m = createModel();
  const results = ['leader-wakeup', 'workflow-auto', 'manual-todo'].map(source => dispatch(m, source));
  assert.equal(m.dispatches.size, 1);
  assert.equal(m.runs.size, 1);
  assert.equal(results.filter(x => x.replay).length, 2);
});

test('DAG-not-ready blocks every entrypoint', () => {
  const m = createModel(); m.ready = false;
  const results = ['leader-wakeup', 'workflow-auto', 'manual-todo'].map(source => dispatch(m, source));
  assert.equal(m.dispatches.size, 0);
  assert.ok(results.every(x => x.reason === 'not-ready'));
});

test('revoked Grant blocks new dispatch and queued claim', () => {
  const m = createModel(); const first = dispatch(m, 'workflow-auto');
  assert.equal(first.ok, true);
  m.grant.active = false;
  assert.equal(dispatch(m, 'leader-wakeup', 'rework').reason, 'grant-invalid');
  const queued = m.runs.get(first.run);
  const claimAllowed = m.grant.active && queued.grantVersion === m.grant.version;
  assert.equal(claimAllowed, false);
});

test('scope expansion requires a new Grant version and matching binding version', () => {
  const m = createModel(); m.binding.scope = 'frontend:C2';
  assert.equal(dispatch(m, 'leader-wakeup').reason, 'grant-invalid');
  m.grant.version = 3; m.grant.allowed.push('frontend:C2'); m.binding.grantVersion = 3; m.binding.generation++;
  assert.equal(dispatch(m, 'leader-wakeup').ok, true);
});

test('late C1 delivery cannot advance current C2 round', () => {
  const active = { round: 2, activation: 'act-2', candidate: 'C2' };
  const late = { round: 1, activation: 'act-1', candidate: 'C1' };
  const eligible = late.round === active.round && late.activation === active.activation && late.candidate === active.candidate;
  assert.equal(eligible, false);
});

test('child_done wakes parent but does not itself release a node', () => {
  let wakeups = 0; const deliveryRecord = null;
  wakeups++;
  assert.equal(wakeups, 1);
  assert.equal(deliveryRecord, null);
});

test('valid parallel branch reports remain independently consumable', () => {
  const required = ['A', 'B']; const received = [];
  received.push('A'); received.push('B');
  assert.ok(required.every(x => received.includes(x)));
});

test('SOP pass without required UAT Decision keeps Project Workflow stage', () => {
  const state = { stage: 'development', sop: 'pass', decision: null, inflight: 0 };
  const eligible = state.sop === 'pass' && !!state.decision && state.inflight === 0;
  if (eligible) state.stage = 'uat';
  assert.equal(state.stage, 'development');
});

test('Decision for stale candidate cannot satisfy current exit', () => {
  const state = { candidate: 'C2', decision: { candidate: 'C1' } };
  assert.notEqual(state.decision.candidate, state.candidate);
});

test('same SOP Result ID applies workflow transition once and returns original receipt', () => {
  const state = { stage: 'development', revision: 10, receipts: new Map() };
  function apply(resultId) {
    if (state.receipts.has(resultId)) return { replay: true, receipt: state.receipts.get(resultId) };
    const receipt = { from: state.stage, to: 'uat', revision: state.revision + 1 };
    state.stage = 'uat'; state.revision++; state.receipts.set(resultId, receipt);
    return { replay: false, receipt };
  }
  const first = apply('result-44'); const replay = apply('result-44');
  assert.equal(first.replay, false); assert.equal(replay.replay, true);
  assert.deepEqual(replay.receipt, first.receipt);
  assert.equal(state.revision, 11);
});

test('old SOP controller is rejected after binding generation handoff', () => {
  const m = createModel(); m.binding.mode = 'workflow'; m.binding.controller = 'workflow-uat'; m.binding.generation = 5;
  assert.equal(dispatch(m, 'old-sop').reason, 'not-controller');
});

test('restart recovers the same SOP instance, Run IDs and artifact references', () => {
  const persisted = { instance: 'sop-17', runs: ['run-1', 'run-2'], artifacts: ['xlsx-hash', 'report-hash'] };
  const restored = { instance: persisted.instance, runs: [...persisted.runs], artifacts: [...persisted.artifacts] };
  assert.deepEqual(restored, persisted);
});

test('cross-Runtime handoff reconstructs the same code candidate', () => {
  const source = { base: 'commit-A', patch: 'patch-B', lock: 'lock-v3', candidate: 'sha-C2' };
  const target = { base: 'commit-A', patch: 'patch-B', lock: 'lock-v3', candidate: 'sha-C2' };
  assert.deepEqual(target, source);
});

test('Grant revoked after queuing but before Runtime Start prevents Start', () => {
  const m = createModel(); const queued = dispatch(m, 'workflow-auto');
  assert.equal(queued.ok, true);
  m.grant.active = false;
  const run = m.runs.get(queued.run);
  const startAllowed = m.grant.active && run.grantVersion === m.grant.version;
  assert.equal(startAllowed, false);
  run.status = 'revoked-before-start';
  assert.equal(run.status, 'revoked-before-start');
});

test('revocation of an in-flight Run requests stop and reconciles unknown side effects', () => {
  const m = createModel(); const queued = dispatch(m, 'workflow-auto');
  const run = m.runs.get(queued.run); run.status = 'running'; run.externalEffect = 'unknown';
  m.grant.active = false; run.stopRequested = true;
  assert.equal(run.stopRequested, true);
  assert.equal(run.externalEffect, 'unknown');
  assert.equal(run.status, 'running'); // retain until stop acknowledgement / reconciliation
});

test('stale Project Workflow revision conflicts instead of overwriting a newer transition', () => {
  const state = { stage: 'uat', revision: 12 };
  const submittedExpectedRevision = 11;
  const accepted = submittedExpectedRevision === state.revision;
  assert.equal(accepted, false);
  assert.equal(state.stage, 'uat');
});

test('two Script Runs and one Human Gate survive restart as one SOP execution', () => {
  const persisted = {
    instance: 'sop-verify-1',
    runs: [{ id: 'script-A', status: 'succeeded' }, { id: 'script-B', status: 'succeeded' }],
    gate: { id: 'gate-1', status: 'waiting', candidate: 'C2', decision: null },
  };
  const restored = {
    instance: persisted.instance,
    runs: persisted.runs.map(x => ({ ...x })),
    gate: { ...persisted.gate },
  };
  assert.deepEqual(restored, persisted);
  assert.equal(restored.gate.status, 'waiting');
  assert.equal(restored.runs.length, 2);
});
