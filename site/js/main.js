import { Swarm } from './sim.js';
import { UI } from './ui.js';

const swarm = new Swarm();
let scene = null;
const ui = new UI(swarm, { onStart: () => scene?.reset() });
try {
  const { Scene3D } = await import('./scene.js');
  scene = new Scene3D(document.getElementById('stage'));
} catch (e) { console.warn('3D unavailable', e); ui.noWebGL(); }
swarm.on((ev, st) => { scene?.handle(ev, st); ui.handle(ev, st); });
document.body.classList.add('ready');
