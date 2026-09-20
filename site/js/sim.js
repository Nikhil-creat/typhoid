// Pure simulation engine (no DOM, no three.js) so it can be unit-tested in Node.
// It mirrors the real LangGraph swarm in /agents: same nodes, same guardrail rules.

export const AGENTS = [
  { id: 'risk_oracle', label: 'Risk oracle' },
  { id: 'architect', label: 'Architect' },
  { id: 'synthetic_data', label: 'Synthetic data' },
  { id: 'execution', label: 'Execution' },
  { id: 'chaos', label: 'Chaos' },
  { id: 'vision', label: 'Vision' },
  { id: 'remediation', label: 'Remediation' },
  { id: 'verifier', label: 'Verifier' },
  { id: 'ship', label: 'Ship' },
];

export const MAX_INTENSITY = 0.3;          // CHAOS_MAX_BLAST_RADIUS
export const AUTOPILOT_MIN_CONFIDENCE = 0.92;
export const AUTOPILOT_MAX_DIFF_LINES = 60;
export const BUDGET_USD = 500;
const PROTECTED = ['.github/workflows/', 'infra/', 'Dockerfile', '.env', 'secrets', 'deploy'];
const INJECTION = /ignore (all|previous) instructions|system prompt|exfiltrate|curl .*\|\s*sh/i;

const DIFF_V1 = `--- a/src/checkout/payment.py
+++ b/src/checkout/payment.py
@@ -41,4 +41,5 @@ def charge(card, amount):
-    exp = card["expiry"].split("/")
-    return gateway.charge(card["number"], exp, amount)
+    if is_expired(card["expiry"]):
+        raise CardDeclined("Card expired", code="expired_card")
+    return gateway.charge(card["number"], card["expiry"], amount)`;

const DIFF_V2 = `--- a/src/checkout/payment.py
+++ b/src/checkout/payment.py
@@ -41,4 +41,5 @@ def charge(card, amount):
-    exp = card["expiry"].split("/")
-    return gateway.charge(card["number"], exp, amount)
+    if is_expired(card["expiry"]):
+        raise CardDeclined("Card expired", code="expired_card")
+    return gateway.charge(card["number"], card["expiry"], amount, timeout=4, retries=2)
--- a/src/checkout/views.py
+++ b/src/checkout/views.py
@@ -18,3 +18,5 @@ def pay(request):
-    receipt = charge(card, total)
+    try:
+        receipt = charge(card, total)
+    except CardDeclined as e:
+        return error_response(e.code, "Your card has expired. Try another card.")
+++ b/tests/test_expired_card.py
+def test_expired_card_shows_clear_error(client):
+    assert client.pay(expired_card()).error == "expired_card"`;

export function countDiffLines(diff) {
  return diff.split('\n').filter((l) => /^[+-]/.test(l) && !l.startsWith('+++') && !l.startsWith('---')).length;
}
export function touchesProtected(diff) {
  return diff.split('\n').some((l) => (l.startsWith('+++') || l.startsWith('---')) && PROTECTED.some((p) => l.includes(p)));
}
export function mayAutopilot(patch, autonomy) {
  if (autonomy !== 'autopilot') return [false, 'autonomy level is not autopilot'];
  if (!patch.verified) return [false, 'patch not verified in sandbox'];
  if (patch.confidence < AUTOPILOT_MIN_CONFIDENCE) return [false, 'confidence below threshold'];
  if (countDiffLines(patch.diff) > AUTOPILOT_MAX_DIFF_LINES) return [false, 'diff too large'];
  if (touchesProtected(patch.diff)) return [false, 'touches protected paths'];
  return [true, 'all gates passed'];
}
export function chaosHolds(fault, k) {
  if (fault === 'db_outage') return false;
  if (fault === 'dns_failure') return k < 0.1;
  if (fault === 'latency') return k < 0.25;
  if (fault === 'packet_loss') return k < 0.2;
  if (fault === 'cpu_throttle') return k < 0.3;
  return true;
}

class Kill extends Error {}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export class Swarm {
  constructor() { this.listeners = []; this.speed = 1; this.paused = false; this.killed = false; this.running = false; this.state = this.fresh(); }
  fresh() { return { status: 'idle', risk: 0, cost: 0, kg: 0, tests: 0, passed: 0, failed: 0, attempt: 0, patch: null, decision: null, autonomy: 'review', prUrl: null }; }
  on(fn) { this.listeners.push(fn); return () => (this.listeners = this.listeners.filter((f) => f !== fn)); }
  emit(agent, kind, text, extra = {}) {
    const ev = { agent, kind, text, ts: Date.now(), ...extra };
    for (const f of this.listeners) f(ev, this.state);
    return ev;
  }
  charge(usd) { this.state.cost = +(this.state.cost + usd).toFixed(4); }
  kill() { this.killed = true; }
  togglePause() { this.paused = !this.paused; return this.paused; }
  async wait(ms) {
    let left = ms;
    while (left > 0) {
      if (this.killed) throw new Kill();
      if (this.paused) { await sleep(60); continue; }
      const t = Math.min(40, left * 1); await sleep(t / this.speed); left -= t;
    }
    if (this.killed) throw new Kill();
  }

  decide(decision) {                       // human approves / rejects in Patch review
    const s = this.state;
    if (!s.patch || s.decision || s.status !== 'awaiting_review') return false;
    if (decision === 'approved' && !s.patch.verified) return false;   // server refuses unverified approvals too
    s.decision = decision;
    s.status = decision === 'approved' ? 'merged' : 'rejected';
    this.emit('ship', decision === 'approved' ? 'patch' : 'error',
      decision === 'approved' ? 'Reviewer approved. PR merged; pipeline goes green.' : 'Reviewer rejected the patch. Bug stays open and is logged to memory.',
      { node: decision === 'approved' ? 'done' : 'fail', patchState: decision });
    return true;
  }

  async run(cfg) {
    if (this.running) return;
    this.running = true; this.killed = false; this.paused = false;
    const s = this.state = this.fresh();
    s.status = 'running'; s.autonomy = cfg.autonomy;
    const faults = cfg.faults ?? [];
    const k = Math.min(cfg.intensity ?? 0.2, MAX_INTENSITY);
    try {
      this.emit('ship', 'status', 'Run started. Sandboxes are provisioned on demand.', { node: 'idle', reset: true });
      if ((cfg.intensity ?? 0) > MAX_INTENSITY)
        this.emit('chaos', 'guardrail', `Requested intensity ${Math.round(cfg.intensity * 100)}% clamped to ${MAX_INTENSITY * 100}% by policy.`);

      // 1 ── risk oracle
      this.emit('risk_oracle', 'status', 'Reading the knowledge graph for hotspots around this change…', { node: 'active', rag: true });
      await this.wait(900);
      s.risk = 0.71; this.charge(0.004);
      this.emit('risk_oracle', 'result', 'Risk 71%. checkout/payment.py had 3 bugs in 30 days; 2 flaky tests nearby. Going exhaustive.', { node: 'done', risk: s.risk });

      // 2 ── architect (with prompt-injection isolation)
      this.emit('architect', 'status', 'Compiling the story into a dependency-ordered test tree…', { node: 'active', rag: true });
      await this.wait(1000);
      if (INJECTION.test(cfg.story ?? '')) this.emit('architect', 'guardrail', 'Story text looks like a prompt injection. Treated as untrusted data, not instructions.');
      s.tests = 7; this.charge(0.031);
      this.emit('architect', 'result', 'Plan ready: 7 tests (4 e2e, 1 api, 1 visual, 1 a11y) plus exploratory crawl.', { node: 'done' });

      // 3 ── synthetic data
      this.emit('synthetic_data', 'status', 'Generating GDPR-safe personas and edge-case seeds…', { node: 'active' });
      await this.wait(800); this.charge(0.006);
      this.emit('synthetic_data', 'result', '12 fictional personas (unicode names, expired cards, 0 and negative amounts). PII scan: clean.', { node: 'done' });

      // 4 ── execution
      this.emit('execution', 'status', 'Spinning up 6 ephemeral sandboxes (read-only rootfs, no capabilities, 15 min TTL)…', { node: 'active', workers: 'up' });
      await this.wait(1300);
      const bug = cfg.seedBug !== false;
      s.passed = bug ? 6 : 7; s.failed = bug ? 1 : 0;
      this.emit('execution', bug ? 'error' : 'result', bug ? '6 passed, 1 failed: checkout:expired-card returned HTTP 500.' : '7 passed, 0 failed.',
        { node: bug ? 'fail' : 'done', workers: bug ? 'fail' : 'up' });

      // 5 ── vision
      this.emit('vision', 'status', 'CNN heatmap and VLM verdict on desktop and mobile…', { node: 'active' });
      await this.wait(1000); this.charge(0.022);
      this.emit('vision', 'visual', bug ? 'Mobile 390px: the Pay button is clipped by the sticky footer (regression, medium).' : 'No visual regressions on 1440px or 390px.',
        { node: bug ? 'fail' : 'done', regions: bug ? [[6, 11], [7, 11], [8, 11]] : [] });
      if (cfg.mockup) this.emit('vision', 'result', `Mockup "${cfg.mockup}" conformance 91%. Two spacing deviations noted.`);

      // 6 ── chaos
      let chaosBroke = 0;
      if (faults.length) {
        this.emit('chaos', 'status', `Hypothesis: "p95 < 800ms and checkout succeeds". Injecting ${faults.length} fault(s) mid-test at ${Math.round(k * 100)}%…`, { node: 'active', workers: 'chaos' });
        for (const f of faults) {
          await this.wait(1100);
          const held = chaosHolds(f, k);
          const p95 = Math.round(300 + k * 2400 * (held ? 0.4 : 1.6));
          if (!held) chaosBroke++;
          this.emit('chaos', 'chaos', `${f.replace('_', ' ')}: ${held ? 'steady state held' : 'steady state violated'} (p95 ${p95}ms). Fault healed.`, { node: held ? 'active' : 'fail', workers: held ? 'chaos' : 'fail' });
        }
        this.emit('chaos', chaosBroke ? 'error' : 'result', chaosBroke ? `${chaosBroke} hypothesis broken.` : 'All hypotheses held.', { node: chaosBroke ? 'fail' : 'done' });
      }

      const failures = (bug ? 1 : 0) + chaosBroke;
      s.failed += chaosBroke;

      if (!failures) {
        this.emit('ship', 'status', 'Everything green. Logging the clean run to memory.', { node: 'active', rag: true, workers: 'destroyed' });
        await this.wait(700); s.kg += 3; s.status = 'passed';
        this.emit('ship', 'result', 'Run passed. Sandboxes destroyed, secrets shredded.', { node: 'done' });
        return;
      }

      // 7 ── diagnose + reflexion loop
      this.emit('remediation', 'status', 'Root-cause analysis with similar past bugs from Qdrant and Neo4j…', { node: 'active', rag: true, workers: 'destroyed' });
      await this.wait(1200); this.charge(0.058);
      const cause = chaosBroke && !bug ? 'The payment gateway call has no timeout or retry.' : 'Expired cards crash payment.py (unhandled split on expiry); no timeout on the gateway call.';
      this.emit('remediation', 'thought', `Product bug, 94% sure. ${cause}`, { node: 'active' });

      s.attempt = 1;
      let patch = { title: 'Handle expired cards in checkout', diff: DIFF_V1, confidence: 0.81, verified: false };
      s.patch = patch;
      this.emit('remediation', 'patch', 'Draft patch 1 (81% confident, 5 changed lines).', { node: 'active', patchState: 'draft' });
      await this.wait(1200); this.charge(0.047);
      this.emit('verifier', 'status', 'Applying patch in a fresh sandbox and re-running the failing tests…', { node: 'active', workers: 'up' });
      await this.wait(1400);
      this.emit('verifier', 'error', 'Attempt 1 failed: the view still surfaces a 500 when the gateway times out.', { node: 'fail', patchState: 'unverified', workers: 'fail' });

      s.attempt = 2;
      patch = { title: 'Handle expired cards and gateway timeouts in checkout', diff: DIFF_V2, confidence: 0.94, verified: false };
      s.patch = patch;
      this.emit('remediation', 'patch', 'Draft patch 2 using the verifier feedback (adds handler, timeout and regression test).', { node: 'active', patchState: 'draft' });
      await this.wait(1200); this.charge(0.052);
      this.emit('verifier', 'status', 'Re-testing patch 2 in a clean sandbox…', { node: 'active', workers: 'up' });
      await this.wait(1400);
      patch.verified = true;
      this.emit('verifier', 'result', 'Verified: failing tests and the new regression test pass.', { node: 'done', patchState: 'verified', workers: 'destroyed' });

      // 8 ── ship + autonomy gates
      if (s.autonomy === 'observe') {
        s.status = 'reported';
        this.emit('ship', 'result', 'Observe mode: report filed, no PR opened.', { node: 'done' });
        return;
      }
      s.prUrl = 'https://github.com/demo/shop/pull/482';
      this.emit('ship', 'status', `Opening ${s.prUrl} (demo)…`, { node: 'active', rag: true });
      await this.wait(900);
      const [ok, why] = mayAutopilot(patch, s.autonomy);
      s.kg += 5;
      if (ok) {
        s.status = 'merged'; s.decision = 'approved';
        this.emit('ship', 'patch', `Autopilot gates: ${why} (verified, ${Math.round(patch.confidence * 100)}% ≥ 92%, ${countDiffLines(patch.diff)} lines ≤ 60, no protected paths). Merged.`, { node: 'done', patchState: 'approved' });
      } else {
        s.status = 'awaiting_review';
        this.emit('ship', 'patch', `PR opened. Human review required: ${why}.`, { node: 'active', patchState: 'verified', review: true });
      }
    } catch (e) {
      if (!(e instanceof Kill)) throw e;
      s.status = 'killed';
      this.emit('ship', 'error', 'Kill-switch pulled. Sandboxes torn down, run halted.', { node: 'fail', workers: 'destroyed', killed: true });
    } finally { this.running = false; }
  }
}
