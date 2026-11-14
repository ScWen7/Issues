import test from 'node:test';
import assert from 'node:assert/strict';

// This checks the proposed platform decisions. Host observations in these tests
// have already been associated with an input and an invocation by an adapter.
function assessRule(required, facts) {
  const observations = facts.filter(f => f.run === required.run && f.attempt === required.attempt
    && f.turn === required.turn && f.resource === required.resource);
  const currentInputs = observations.filter(f => f.kind === 'request' && f.position === 'effective');
  const revisions = new Set(currentInputs.map(f => f.revision));
  if (revisions.size > 1) return 'conflicting inputs';
  if (revisions.has(required.revision)) return 'current rule in request';
  if (revisions.size === 1) return 'stale rule in request';
  if (observations.some(f => f.kind === 'file' && f.revision === required.revision)) {
    return 'current rule delivered; request coverage unknown';
  }
  return 'current rule unconfirmed';
}

// The adapter supplies the authenticated Run's dispatch record. The active
// node attempt and Grant are read again when a delegated report arrives.
function reviewReport(context, submission) {
  if (!context.activeTask || !context.runtimeAuthorized || !context.issueVisible) return 'access withdrawn';
  if (submission.action === 'comment') return 'native comment received';
  if (submission.action !== 'submit-report') return 'outside delegation';

  const { grant, dispatched, current } = context;
  if (!grant?.active || !grant.actions.includes(submission.action)
      || !grant.issueIds.includes(submission.issue) || !grant.nodes.includes(submission.node)
      || !dispatched || dispatched.grantId !== grant.id || dispatched.grantVersion !== grant.version) {
    return 'outside delegation';
  }
  // Match the claimed provenance against the authenticated dispatch before
  // classifying older evidence. A mismatched claim is never archived as fact.
  for (const field of ['grantId', 'grantVersion', 'run', 'issue', 'node', 'attempt', 'candidate', 'revision']) {
    if (submission[field] !== dispatched[field]) return 'outside delegation';
  }
  if (dispatched.issue !== current.issue || dispatched.node !== current.node
      || dispatched.attempt !== current.attempt || dispatched.candidate !== current.candidate
      || dispatched.revision !== current.revision) return 'historical evidence';
  return 'report received';
}

const rule = { run: 'R', attempt: 2, turn: 'T', resource: 'export-rule', revision: 'D2' };
const observation = (kind, revision, fields = {}) => ({ ...rule, kind, revision, ...fields });
const request = (revision, position = 'effective') => observation('request', revision, { position });
const dispatched = {
  grantId: 'G', grantVersion: 3, run: 'R2', issue: 'verify', node: 'verify-export',
  attempt: 2, candidate: 'C2', revision: 'D2',
};
const base = {
  activeTask: true, runtimeAuthorized: true, issueVisible: true, dispatched,
  grant: { id: 'G', version: 3, active: true, issueIds: ['verify'], nodes: ['verify-export'], actions: ['submit-report'] },
  current: { issue: 'verify', node: 'verify-export', attempt: 2, candidate: 'C2', revision: 'D2' },
};
const report = { action: 'submit-report', ...dispatched, paymentTimeCheck: 'fail' };
const peerComment = { action: 'comment', issue: 'visible-peer', text: 'See verification Issue.' };

test('a written D2 and earlier version probe support delivery only', () => {
  assert.equal(assessRule(rule, [observation('file', 'D2'), observation('prior-version-probe', 'D2')]),
    'current rule delivered; request coverage unknown');
});
test('an old active input remains stale after rewriting the file', () => {
  assert.equal(assessRule(rule, [request('D1'), observation('file', 'D2')]), 'stale rule in request');
});
test('fresh D2 in this input can coexist with historical D1', () => {
  assert.equal(assessRule(rule, [request('D1', 'history'), request('D2')]), 'current rule in request');
});
test('history, a path-only hook and an earlier attempt do not establish current D2', () => {
  assert.equal(assessRule(rule, [request('D2', 'history'), observation('loaded-path', null),
    { ...request('D2'), attempt: 1 }]), 'current rule unconfirmed');
});
test('conflicting active instructions remain unresolved', () => {
  assert.equal(assessRule(rule, [request('D1'), request('D2')]), 'conflicting inputs');
});
test('native comments use Issue access and delegated reports require an active Grant', () => {
  const withoutGrant = { ...base, grant: null };
  assert.equal(reviewReport(withoutGrant, peerComment), 'native comment received');
  assert.equal(reviewReport(base, peerComment), 'native comment received');
  assert.equal(reviewReport(withoutGrant, report), 'outside delegation');
  assert.equal(reviewReport(base, { ...report, issue: peerComment.issue }), 'outside delegation');
  assert.equal(reviewReport({ ...base, grant: { ...base.grant, actions: [] } }, report), 'outside delegation');
});
test('delivery rechecks native access, delegation generation and dispatched provenance', () => {
  for (const field of ['activeTask', 'runtimeAuthorized', 'issueVisible']) {
    assert.equal(reviewReport({ ...base, [field]: false }, report), 'access withdrawn', field);
    assert.equal(reviewReport({ ...base, [field]: false }, peerComment), 'access withdrawn', field);
  }
  for (const changes of [{ active: false }, { id: 'other-grant' }, { version: 4 }, { issueIds: [] }, { nodes: [] }]) {
    assert.equal(reviewReport({ ...base, grant: { ...base.grant, ...changes } }, report), 'outside delegation');
  }
  assert.equal(reviewReport({ ...base, dispatched: null }, report), 'outside delegation');
  for (const [field, value] of Object.entries({
    grantId: 'other-grant', grantVersion: 2, run: 'R-other', issue: 'visible-peer', node: 'other-node',
    attempt: 1, candidate: 'C1', revision: 'D1',
  })) {
    assert.equal(reviewReport(base, { ...report, [field]: value }), 'outside delegation', field);
  }
});
test('a genuine late report goes to history and the current receipt retains its failed field check', () => {
  const priorDispatch = { ...dispatched, run: 'R1', attempt: 1, candidate: 'C1', revision: 'D1' };
  const late = { ...report, ...priorDispatch };
  assert.equal(reviewReport({ ...base, dispatched: priorDispatch }, late), 'historical evidence');
  assert.equal(reviewReport({ ...base, dispatched: priorDispatch }, report), 'outside delegation');
  assert.equal(reviewReport({ ...base, current: { ...base.current, attempt: 3 } }, report), 'historical evidence');
  assert.equal(reviewReport(base, report), 'report received');
  assert.equal(report.paymentTimeCheck, 'fail');
});
