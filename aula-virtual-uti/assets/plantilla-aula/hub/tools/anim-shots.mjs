#!/usr/bin/env node
/* Capturas de una animación escena por escena (Node ≥ 22 + Chrome/Chromium, sin dependencias).
 *
 *   node hub/tools/anim-shots.mjs A2.1 --scenes 0:9000,2:6000,4:9000
 *        → para cada par escena:espera(ms) entra en la escena en modo automático, espera y recorta la figura
 *   node hub/tools/anim-shots.mjs A2.1 --slide --scenes all
 *        → la copia de la presentación, maquetada como en el PDF (medio print, 297 mm de ancho), con la foto
 *          determinista de Stage.still: aquí el par es escena:segundos simulados, "all" = cada escena al 90 % de
 *          su duración (8 s si no tiene) y "print" = el data-print de la diapositiva. Recorta la diapositiva entera.
 *   Opciones: --dark · --mobile (390×844) · --width 1440 · --speed 2 (acelera la simulación) · --lang es|en
 *             --eval "js" (se ejecuta con `st` = Stage y `S` = estado antes de cada captura; si hace `return x`, imprime x)
 *   Salida: hub/tools/shots/anim-A2-1-e0.png, … (con --slide: slide-A2-1-e0-6s.png, …) y los errores de consola
 *           (código 1 si hubo errores).
 */
import { spawn, execSync } from 'node:child_process';
import { mkdirSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, '../dist/index.html');
const shotsDir = resolve(here, 'shots');
const argv = process.argv.slice(2);
const flag = n => argv.includes('--' + n);
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : d; };
const id = argv.find(a => /^A\d+\.\d+$/.test(a));
if (!id) { console.error('Uso: node hub/tools/anim-shots.mjs A2.1 --scenes 0:8000,1:6000 [--slide]'); process.exit(2); }
const unit = id.match(/^A(\d+)/)[1];
const slide = flag('slide');
const mobile = flag('mobile');
// 297 mm = 1123 px CSS: el ancho de la página del PDF de las presentaciones
const W = +opt('width', mobile ? 390 : slide ? 1123 : 1440), H = +opt('height', mobile ? 844 : 900);
const speed = +opt('speed', 1);
const lang = opt('lang', 'es');
const EVAL = opt('eval', '');

const chrome = process.env.CHROME || ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']
  .find(c => { try { execSync(`command -v ${c}`, { stdio: 'ignore' }); return true; } catch { return false; } });
if (!chrome) { console.error('No se encontró Chrome/Chromium.'); process.exit(2); }
const port = 9700 + Math.floor(Math.random() * 250);
const profile = mkdtempSync(join(tmpdir(), 'animshots-'));
const proc = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-sandbox', '--allow-file-access-from-files',
  `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--hide-scrollbars', `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function target() {
  for (let k = 0; k < 60; k++) {
    try { const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); const p = l.find(t => t.type === 'page'); if (p) return p.webSocketDebuggerUrl; } catch { /* aún no */ }
    await sleep(150);
  }
  throw new Error('Chrome no respondió');
}
const ws = new WebSocket(await target());
await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = ko; });
let seq = 0; const pending = new Map(); const events = [];
ws.onmessage = m => { const msg = JSON.parse(m.data); if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); } else if (msg.method) events.push(msg); };
const send = (method, params = {}) => new Promise(ok => { const i = ++seq; pending.set(i, ok); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async expr => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); return r.result && r.result.result ? r.result.result.value : undefined; };
const quit = code => { ws.close(); proc.kill('SIGKILL'); try { rmSync(profile, { recursive: true, force: true }); } catch { /* nada */ } process.exit(code); };

await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile });
await send('Page.navigate', { url: `file://${dist}?lang=${lang}#/u${unit}/${slide ? 'presentacion' : 'animaciones'}` });
await sleep(900);
await evaluate(`Hub.theme.set('${flag('dark') ? 'dark' : 'light'}')`);
mkdirSync(shotsDir, { recursive: true });
const slug = id.replace('.', '-');

if (slide) {
  // Igual que check.mjs --deck: todas las diapositivas en columna, maquetadas para imprimir.
  await send('Emulation.setEmulatedMedia', { media: 'print' });
  const host = `document.querySelector('.slide [data-anim="${id}"]')`;
  const ok = await evaluate(`(async () => {
    const a = ${host}; if (!a) return false;
    document.documentElement.classList.add('print-deck');
    if (!a.hasAttribute('data-mounted')) Hub.anim.mount(a);
    if (Hub.math) Hub.math.render(a.closest('.slide'));
    await document.fonts.ready; return !!a._stage; })()`);
  if (!ok) { console.error(`La animación ${id} no está en la presentación P${unit} (o falta su spec).`); quit(1); }
  await sleep(300);
  const info = await evaluate(`(() => { const a = ${host}; return { print: a.dataset.print || '', durs: a._stage.spec.scenes.map(s => s.dur || 0) }; })()`);
  const arg = opt('scenes', 'all');
  const pairs = arg === 'all' ? info.durs.map((d, k) => [k, d ? +(d * 0.9).toFixed(1) : 8])
    : arg === 'print' ? [(info.print || '0:0').split(':').map(Number)]
    : arg.split(',').map(s => s.split(':').map(Number));
  console.log(`${id} · data-print="${info.print}" · duración de las escenas: ${info.durs.join(', ')} s`);
  for (const [k, secs] of pairs) {
    const r = await evaluate(`(() => { const a = ${host}, st = a._stage, S = st.S; st.still(${k}, ${secs || 0});
      const v = (() => { ${EVAL} })();
      const b = a.closest('.slide').getBoundingClientRect(); return { v, x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height }; })()`);
    if (r.v !== undefined && r.v !== null) console.log('  eval →', typeof r.v === 'string' ? r.v : JSON.stringify(r.v));
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: r.w, height: r.h, scale: 1 } });
    const name = `slide-${slug}-e${k}-${secs || 0}s${lang === 'en' ? '-en' : ''}.png`;
    writeFileSync(join(shotsDir, name), Buffer.from(shot.result.data, 'base64'));
    console.log(`escena ${k} + ${secs || 0} s → hub/tools/shots/${name}`);
  }
} else {
  const scenes = (opt('scenes', '0:6000')).split(',').map(s => s.split(':').map(Number));
  // la del laboratorio de técnicas (no la copia compacta dentro de una presentación)
  const host = `[...document.querySelectorAll('[data-anim="${id}"]')].find(e => !e.closest('.slide'))`;
  const ok = await evaluate(`!!(${host} && ${host}._stage)`);
  if (!ok) { console.error(`La animación ${id} no está montada (¿falta la spec?).`); quit(1); }
  const scrollTo = `(() => { const y = ${host}.getBoundingClientRect().top + scrollY - 12; window.scrollTo(0, y); return scrollY; })()`;
  await evaluate(`${host}._stage.speed = ${speed}`);
  await evaluate(scrollTo);
  await sleep(500);
  await evaluate(scrollTo);   // por si el enrutador o la carga de fuentes movieron la página
  await sleep(300);
  for (const [k, ms] of scenes) {
    await evaluate(scrollTo);
    await evaluate(`(() => { const st = ${host}._stage; st.go(${k}, false); st.play(); })()`);
    await sleep(ms);
    if (EVAL) { const v = await evaluate(`(() => { const st = ${host}._stage, S = st.S; ${EVAL} })()`); if (v !== undefined) console.log('  eval →', typeof v === 'string' ? v : JSON.stringify(v)); }
    await sleep(120);
    const r = await evaluate(`(() => { const b = ${host}.querySelector('.stage').getBoundingClientRect(); return {x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height}; })()`);
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: r.w, height: Math.min(r.h, 3000), scale: 1 } });
    const name = `anim-${slug}-e${k}${mobile ? '-m' : ''}${flag('dark') ? '-dark' : ''}.png`;
    writeFileSync(join(shotsDir, name), Buffer.from(shot.result.data, 'base64'));
    console.log(`escena ${k} (${ms} ms) → hub/tools/shots/${name}`);
  }
}
const errs = events.filter(e => e.method === 'Runtime.exceptionThrown' || (e.method === 'Runtime.consoleAPICalled' && ['error', 'warning', 'assert'].includes(e.params.type)))
  .map(e => e.method === 'Runtime.exceptionThrown' ? 'EXCEPCIÓN ' + (e.params.exceptionDetails.exception?.description || e.params.exceptionDetails.text) : e.params.type.toUpperCase() + ' ' + e.params.args.map(a => a.value ?? a.description ?? '').join(' '));
errs.forEach(x => console.log('  ✗ ' + x));
console.log(errs.length ? `${errs.length} error(es).` : 'Sin errores de consola.');
quit(errs.length ? 1 : 0);
