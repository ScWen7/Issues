import test from 'node:test';
import assert from 'node:assert/strict';

// A design model. Inputs are synthetic normalized records after adapter parsing.
// A scope is an already-authorized workspace, provider and origin namespace.
const key = (...parts) => JSON.stringify(parts);

function bindUnits(index, scope, units, target) {
  if (!scope || !target || !units.length || units.some(unit => !unit.session || !unit.turn)) {
    return 'unresolved';
  }
  const keys = units.map(({ session, turn }) => key(scope, session, turn));
  if (keys.some(k => index.has(k) && index.get(k) !== target)) return 'conflict';
  for (const k of keys) index.set(k, target);
  return 'bound';
}

function share(selection, events, canWrite) {
  if (!canWrite(selection.issue, selection.revision)) return [];
  // Fields are positively selected locally. Attachments are shared separately.
  const names = {
    message: ['role', 'text'],
    tool: ['name', 'outcome'],
    usage: ['model', 'input', 'output'],
    artifact: ['digest', 'candidate', 'teamRef'],
  };
  const delivered = [];
  for (const event of events) {
    if (event.origin !== selection.origin || event.session !== selection.session) continue;
    const choice = selection.items.find(item => item.turn === event.turn
      && item.id === event.id && item.kind === event.kind);
    if (!choice || !names[event.kind]) continue;
    const fields = {};
    for (const name of names[event.kind]) {
      if (choice.fields.includes(name) && Object.hasOwn(event, name)) fields[name] = event[name];
    }
    if (Object.keys(fields).length === 0) continue;
    delivered.push({ turn: event.turn, id: event.id, kind: event.kind, fields });
  }
  return delivered;
}

// The adapter has verified both checkpoints share model, unit and counter epoch.
// An exclusive interval comes from a complete sequence of attributable host units.
function interval(start, end, exclusive) {
  if (!start || !end || !exclusive || start.series !== end.series
      || start.epoch !== end.epoch || end.position <= start.position
      || !Number.isSafeInteger(start.value) || !Number.isSafeInteger(end.value)
      || start.value < 0 || end.value < start.value) return null;
  return end.value - start.value;
}

// Input rows refer to a disjoint metering unit after coverage reconciliation.
// Multiple observers may certify one value. Equivalent-scope disagreements stay open.
function reconcile(rows) {
  const byUnit = new Map();
  for (const row of rows) {
    if (!row.unit || !Number.isSafeInteger(row.value) || row.value < 0) continue;
    const k = key(row.origin, row.unit, row.model, row.metric);
    if (!byUnit.has(k)) byUnit.set(k, new Set());
    byUnit.get(k).add(row.value);
  }
  let sum = 0;
  let conflicts = 0;
  for (const values of byUnit.values()) {
    if (values.size === 1) sum += values.values().next().value;
    else conflicts++;
  }
  return { sum, conflicts, distinct: byUnit.size };
}

const turn = (id, session = 'S') => ({ session, turn: id });
const usage = (value, observer, unit = 'response-1') =>
  ({ origin: 'workspace/codex/profile', unit, model: 'M', metric: 'input', value, observer });
const point = (position, value, epoch = 'boot-1', series = 'profile/M/input') =>
  ({ position, value, epoch, series });
const events = [
  { origin: 'O', session: 'S', turn: 't1', id: 'm1', kind: 'message', role: 'user', text: 'private investigation' },
  { origin: 'O', session: 'S', turn: 't2', id: 'm2', kind: 'message', role: 'assistant', text: 'C1 A2 failed' },
  { origin: 'O', session: 'S', turn: 't2', id: 'c1', kind: 'tool', name: 'verify', outcome: 'failed', output: 'private raw data' },
  { origin: 'O', session: 'S', turn: 't2', id: 'a1', kind: 'artifact', digest: 'hash-C1', candidate: 'C1', localPath: '/private/report' },
  { origin: 'O', session: 'S', turn: 't3', id: 'm2', kind: 'message', text: 'different Issue' },
];
const selection = {
  origin: 'O', session: 'S', issue: 'verification', revision: 3, items: [
    { turn: 't2', id: 'm2', kind: 'message', fields: ['text'] },
    { turn: 't2', id: 'c1', kind: 'tool', fields: ['name', 'outcome', 'output'] },
    { turn: 't2', id: 'a1', kind: 'artifact', fields: ['digest', 'candidate'] },
  ],
};

test('central dispatch, live hook and later import resolve the same native units', () => {
  const index = new Map();
  for (const units of [[turn('a'), turn('b')], [turn('b')], [turn('a')]]) {
    assert.equal(bindUnits(index, 'O', units, 'run1'), 'bound');
  }
  assert.deepEqual([...new Set(index.values())], ['run1']);
});

test('switching Issue at next native unit preserves old binding and supports several turns per Run', () => {
  const index = new Map();
  bindUnits(index, 'O', [turn('a'), turn('b')], 'run1');
  bindUnits(index, 'O', [turn('c')], 'run2');
  assert.deepEqual([...index.values()], ['run1', 'run1', 'run2']);
});

test('a partial overlap with another Run does not create a partial binding', () => {
  const index = new Map();
  bindUnits(index, 'O', [turn('b')], 'run1');
  assert.equal(bindUnits(index, 'O', [turn('a'), turn('b')], 'run2'), 'conflict');
  assert.equal(index.size, 1);
});

test('time or summary alone leaves an observation unresolved', () => {
  const index = new Map();
  assert.equal(bindUnits(index, 'O', [{ session: 'S', time: 12, text: 'done' }], 'run1'), 'unresolved');
  assert.equal(index.size, 0);
});

test('matching host IDs in distinct origins or forked sessions remain distinct', () => {
  const index = new Map();
  bindUnits(index, 'O', [turn('a')], 'run1');
  bindUnits(index, 'O2', [turn('a')], 'run2');
  bindUnits(index, 'O', [turn('new-work', 'fork')], 'run3');
  assert.equal(index.size, 3);
});

test('selection exports only requested fields, segments and origin', () => {
  const anotherOrigin = { ...events[1], origin: 'different', text: 'wrong origin' };
  assert.deepEqual(share(selection, [...events, anotherOrigin], () => true).map(r => r.fields), [
    { text: 'C1 A2 failed' }, { name: 'verify', outcome: 'failed' },
    { digest: 'hash-C1', candidate: 'C1' },
  ]);
});

test('delayed offline delivery checks the current revision and Issue authorization', () => {
  assert.deepEqual(share(selection, events, (issue, revision) => issue === 'verification' && revision === 4), []);
  assert.deepEqual(share(selection, events, issue => issue === 'other'), []);
});

test('repeated observation of a request charges once; equal-valued distinct requests both count', () => {
  assert.deepEqual(reconcile([usage(40, 'daemon'), usage(40, 'hook'), usage(40, 'import'), usage(40, 'daemon', 'response-2')]),
    { sum: 80, conflicts: 0, distinct: 2 });
});

test('a same-scope disagreement stays unresolved regardless of arrival order', () => {
  const rows = [usage(40, 'daemon'), usage(45, 'import')];
  const expected = { sum: 0, conflicts: 1, distinct: 1 };
  assert.deepEqual(reconcile(rows), expected);
  assert.deepEqual(reconcile(rows.toReversed()), expected);
});

test('reconnect charges only the attributable change; replayed checkpoints do not add usage', () => {
  const delta = interval(point(10, 120), point(12, 170), true);
  assert.equal(delta, 50);
  assert.equal(reconcile([usage(delta, 'stream'), usage(delta, 'replay')]).sum, 50);
});

test('mixed scope, missing baseline, model switch, reordering and reset keep attribution unknown', () => {
  const start = point(10, 120);
  for (const [before, after, exclusive] of [
    [null, point(12, 170), true], [start, point(12, 170), false],
    [start, point(12, 80), true], [start, point(12, 170, 'new'), true],
    [start, point(13, 170, 'boot-1', 'profile/M2/input'), true], [start, point(8, 120), true],
  ]) assert.equal(interval(before, after, exclusive), null);
  assert.equal(interval(start, point(12, 120), true), 0);
});

// A covering total is reported along with children as its breakdown.
// The adapter supplies explicit membership on the same meter and interval.
function coveredUsage(total, children) {
  if (!total) return { confirmed: null, breakdown: children, unallocated: null };
  const ids = new Set(total.includes);
  if (children.some(child => !ids.has(child.unit)) || new Set(children.map(c => c.unit)).size !== children.length) {
    return { confirmed: null, breakdown: children, unallocated: null };
  }
  const remainder = total.value - children.reduce((sum, child) => sum + child.value, 0);
  if (remainder < 0) return { confirmed: null, breakdown: children, unallocated: null };
  return { confirmed: total.value, breakdown: children, unallocated: remainder };
}

test('inclusive parent total and subagent breakdown are displayed together without double counting', () => {
  const children = [{ unit: 'child-B', value: 30 }];
  const result = coveredUsage({ value: 100, includes: ['main', 'child-B'] }, children);
  assert.deepEqual(result, { confirmed: 100, breakdown: children, unallocated: 70 });
  assert.equal(coveredUsage({ value: 100, includes: ['main'] }, children).confirmed, null);
});

test('when a tool completion belongs to an old candidate, late delivery follows the original unit', () => {
  const index = new Map();
  bindUnits(index, 'O', [turn('C1-turn')], 'C1-run');
  bindUnits(index, 'O', [turn('C2-turn')], 'C2-run');
  const currentCandidate = 'C2-run';
  const oldCompletion = index.get(key('O', 'S', 'C1-turn'));
  assert.equal(oldCompletion, 'C1-run');
  assert.notEqual(oldCompletion, currentCandidate);
});
