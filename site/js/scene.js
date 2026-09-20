import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { AGENTS } from './sim.js';

const COL = { idle: 0xa9b8ad, active: 0xd98e04, done: 0x1e6f5c, fail: 0xb3261e, off: 0x7d8a82 };
const RING = 5.5, WORKERS = 8;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;

function label(text) {
  const c = document.createElement('canvas'); c.width = 320; c.height = 72;
  const g = c.getContext('2d'); g.font = '600 30px system-ui, sans-serif'; g.textAlign = 'center'; g.fillStyle = '#17231F';
  g.fillText(text, 160, 46);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
  s.scale.set(3.2, 0.72, 1); s.renderOrder = 10; return s;
}
function rng(seed) { let x = seed; return () => ((x = (x * 16807) % 2147483647) / 2147483647); }

export class Scene3D {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });   // throws without WebGL
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xe9efe4);
    this.scene.fog = new THREE.Fog(0xe9efe4, 26, 60);
    this.camera = new THREE.PerspectiveCamera(50, 1, 0.1, 100);
    this.camera.position.set(0, 10.5, 15.5);
    this.controls = new OrbitControls(this.camera, canvas);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.06, maxPolarAngle: Math.PI * 0.48, minDistance: 8, maxDistance: 28,
      autoRotate: !reduced, autoRotateSpeed: 0.5, target: new THREE.Vector3(0, 1.2, 0) });

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0xb9c7b3, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(6, 12, 8); this.scene.add(sun);

    this.pulses = []; this.agents = new Map(); this.last = null; this.clock = new THREE.Clock();
    this.buildDish(); this.buildAgents(); this.buildKnowledge(); this.buildWorkers(); this.buildDiffPanel(); this.buildPatch();
    this.reset();

    new ResizeObserver(() => this.resize()).observe(canvas.parentElement); this.resize();
    this.renderer.setAnimationLoop(() => this.frame());
  }

  resize() {
    const { clientWidth: w, clientHeight: h } = this.canvas.parentElement;
    this.renderer.setSize(w, h, false); this.camera.aspect = w / h;
    this.camera.position.setLength(w < 700 ? 24 : Math.min(this.camera.position.length(), 19)); // wider framing on phones
    this.camera.updateProjectionMatrix();
  }

  buildDish() {
    const dish = new THREE.Mesh(new THREE.CylinderGeometry(9.4, 9.4, 0.3, 96),
      new THREE.MeshStandardMaterial({ color: 0xf8faf5, transparent: true, opacity: 0.85, roughness: 0.25 }));
    dish.position.y = -0.15; this.scene.add(dish);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(9.4, 0.12, 12, 128), new THREE.MeshStandardMaterial({ color: 0xcbd6c6, roughness: 0.4 }));
    rim.rotation.x = Math.PI / 2; this.scene.add(rim);
    const bus = new THREE.Mesh(new THREE.TorusGeometry(RING, 0.035, 8, 128), new THREE.MeshBasicMaterial({ color: 0x1e6f5c, transparent: true, opacity: 0.35 }));
    bus.rotation.x = Math.PI / 2; bus.position.y = 0.08; this.scene.add(bus);   // the event bus
    const busLabel = label('event bus'); busLabel.scale.set(2.2, 0.5, 1); busLabel.position.set(0, 0.6, RING + 1.4); this.scene.add(busLabel);
  }

  buildAgents() {
    const geos = [new THREE.IcosahedronGeometry(0.7, 1), new THREE.OctahedronGeometry(0.75), new THREE.DodecahedronGeometry(0.7),
      new THREE.BoxGeometry(1.1, 1.1, 1.1), new THREE.TorusKnotGeometry(0.5, 0.18, 64, 8), new THREE.ConeGeometry(0.7, 1.3, 6),
      new THREE.TetrahedronGeometry(0.85), new THREE.CylinderGeometry(0.6, 0.6, 1.1, 8), new THREE.SphereGeometry(0.75, 24, 16)];
    const links = [];
    AGENTS.forEach((a, i) => {
      const ang = (i / AGENTS.length) * Math.PI * 2 - Math.PI / 2;
      const mat = new THREE.MeshStandardMaterial({ color: COL.idle, emissive: 0x000000, roughness: 0.35, metalness: 0.1 });
      const mesh = new THREE.Mesh(geos[i], mat);
      mesh.position.set(Math.cos(ang) * RING, 1.1, Math.sin(ang) * RING); mesh.userData = { base: 1.1, i, state: 'idle' };
      const l = label(a.label); l.position.set(0, 1.5, 0); mesh.add(l);
      this.scene.add(mesh); this.agents.set(a.id, mesh);
      links.push(mesh.position.x, 1.1, mesh.position.z, 0, 1.4, 0);
    });
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(links, 3));
    this.scene.add(new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x5b6b62, transparent: true, opacity: 0.18 }))); // RAG links
  }

  buildKnowledge() {                                   // hybrid RAG: a graph that grows as the swarm learns
    const N = 90, r = rng(7), pts = [];
    for (let i = 0; i < N; i++) { const u = r() * 2 - 1, t = r() * Math.PI * 2, s = Math.sqrt(1 - u * u), d = 0.6 + r() * 1.7;
      pts.push(new THREE.Vector3(Math.cos(t) * s * d, 1.4 + u * d * 0.9, Math.sin(t) * s * d)); }
    this.kgPts = pts;
    this.kgMesh = new THREE.InstancedMesh(new THREE.SphereGeometry(0.09, 10, 8), new THREE.MeshStandardMaterial({ color: 0x1e6f5c, emissive: 0x0d3a30 }), N);
    this.scene.add(this.kgMesh);
    const v = [];
    for (let i = 1; i < N; i++) {
      const sorted = pts.slice(0, i).map((p, j) => [p.distanceTo(pts[i]), j]).sort((a, b) => a[0] - b[0]);
      for (const [, j] of [sorted[0], sorted[Math.min(1, sorted.length - 1)]]) v.push(pts[i].x, pts[i].y, pts[i].z, pts[j].x, pts[j].y, pts[j].z);
    }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
    this.kgLines = new THREE.LineSegments(g, new THREE.LineBasicMaterial({ color: 0x1e6f5c, transparent: true, opacity: 0.45 }));
    this.scene.add(this.kgLines); this.kgCount = 0; this.setKnowledge(12);
  }
  setKnowledge(n) {
    this.kgCount = Math.min(90, n); const m = new THREE.Matrix4(), z = new THREE.Matrix4().makeScale(0, 0, 0);
    for (let i = 0; i < 90; i++) this.kgMesh.setMatrixAt(i, i < this.kgCount ? m.makeTranslation(this.kgPts[i].x, this.kgPts[i].y, this.kgPts[i].z) : z);
    this.kgMesh.instanceMatrix.needsUpdate = true; this.kgLines.geometry.setDrawRange(0, Math.max(0, (this.kgCount - 1) * 4));
  }

  buildWorkers() {                                     // ephemeral chaos sandboxes
    this.workers = [];
    for (let i = 0; i < WORKERS; i++) {
      const ang = (i / WORKERS) * Math.PI * 2 + 0.2;
      const box = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshStandardMaterial({ color: COL.done, transparent: true, opacity: 0.55 }));
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(box.geometry), new THREE.LineBasicMaterial({ color: 0x17231f })); box.add(edges);
      box.position.set(Math.cos(ang) * 8.1, 0.55, Math.sin(ang) * 8.1); box.userData = { ang }; box.visible = false; this.scene.add(box); this.workers.push(box);
    }
    this.workerMode = 'hidden';
  }
  setWorkers(mode) {
    this.workerMode = mode;
    for (const w of this.workers) {
      w.visible = mode !== 'hidden' && mode !== 'destroyed';
      w.material.color.setHex(mode === 'chaos' ? COL.active : mode === 'fail' ? COL.fail : COL.done);
    }
  }

  buildDiffPanel() {                                   // CNN heatmap over a mini UI screenshot
    this.diffCanvas = document.createElement('canvas'); this.diffCanvas.width = 320; this.diffCanvas.height = 220;
    this.diffTex = new THREE.CanvasTexture(this.diffCanvas); this.diffTex.colorSpace = THREE.SRGBColorSpace;
    this.diffPanel = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 2.9), new THREE.MeshBasicMaterial({ map: this.diffTex, side: THREE.DoubleSide }));
    this.diffPanel.position.set(0, 3.6, -9.4); this.diffPanel.visible = false; this.scene.add(this.diffPanel);
    const t = label('visual diff (CNN + VLM)'); t.position.set(0, 2.0, 0); this.diffPanel.add(t);
  }
  drawDiff(cells) {
    const g = this.diffCanvas.getContext('2d'); g.fillStyle = '#f8faf5'; g.fillRect(0, 0, 320, 220);
    g.fillStyle = '#17231f'; g.fillRect(0, 0, 320, 26); g.fillStyle = '#cbd6c6'; for (let i = 0; i < 3; i++) g.fillRect(16, 44 + i * 40, 288, 28);
    g.fillStyle = '#1e6f5c'; g.fillRect(16, 170, 288, 34); g.fillStyle = '#fff'; g.font = '600 16px system-ui'; g.fillText('Pay now', 132, 193);
    g.fillStyle = 'rgba(179,38,30,0.55)';
    for (const [x, y] of cells) g.fillRect(x * 20 + 8, y * 14 + 20, 20, 14);   // 14×14 CNN grid
    this.diffTex.needsUpdate = true;
  }

  buildPatch() {
    this.patch = new THREE.Mesh(new THREE.OctahedronGeometry(0.5), new THREE.MeshStandardMaterial({ color: COL.active, emissive: 0x442a00 }));
    this.patch.position.set(0, 4.3, 0); this.patch.visible = false; this.scene.add(this.patch);
  }

  pulse(from, to, color = 0x1e6f5c) {
    const a = this.agents.get(from)?.position, b = to === 'center' ? new THREE.Vector3(0, 1.4, 0) : this.agents.get(to)?.position;
    if (!a || !b) return;
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 10), new THREE.MeshBasicMaterial({ color }));
    m.position.copy(a); this.scene.add(m); this.pulses.push({ m, a: a.clone(), b: b.clone(), t: 0 });
  }
  setNode(id, state) {
    const m = this.agents.get(id); if (!m) return; m.userData.state = state;
    m.material.color.setHex(COL[state]); m.material.emissive.setHex(state === 'active' ? 0x5a3900 : state === 'fail' ? 0x4a0f0c : 0x000000);
  }

  reset() {
    for (const id of this.agents.keys()) this.setNode(id, 'idle');
    this.setWorkers('hidden'); this.diffPanel.visible = false; this.patch.visible = false; this.setKnowledge(12); this.last = null;
    for (const p of this.pulses) this.scene.remove(p.m); this.pulses = [];
  }

  handle(ev, st) {
    if (ev.reset) this.reset();
    if (ev.node && ev.agent) {
      this.setNode(ev.agent, ev.node);
      if (ev.node === 'active' && this.last && this.last !== ev.agent) this.pulse(this.last, ev.agent, 0xd98e04);
      if (ev.node === 'active') this.last = ev.agent;
    }
    if (ev.rag) this.pulse(ev.agent, 'center', 0x1e6f5c);
    if (ev.workers) this.setWorkers(ev.workers);
    if (ev.kind === 'visual') { this.diffPanel.visible = true; this.drawDiff(ev.regions ?? []); }
    if (ev.patchState) {
      this.patch.visible = ['draft', 'unverified', 'verified', 'approved'].includes(ev.patchState);
      this.patch.material.color.setHex(ev.patchState === 'unverified' ? COL.fail : ev.patchState === 'verified' || ev.patchState === 'approved' ? COL.done : COL.active);
    }
    if (ev.killed) for (const id of this.agents.keys()) this.setNode(id, 'off');
    this.setKnowledge(12 + st.kg * 9);
  }

  frame() {
    const dt = Math.min(this.clock.getDelta(), 0.05), t = this.clock.elapsedTime;
    for (const [, m] of this.agents) {
      const { base, i, state } = m.userData;
      m.position.y = base + (reduced ? 0 : Math.sin(t * 1.2 + i) * 0.12);
      m.rotation.y += dt * (state === 'active' ? 1.6 : 0.3);
      const s = state === 'active' && !reduced ? 1 + Math.sin(t * 5) * 0.08 : 1; m.scale.setScalar(s);
    }
    for (const w of this.workers) {
      if (!w.visible) continue;
      const shake = this.workerMode === 'chaos' && !reduced ? Math.sin(t * 40 + w.userData.ang * 9) * 0.06 : 0;
      w.position.x = Math.cos(w.userData.ang) * 8.1 + shake; w.rotation.y += dt * 0.4;
    }
    this.patch.rotation.y += dt * 1.2; this.patch.rotation.x += dt * 0.6;
    this.kgMesh.rotation.y += dt * 0.04; this.kgLines.rotation.y = this.kgMesh.rotation.y;
    this.pulses = this.pulses.filter((p) => {
      p.t += dt * 1.1; p.m.position.lerpVectors(p.a, p.b, Math.min(p.t, 1)); p.m.position.y += Math.sin(Math.min(p.t, 1) * Math.PI) * 0.8;
      if (p.t >= 1) { this.scene.remove(p.m); return false; } return true;
    });
    this.controls.update(); this.renderer.render(this.scene, this.camera);
  }
}
