import { BUDGET_USD, MAX_INTENSITY } from './sim.js';
const $ = (s) => document.querySelector(s);

export class UI {
  constructor(swarm, hooks) {
    this.swarm = swarm; this.hooks = hooks;
    this.feed = $('#feed'); this.startBtn = $('#start'); this.pauseBtn = $('#pause'); this.killBtn = $('#kill');
    $('#intensity').max = MAX_INTENSITY; $('#intensity').addEventListener('input', () => this.syncIntensity()); this.syncIntensity();
    this.startBtn.addEventListener('click', () => this.start());
    this.pauseBtn.addEventListener('click', () => { const p = swarm.togglePause(); this.pauseBtn.textContent = p ? 'Resume' : 'Pause'; this.pauseBtn.setAttribute('aria-pressed', p); });
    this.killBtn.addEventListener('click', () => swarm.kill());
    $('#speed').addEventListener('change', (e) => (swarm.speed = +e.target.value));
    $('#approve').addEventListener('click', () => swarm.decide('approved'));
    $('#reject').addEventListener('click', () => swarm.decide('rejected'));
    $('#mockup').addEventListener('change', (e) => { this.mockup = e.target.files[0]?.name ?? null; });
    document.querySelectorAll('[data-open]').forEach((b) => b.addEventListener('click', () => this.dock(b.dataset.open, b)));
    this.renderState(swarm.state);
  }
  syncIntensity() { const v = +$('#intensity').value; $('#intensityOut').textContent = `${Math.round(v * 100)}% (policy cap ${MAX_INTENSITY * 100}%)`; }
  dock(id, btn) {                                    // mobile bottom-sheet switcher
    const card = document.getElementById(id), open = !card.classList.contains('open');
    document.querySelectorAll('.card').forEach((c) => c.classList.remove('open'));
    document.querySelectorAll('[data-open]').forEach((b) => b.setAttribute('aria-expanded', 'false'));
    if (open) { card.classList.add('open'); btn.setAttribute('aria-expanded', 'true'); }
  }
  cfg() {
    return { story: $('#story').value, faults: [...document.querySelectorAll('input[name=fault]:checked')].map((i) => i.value),
      intensity: +$('#intensity').value, autonomy: document.querySelector('input[name=autonomy]:checked').value,
      seedBug: $('#seedBug').checked, mockup: this.mockup };
  }
  async start() {
    if (this.swarm.running) return;
    this.feed.innerHTML = ''; this.hooks.onStart();
    this.startBtn.disabled = true; this.pauseBtn.disabled = false; this.killBtn.disabled = false; this.pauseBtn.textContent = 'Pause';
    if (window.matchMedia('(max-width: 959px)').matches) this.dock('p-feed', document.querySelector('[data-open=p-feed]'));
    await this.swarm.run(this.cfg());
    this.startBtn.disabled = false; this.pauseBtn.disabled = true; this.killBtn.disabled = true; this.renderState(this.swarm.state);
  }
  handle(ev, st) {
    const li = document.createElement('li'); li.className = `ev ${ev.kind}`;
    li.innerHTML = '<span class="who"></span><time></time><p></p>';
    li.querySelector('.who').textContent = ev.agent.replace('_', ' ');
    li.querySelector('time').textContent = new Date(ev.ts).toLocaleTimeString();
    li.querySelector('p').textContent = ev.text;
    this.feed.prepend(li); while (this.feed.children.length > 80) this.feed.lastChild.remove();
    this.renderState(st);
  }
  renderState(s) {
    $('#m-status').textContent = s.status.replace('_', ' '); $('#m-status').dataset.s = s.status;
    $('#m-risk').style.width = `${Math.round(s.risk * 100)}%`; $('#m-risk-t').textContent = s.risk ? `${Math.round(s.risk * 100)}%` : '–';
    $('#m-tests').textContent = `${s.passed} passed · ${s.failed} failed`;
    $('#m-kg').textContent = `${12 + s.kg * 9} nodes`; $('#m-attempt').textContent = s.attempt ? `${s.attempt} of 3` : '–';
    $('#m-cost').textContent = `$${s.cost.toFixed(3)} of $${BUDGET_USD}`;
    const p = s.patch;
    $('#patch-empty').hidden = !!p; $('#patch-body').hidden = !p;
    if (p) {
      $('#patch-title').textContent = p.title;
      $('#patch-meta').textContent = `${p.verified ? 'Verified in sandbox' : 'Not verified'} · ${Math.round(p.confidence * 100)}% confident`;
      const pre = $('#diff'); pre.replaceChildren();
      for (const line of p.diff.split('\n')) { const sp = document.createElement('span'); sp.textContent = line + '\n';
        sp.className = line.startsWith('+') ? 'add' : line.startsWith('-') ? 'del' : line.startsWith('@@') ? 'hunk' : ''; pre.append(sp); }
      const need = s.status === 'awaiting_review';
      $('#approve').disabled = !need || !p.verified; $('#reject').disabled = !need;
      $('#decision').textContent = need ? 'Waiting for a reviewer.' : s.decision ? `Decision: ${s.decision}.` : '';
    }
  }
  noWebGL() { $('#nogl').hidden = false; }
}
