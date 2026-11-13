#!/usr/bin/env node
/* Verificación headless del hub (sin dependencias; Node ≥ 22 + Google Chrome/Chromium).
 *
 *   node hub/tools/check.mjs                         → recorre las rutas por defecto y reporta errores
 *   node hub/tools/check.mjs --shots                 → además guarda capturas en hub/tools/shots/
 *   node hub/tools/check.mjs --routes "#/s1/animaciones" --shots --mobile --full
 *   node hub/tools/check.mjs --routes "#/s1/animaciones" --eval "document.querySelector('#anim-A1-3').scrollIntoView()" --wait 3000 --shots
 *
 * Opciones: --width 1440 --height 900 --mobile (390×844) --full (página completa, máx. 12000 px)
 *           --dark (tema oscuro) --wait ms (espera tras cargar, def. 1500) --eval "js" (se ejecuta antes de esperar)
 *           --pdf archivo.pdf  exporta la ruta a PDF A4 con encabezado y pie UTI (--titulo "texto" en el encabezado; --lang es|en)
 *           --lang es|en|both  idioma(s) a verificar (both = es y en, por defecto)
 *                              · --strict: una sección pendiente, o texto inglés de respaldo en una vista que se declara
 *                              traducida (data-l10n), cuenta como error
 *           --deck             con --pdf: exporta la presentación de la ruta, una diapositiva 16:9 por página; cada
 *                              animación sale en la escena de su data-print="escena:segundos" (Stage.still)
 *           --show-missing N   lista hasta N cadenas de JavaScript que se mostraron en inglés (fr/ca/ja)
 *           --html ruta        verifica otro archivo HTML en lugar de hub/dist/index.html
 *           --url URL          verifica el aula servida por HTTP (p. ej. la copia de GitHub Pages: hub/tools/github.py)
 *           --slides           en las rutas con presentación, mide cada diapositiva en pantalla: error si un bloque
 *                              baja hasta el pie o se sale por la derecha (los PDF: hub/tools/deck_overflow.py)
 * Código de salida 1 si hubo errores de consola o excepciones.
 */
import { spawn, execSync } from 'node:child_process';
import { mkdirSync, writeFileSync, mkdtempSync, rmSync, readFileSync, readdirSync, existsSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const shotsDir = resolve(here, 'shots');

const argv = process.argv.slice(2);
const flag = n => argv.includes('--' + n);
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : d; };
// --profesor = edición docente · --html ruta = otro archivo (p. ej. Blackboard/MIAR0525_aula_interactiva.html)
const dist = opt('html') ? resolve(opt('html')) : resolve(here, '../dist/' + (flag('profesor') ? 'profesor.html' : 'index.html'));
// Rutas por defecto: portada, cada unidad con todas sus secciones (las que tengan archivo en src/content/<id>/,
// más resumen y animaciones, que build.py genera si faltan) y Recursos. Se leen de course.json.
const course = JSON.parse(readFileSync(resolve(here, '../src/course.json'), 'utf8'));
const subsOf = id => {
  const dir = resolve(here, '../src/content', id);
  const found = existsSync(dir) ? readdirSync(dir).map(f => (f.match(/^\d+-([a-z]+)\.html$/) || [])[1]).filter(Boolean) : [];
  return [...new Set(['resumen', ...found, 'animaciones'])];
};
const DEFAULT_ROUTES = ['#/inicio', ...course.units.flatMap(u => subsOf(u.id).map(s => `#/${u.id}/${s}`)), '#/recursos'];
const routes = (opt('routes', '') || '').split(',').map(s => s.trim()).filter(Boolean);
const ROUTES = routes.length ? routes : DEFAULT_ROUTES;
const mobile = flag('mobile');
const W = +opt('width', mobile ? 390 : 1440), H = +opt('height', mobile ? 844 : 900);
const WAIT = +opt('wait', 1500);
const EVAL = opt('eval', '');
// --lang es|en|fr|ca|ja, una lista (es,fr), both (es y en, por defecto) o all (los cinco)
const LANG_OPT = opt('lang', 'both');
const LANGS = LANG_OPT === 'both' || LANG_OPT === 'all' ? ['es', 'en'] : LANG_OPT.split(',');

// Chrome, Edge o Chromium: variable CHROME, el PATH (Linux) o las rutas habituales de macOS y Windows
const chrome = process.env.CHROME
  || (process.platform === 'win32' ? null : ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'microsoft-edge']
    .find(c => { try { execSync(`command -v ${c}`, { stdio: 'ignore' }); return true; } catch { return false; } }))
  || ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe', 'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', 'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe']
    .find(p => existsSync(p));
if (!chrome) { console.error('No se encontró Chrome/Chromium (define CHROME=/ruta/al/binario).'); process.exit(2); }

const port = 9300 + Math.floor(Math.random() * 400);
const profile = mkdtempSync(join(tmpdir(), 'hubcheck-'));
const proc = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--no-sandbox',
  '--allow-file-access-from-files', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--hide-scrollbars',
  `--window-size=${W},${H}`, 'about:blank'], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
async function target() {
  for (let k = 0; k < 60; k++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = list.find(t => t.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch { /* aún no arranca */ }
    await sleep(150);
  }
  throw new Error('Chrome no respondió en el puerto de depuración');
}

const ws = new WebSocket(await target());
await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = ko; });
let seq = 0;
const pending = new Map();
const events = [];
ws.onmessage = m => {
  const msg = JSON.parse(m.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  else if (msg.method) events.push(msg);
};
const send = (method, params = {}) => new Promise(ok => { const id = ++seq; pending.set(id, ok); ws.send(JSON.stringify({ id, method, params })); });

await send('Runtime.enable');
await send('Log.enable');
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile });
if (flag('dark')) await send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: 'dark' }] });
if (flag('shots')) mkdirSync(shotsDir, { recursive: true });

let failures = 0;
for (const lang of LANGS) for (const route of ROUTES) {
  events.length = 0;
  await send('Page.navigate', { url: 'about:blank' });
  await sleep(100);
  await send('Page.navigate', { url: (opt('url') || 'file://' + dist) + '?lang=' + lang + route });
  await sleep(700);
  if (EVAL) {
    const r = await send('Runtime.evaluate', { expression: EVAL, awaitPromise: true });
    if (r.result && r.result.exceptionDetails) events.push({ method: 'Runtime.exceptionThrown', params: { exceptionDetails: r.result.exceptionDetails } });
  }
  await sleep(WAIT);
  const errs = [];
  for (const e of events) {
    if (e.method === 'Runtime.exceptionThrown') {
      const d = e.params.exceptionDetails;
      errs.push(`EXCEPCIÓN ${(d.exception && d.exception.description) || d.text} (línea ${d.lineNumber})`);
    } else if (e.method === 'Runtime.consoleAPICalled' && (e.params.type === 'error' || e.params.type === 'warning' || e.params.type === 'assert')) {
      errs.push(`${e.params.type.toUpperCase()} ${e.params.args.map(a => a.value ?? a.description ?? '').join(' ')}`);
    } else if (e.method === 'Log.entryAdded' && e.params.entry.level === 'error') {
      errs.push(`LOG ${e.params.entry.text}`);
    }
  }
  // Además de la consola: la ruta pedida debe existir y no debe verse texto de otro idioma (en francés, catalán y
  // japonés el inglés es el respaldo de lo que falta: se cuenta aparte y solo es error con --strict en una vista
  // que se declara traducida).
  const stat = await send('Runtime.evaluate', { expression: `(() => {
      const vis = e => (e.checkVisibility ? e.checkVisibility() : e.offsetParent !== null);
      const cur = document.documentElement.lang, extra = ['fr', 'ca', 'ja'].includes(cur);
      const view = document.querySelector('main > .view:not([hidden])');
      const tagged = view ? [...view.querySelectorAll('[lang]')].filter(e => ['es', 'en', 'fr', 'ca', 'ja'].includes(e.getAttribute('lang'))) : [];
      const leak = tagged.filter(e => !Hub.i18n.shows(e) && vis(e)).length;
      const subEl = view && view.querySelector('.sub:not([hidden])');
      const scope = subEl || view;
      const fallback = extra && scope ? [...scope.querySelectorAll('[lang="en"]')].filter(e => vis(e) && !e.closest('.l10n-note')).map(e => e.textContent.trim().slice(0, 50)) : [];
      const done = extra && view && (view.dataset.l10n || '').split(' ').includes(cur);
      // cadenas de JavaScript mostradas en inglés, sin contar los data-i18n de las otras vistas (se aplican todos al cargar)
      const ajenos = new Set([...document.querySelectorAll('[data-i18n]')].filter(e => view && !view.contains(e) && e.closest('main'))
        .flatMap(e => { try { return Object.values(JSON.parse(e.dataset.i18n)).map(p => String(p[1]).replace(/\\s+/g, ' ').trim()); } catch (x) { return []; } }));
      const jsAll = extra ? [...Hub.i18n.missing].filter(k => !ajenos.has(k)) : [];
      const jsMissing = jsAll.slice(0, +'${opt('show-missing', 6)}');
      const sub = location.hash.split('/')[2];
      const shown = document.querySelector('main > .view:not([hidden]) .sub:not([hidden])');
      return JSON.stringify({ stages: (window.Hub && Hub.anim) ? Hub.anim.instances.length : -1,
        view: document.querySelector('main > .view:not([hidden])')?.dataset.view, sub: shown ? shown.dataset.sub : null,
        missing: !!(sub && shown && shown.dataset.sub !== sub), leak, title: document.title,
        fallback: fallback.length, fallbackEx: fallback.slice(0, 3), done, jsMissing, jsMissingN: jsAll.length });
    })()`, returnByValue: true });
  const info = stat.result && stat.result.result ? stat.result.result.value : '{}';
  const st = JSON.parse(info || '{}');
  if (st.leak) errs.push(`IDIOMA ${st.leak} elemento(s) visibles en el otro idioma`);
  if (st.fallback && st.done && flag('strict')) errs.push(`IDIOMA ${st.fallback} bloque(s) en inglés en una vista traducida: ${st.fallbackEx.join(' | ')}`);
  if (st.jsMissingN && st.done && flag('strict')) errs.push(`IDIOMA ${st.jsMissingN} cadena(s) de JavaScript sin traducir: ${st.jsMissing.join(' | ')}`);
  if (flag('slides')) {
    // Las diapositivas no visibles siguen maquetadas (solo ocultas): se miden todas sin navegar.
    const m = await send('Runtime.evaluate', { returnByValue: true, expression: `(() => {
      const d = document.querySelector('main > .view:not([hidden]) .deck');
      if (!d) return [];
      const out = [];
      d.querySelectorAll('.slide').forEach((s, k) => {
        const foot = s.querySelector('.slide__foot'), sr = s.getBoundingClientRect();
        const fy = foot ? foot.getBoundingClientRect().top : sr.bottom;
        let low = 0, right = 0;
        s.querySelectorAll('p, li, pre, table, .code, .stage, h2, h3, .box').forEach(e => {
          if (e.closest('.slide__foot, aside.notes')) return;
          const r = e.getBoundingClientRect();
          if (!r.width || !r.height) return;              // idioma inactivo u oculto
          if (r.bottom > fy + 1) low++;
          // la caja de un párrafo no crece con su texto: se mira también si el contenido la desborda (pre se desplaza a propósito)
          if (r.right > sr.right - 4 || (!e.matches('pre, .code') && e.scrollWidth > e.clientWidth + 2)) right++;
        });
        if (low || right) out.push('diapositiva ' + (k + 1) + (low ? ' · ' + low + ' bloque(s) llegan al pie' : '') + (right ? ' · ' + right + ' se salen por la derecha' : ''));
      });
      return out;
    })()` });
    ((m.result && m.result.result && m.result.result.value) || []).forEach(x => errs.push('DIAPOSITIVA ' + x));
  }
  const skip = st.missing && !flag('strict');     // sección aún no escrita: se informa sin fallar (con --strict falla)
  const resp = st.fallback || st.jsMissingN ? ` · en inglés: ${st.fallback} bloque(s), ${st.jsMissingN} cadena(s) JS${st.done ? '' : ' (vista sin traducir)'}` : '';
  if (opt('show-missing') && st.jsMissingN) console.log('    JS sin traducir: ' + st.jsMissing.join(' | '));
  console.log(`${errs.length ? '✗' : skip ? '·' : '✓'} ${lang} ${route.padEnd(26)} ${skip ? '(sección pendiente) ' : ''}${st.title || ''} · anim ${st.stages}${resp}`);
  errs.forEach(x => console.log('    ' + x));
  failures += errs.length;
  if (flag('shots')) {
    let clip;
    if (flag('full')) {
      const lm = await send('Page.getLayoutMetrics');
      const hgt = Math.min(12000, Math.ceil(lm.result.cssContentSize.height));
      clip = { x: 0, y: 0, width: W, height: hgt, scale: 1 };
    }
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: !!clip, ...(clip ? { clip } : {}) });
    const name = (route.replace(/[#/]+/g, '_').replace(/^_+|_+$/g, '') || 'inicio') + '-' + lang + (mobile ? '-mobile' : '') + (flag('dark') ? '-dark' : '') + '.png';
    writeFileSync(join(shotsDir, name), Buffer.from(shot.result.data, 'base64'));
    console.log('    captura → hub/tools/shots/' + name);
  }
  if (opt('pdf')) {
    const deck = flag('deck');
    // Presentación: las fotos de las animaciones se toman con la maqueta de impresión (297 mm = 1123 px, medio print)
    // para que el lienzo no se estire al imprimir, y a 2× para que su texto se lea nítido en papel.
    if (deck) {
      await send('Emulation.setDeviceMetricsOverride', { width: 1123, height: 632, deviceScaleFactor: 2, mobile: false });
      await send('Emulation.setEmulatedMedia', { media: 'print' });
    }
    await send('Runtime.evaluate', { awaitPromise: true, expression: `(async () => {
      Hub.theme.set('light');
      document.querySelectorAll('details').forEach(d => { d.open = true; });
      if (${deck}) {
        document.documentElement.classList.add('print-deck');
        const pg = document.createElement('style'); pg.textContent = '@page { size: 297mm 167.06mm; margin: 0; }'; document.head.append(pg);
        document.querySelectorAll('.slide [data-anim]').forEach(a => { if (!a.hasAttribute('data-mounted')) Hub.anim.mount(a); });
        document.querySelectorAll('.slide').forEach(sl => { if (Hub.math) Hub.math.render(sl); });
      }
      await document.fonts.ready;
      await new Promise(r => setTimeout(r, 1500));
      // cada animación, en la escena y el instante de su data-print="escena:segundos" (Stage.still: foto determinista)
      if (${deck}) document.querySelectorAll('.slide [data-anim]').forEach(a => { if (a._stage) a._stage.still(...(a.dataset.print || '0:0').split(':').map(Number)); });
    })()` });
    await sleep(600);
    const logo = readFileSync(resolve(here, '../../identidad-uti/logo-uti-horizontal-color.png')).toString('base64');
    const ct = course.title || {}, cf = course.faculty || {};
    const PIE = {
      es: [`${ct.es || 'Aula interactiva'} · UTI`, cf.es || '', 'Página', 'de'],
      en: [`${ct.en || ct.es || 'Interactive classroom'} · UTI`, cf.en || cf.es || '', 'Page', 'of'],
    }[lang] || [];
    const titulo = opt('titulo', PIE[0]);
    const header = `<div style="font-family:Arial,'Noto Sans CJK JP',sans-serif;font-size:8px;color:#5D5866;width:100%;margin:0 15mm;display:flex;align-items:center;justify-content:space-between"><img src="data:image/png;base64,${logo}" style="height:20px"><span>${titulo}</span></div>`;
    const footer = `<div style="font-family:Arial,'Noto Sans CJK JP',sans-serif;font-size:8px;color:#7A7582;width:100%;margin:0 15mm;display:flex;justify-content:space-between;border-top:1px solid #EA600A;padding-top:4px"><span>Universidad Tecnológica Indoamérica${PIE[1] ? ' · ' + PIE[1] : ''}</span><span>${PIE[2]} <span class="pageNumber"></span> ${PIE[3]} <span class="totalPages"></span></span></div>`;
    const params = deck
      ? { printBackground: true, preferCSSPageSize: true, marginTop: 0, marginBottom: 0, marginLeft: 0, marginRight: 0 }
      : { printBackground: true, displayHeaderFooter: true, headerTemplate: header, footerTemplate: footer, paperWidth: 8.27, paperHeight: 11.69, marginTop: 0.85, marginBottom: 0.75, marginLeft: 0.6, marginRight: 0.6 };
    const pdf = await send('Page.printToPDF', params);
    if (pdf.error) { console.log('    ✗ PDF: ' + pdf.error.message); failures++; }
    else {
      const out = resolve(process.cwd(), opt('pdf'));
      mkdirSync(dirname(out), { recursive: true });
      writeFileSync(out, Buffer.from(pdf.result.data, 'base64'));
      console.log('    PDF → ' + opt('pdf'));
    }
    if (deck) {
      await send('Emulation.setEmulatedMedia', { media: '' });
      await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile });
    }
  }
}

ws.close();
proc.kill('SIGKILL');
try { rmSync(profile, { recursive: true, force: true }); } catch { /* nada */ }
console.log(failures ? `\n${failures} problema(s) encontrados.` : '\nSin errores de consola.');
process.exit(failures ? 1 : 0);
