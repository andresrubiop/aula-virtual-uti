/* Control de un navegador sin interfaz para las pruebas de extremo a extremo (Node ≥ 22, sin dependencias).
 *
 *   import { launch } from './lib/browser.mjs';
 *   const drv = await launch({ firefox: false });      // Chrome/Chromium (CDP) · { firefox: true } → Firefox (WebDriver BiDi)
 *   await drv.navigate(url); await drv.ev('document.title');
 *   await drv.pointer('down', x, y, { type: 'pen', pressure: .6 }); …('move' …) …('up' …)   // type: mouse | pen | touch
 *   await drv.key('ArrowRight'); drv.errors(); drv.close();
 *
 * Lo usan hub/tools/terminal-e2e.mjs y hub/tools/ink-e2e.mjs. El Firefox de Ubuntu es un snap: su perfil se crea en
 * ~/snap/firefox/common (el /tmp del snap es privado).
 */
import { spawn, execSync } from 'node:child_process';
import { writeFileSync, mkdtempSync, rmSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir, homedir } from 'node:os';
import { createServer } from 'node:net';

export const sleep = ms => new Promise(r => setTimeout(r, ms));
export const has = c => { try { execSync(`command -v ${c}`, { stdio: 'ignore' }); return true; } catch { return false; } };
export const freePort = () => new Promise(ok => { const s = createServer(); s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => ok(p)); }); });

async function socketTo(url) {
  for (let k = 0; k < 100; k++) {
    try {
      const ws = new WebSocket(await url());
      await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = ko; });
      return ws;
    } catch { await sleep(200); }
  }
  throw new Error('el navegador no abrió su puerto de control');
}

// Teclas: CDP necesita key + code + código virtual; BiDi, el carácter (o el código de WebDriver para las especiales)
const KEYS = {
  ArrowRight: ['ArrowRight', 39, ''], ArrowLeft: ['ArrowLeft', 37, ''], ArrowUp: ['ArrowUp', 38, ''], ArrowDown: ['ArrowDown', 40, ''],
  Escape: ['Escape', 27, ''], Enter: ['Enter', 13, ''], Tab: ['Tab', 9, ''], ' ': ['Space', 32, ' '],
  Home: ['Home', 36, ''], End: ['End', 35, ''], PageDown: ['PageDown', 34, ''], PageUp: ['PageUp', 33, ''],
};
const keyInfo = k => KEYS[k] || [/^[a-z]$/i.test(k) ? 'Key' + k.toUpperCase() : /^\d$/.test(k) ? 'Digit' + k : k, k.length === 1 ? k.toUpperCase().charCodeAt(0) : 0, k];

/* ---------- Chrome / Chromium: Chrome DevTools Protocol ---------- */
async function chrome({ width, height }) {
  const bin = process.env.CHROME || ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'].find(has);
  if (!bin) throw new Error('No se encontró Chrome/Chromium.');
  const cport = await freePort();
  const profile = mkdtempSync(join(tmpdir(), 'hubcheck-'));
  const proc = spawn(bin, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-sandbox', '--allow-file-access-from-files',
    `--remote-debugging-port=${cport}`, `--user-data-dir=${profile}`, `--window-size=${width},${height}`, 'about:blank'], { stdio: 'ignore' });
  const ws = await socketTo(async () => (await (await fetch(`http://127.0.0.1:${cport}/json/list`)).json()).find(t => t.type === 'page').webSocketDebuggerUrl);
  let seq = 0; const pending = new Map(); const events = [];
  ws.onmessage = m => { const msg = JSON.parse(m.data); if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); } else if (msg.method) events.push(msg); };
  const send = (method, params = {}) => new Promise(ok => { const i = ++seq; pending.set(i, ok); ws.send(JSON.stringify({ id: i, method, params })); });
  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable'); await send('Network.enable');
  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  const png = async (params, file) => { const r = await send('Page.captureScreenshot', { format: 'png', ...params }); writeFileSync(file, Buffer.from(r.result.data, 'base64')); };
  const touches = new Map();                          // id → [x, y] de los dedos apoyados
  return {
    name: 'Chrome', send,
    async ev(expr) {
      const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true, userGesture: true });
      if (r.result && r.result.exceptionDetails) console.error('    [js] ' + (r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text).split('\n')[0]);
      return r.result && r.result.result ? r.result.result.value : undefined;
    },
    async navigate(url) { await send('Page.navigate', { url }); },
    async reload() { await send('Page.reload'); },
    async pointer(kind, x, y, o = {}) {
      const type = o.type || 'mouse';
      if (type === 'touch') {
        const id = o.id || 1;
        if (kind === 'up') touches.delete(id); else touches.set(id, [x, y]);
        const pts = kind === 'up' && !touches.size ? [] : [...touches].map(([i, [px, py]]) => ({ x: px, y: py, id: i }));
        // touchEnd no lleva puntos (CDP); las pruebas usan un dedo a la vez
        await send('Input.dispatchTouchEvent', { type: kind === 'down' ? 'touchStart' : kind === 'up' ? 'touchEnd' : 'touchMove', touchPoints: kind === 'up' ? [] : pts });
        return;
      }
      const button = o.button || 'left';
      await send('Input.dispatchMouseEvent', {
        type: { down: 'mousePressed', move: 'mouseMoved', up: 'mouseReleased' }[kind], x, y, button,
        buttons: kind === 'up' ? 0 : o.buttons ?? 1, clickCount: 1, pointerType: type, force: type === 'pen' ? (o.pressure ?? 0.5) : undefined,
      });
    },
    async key(k, mods = 0) {
      const [code, vk, text] = keyInfo(k);
      await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code, windowsVirtualKeyCode: vk, modifiers: mods, text: k.length === 1 && !mods ? text : undefined });
      await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, code, windowsVirtualKeyCode: vk, modifiers: mods });
    },
    shot: file => png({}, file),
    clip: (file, r) => png({ captureBeyondViewport: true, clip: { ...r, scale: 1 } }, file),
    errors: () => events.filter(e => e.method === 'Runtime.exceptionThrown' || (e.method === 'Runtime.consoleAPICalled' && ['error', 'assert'].includes(e.params.type)) || (e.method === 'Log.entryAdded' && e.params.entry.level === 'error')),
    sockets: () => events.filter(e => e.method === 'Network.webSocketCreated').length,
    close() { ws.close(); proc.kill('SIGKILL'); try { rmSync(profile, { recursive: true, force: true }); } catch { /* nada */ } },
  };
}

/* ---------- Firefox: WebDriver BiDi ---------- */
async function firefox({ width, height }) {
  const bin = process.env.FIREFOX || (has('firefox') ? 'firefox' : null);
  if (!bin) throw new Error('No se encontró Firefox.');
  const fport = await freePort();
  const snap = join(homedir(), 'snap/firefox/common');
  const profile = mkdtempSync(join(existsSync(snap) ? snap : tmpdir(), 'hubcheck-'));
  const proc = spawn(bin, ['--headless', '--no-remote', '--profile', profile, `--remote-debugging-port=${fport}`, 'about:blank'], { stdio: 'ignore' });
  const ws = await socketTo(async () => `ws://127.0.0.1:${fport}/session`);
  let seq = 0; const pending = new Map(); const events = [];
  ws.onmessage = m => { const msg = JSON.parse(m.data); if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); } else if (msg.type === 'event') events.push(msg); };
  const send = (method, params = {}) => new Promise(ok => { const i = ++seq; pending.set(i, m => ok(m.type === 'success' ? m.result : { error: m.message || m.error })); ws.send(JSON.stringify({ id: i, method, params })); });
  const s = await send('session.new', { capabilities: {} });
  if (s.error) throw new Error('Firefox: ' + s.error);
  const context = (await send('browsingContext.getTree', {})).contexts[0].context;
  await send('browsingContext.setViewport', { context, viewport: { width, height } });
  await send('session.subscribe', { events: ['log.entryAdded'] });
  const act = async actions => { const r = await send('input.performActions', { context, actions: [actions] }); if (r && r.error) console.error('    [bidi] ' + r.error); return r; };
  const png = async (params, file) => { const r = await send('browsingContext.captureScreenshot', { context, ...params }); writeFileSync(file, Buffer.from(r.data, 'base64')); };
  // Firefox (156) aún no implementa el lápiz en WebDriver BiDi («Unimplemented pointerMove for pointerType pen»):
  // se simula con PointerEvent de tipo pen, con presión, lanzados en la página. Los mueve y levanta el mismo elemento
  // que lo recibió al apoyarse (como la captura del puntero); el levantar va a lo que haya bajo el punto.
  const penSintetico = (kind, x, y, o) => send('script.evaluate', { target: { context }, awaitPromise: false, expression: `(() => {
    const k = ${JSON.stringify(kind)}, x = ${x}, y = ${y}, p = ${o.pressure ?? 0.5};
    const t = k === 'down' || !window.__lapiz ? (document.elementFromPoint(x, y) || document.body) : k === 'up' ? (document.elementFromPoint(x, y) || window.__lapiz) : window.__lapiz;
    if (k === 'down') window.__lapiz = t;
    t.dispatchEvent(new PointerEvent('pointer' + k, { bubbles: true, cancelable: true, composed: true, pointerId: 77, pointerType: 'pen', isPrimary: true,
      clientX: x, clientY: y, pressure: k === 'up' ? 0 : p, button: k === 'move' ? -1 : 0, buttons: k === 'up' ? 0 : 1 }));
    if (k === 'up') window.__lapiz = null;
  })()` });
  return {
    name: 'Firefox', penSintetico: true, send,
    async ev(expr) {
      const r = await send('script.evaluate', { expression: `(async () => { const v = await (${expr}); return v === undefined ? '\u0000' : JSON.stringify(v); })()`, target: { context }, awaitPromise: true, userActivation: true });
      if (r.type === 'exception' || r.exceptionDetails) console.error('    [js] ' + (r.exceptionDetails?.text || 'excepción'));
      if (!r.result || r.type === 'exception') return undefined;
      return r.result.value === '\u0000' ? undefined : JSON.parse(r.result.value);
    },
    async navigate(url) { await send('browsingContext.navigate', { context, url, wait: 'complete' }); },
    async reload() { await send('browsingContext.reload', { context, wait: 'complete' }); },
    async pointer(kind, x, y, o = {}) {
      const type = o.type || 'mouse', id = type === 'touch' ? 'dedo' + (o.id || 1) : type;
      if (type === 'pen') return penSintetico(kind, x, y, o);
      const at = { type: 'pointerMove', x: Math.round(x), y: Math.round(y), duration: 0 };
      const extra = type === 'pen' ? { pressure: o.pressure ?? 0.5 } : {};
      if (kind === 'move' && type === 'pen') Object.assign(at, extra);
      const button = o.button === 'right' ? 2 : o.button === 'eraser' ? 5 : 0;
      await act({ type: 'pointer', id, parameters: { pointerType: type },
        actions: kind === 'down' ? [at, { type: 'pointerDown', button, ...extra }] : kind === 'up' ? [at, { type: 'pointerUp', button }] : [at] });
    },
    async key(k) { const v = keyInfo(k)[2]; await act({ type: 'key', id: 'teclado', actions: [{ type: 'keyDown', value: v }, { type: 'keyUp', value: v }] }); },
    shot: file => png({}, file),
    clip: (file, r) => png({ origin: 'document', clip: { type: 'box', ...r } }, file),
    errors: () => events.filter(e => e.method === 'log.entryAdded' && e.params.level === 'error'),
    sockets: () => null,                               // BiDi no los cuenta
    close() { ws.close(); proc.kill('SIGKILL'); try { rmSync(profile, { recursive: true, force: true }); } catch { /* nada */ } },
  };
}

export async function launch({ firefox: ff = false, width = 1440, height = 900 } = {}) {
  return ff ? firefox({ width, height }) : chrome({ width, height });
}
