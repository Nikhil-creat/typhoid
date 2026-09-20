import test from 'node:test';
import assert from 'node:assert/strict';
import { Swarm, mayAutopilot, chaosHolds, countDiffLines, touchesProtected, MAX_INTENSITY } from '../js/sim.js';

const fast = () => { const s = new Swarm(); s.speed = 1e6; return s; };
const cfg = (o = {}) => ({ story: 'checkout', faults: ['latency'], intensity: 0.2, autonomy: 'review', seedBug: true, ...o });

test('review mode ends awaiting human, then approve merges', async () => {
  const s = fast(); await s.run(cfg());
  assert.equal(s.state.status, 'awaiting_review');
  assert.ok(s.state.patch.verified);
  assert.ok(s.decide('approved'));
  assert.equal(s.state.status, 'merged');
});
test('autopilot merges only when all gates pass', async () => {
  const s = fast(); await s.run(cfg({ autonomy: 'autopilot' }));
  assert.equal(s.state.status, 'merged');
});
test('observe mode opens no PR', async () => {
  const s = fast(); await s.run(cfg({ autonomy: 'observe' }));
  assert.equal(s.state.status, 'reported'); assert.equal(s.state.prUrl, null);
});
test('clean app takes the green path and learns', async () => {
  const s = fast(); await s.run(cfg({ seedBug: false, faults: [] }));
  assert.equal(s.state.status, 'passed'); assert.ok(s.state.kg > 0);
});
test('chaos intensity is clamped and announced', async () => {
  const s = fast(); const seen = [];
  s.on((e) => seen.push(e)); await s.run(cfg({ intensity: 0.9 }));
  assert.ok(seen.some((e) => e.kind === 'guardrail' && /clamped/.test(e.text)));
  assert.ok(MAX_INTENSITY <= 0.3);
});
test('kill-switch halts the run', async () => {
  const s = new Swarm(); s.speed = 50;
  const p = s.run(cfg()); setTimeout(() => s.kill(), 30); await p;
  assert.equal(s.state.status, 'killed'); assert.equal(s.running, false);
});
test('unverified or protected patches never autopilot', () => {
  const ok = { diff: '--- a/x\n+++ b/x\n+1', confidence: 0.99, verified: true };
  assert.equal(mayAutopilot(ok, 'autopilot')[0], true);
  assert.equal(mayAutopilot({ ...ok, verified: false }, 'autopilot')[0], false);
  assert.equal(mayAutopilot({ ...ok, confidence: 0.5 }, 'autopilot')[0], false);
  assert.equal(mayAutopilot({ ...ok, diff: '--- a/.github/workflows/ci.yml\n+++ b/.github/workflows/ci.yml\n+1' }, 'autopilot')[0], false);
});
test('unverified patches cannot be approved', () => {
  const s = new Swarm(); s.state.status = 'awaiting_review'; s.state.patch = { verified: false };
  assert.equal(s.decide('approved'), false);
});
test('helpers', () => {
  assert.equal(chaosHolds('db_outage', 0.05), false);
  assert.equal(countDiffLines('+++ b\n+a\n-b'), 2);
  assert.equal(touchesProtected('--- a/infra/x'), true);
});
