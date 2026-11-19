#!/usr/bin/env node
/* Revisión automática de accesibilidad del aula compilada (Node ≥ 22 + Chrome/Chromium; sin dependencias).
 *
 *   node hub/tools/accesibilidad.mjs                     → todas las rutas, ES y EN, tema claro y oscuro
 *   node hub/tools/accesibilidad.mjs --routes "#/u1/manual,#/u1/quiz" --lang es --tema claro
 *   node hub/tools/accesibilidad.mjs --profesor          → la edición docente
 *
 * Comprueba en cada ruta (lo que un lector de pantalla, el teclado o una persona con baja visión necesitan):
 *   · contraste de texto WCAG AA (4,5:1; 3:1 en texto grande), con el color de fondo real de cada elemento;
 *   · imágenes con alt (alt="" solo si son decorativas), lienzos de animación con descripción (role="img" + aria-label);
 *   · botones, enlaces y campos con nombre accesible; iframes con title;
 *   · un único h1 visible y sin saltos de nivel entre encabezados;
 *   · teclado: recorre con Tab y exige foco visible (contorno o sombra) en cada elemento que recibe el foco;
 *   · videos con subtítulos;
 *   · con «reducir movimiento» del sistema activado, ninguna animación CSS infinita.
 * Escribe control/ACCESIBILIDAD.md (para el docente) y control/accesibilidad.json. Código 1 si hay errores.
 * No sustituye la revisión con un lector de pantalla real ni la valoración pedagógica: lo indica el informe.
 */
import { writeFileSync, readFileSync, readdirSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, sleep } from './lib/browser.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '../..');
const argv = process.argv.slice(2);
const flag = n => argv.includes('--' + n);
const opt = (n, d) => { const i = argv.indexOf('--' + n); return i >= 0 ? argv[i + 1] : d; };
const dist = resolve(here, '../dist/' + (flag('profesor') ? 'profesor.html' : 'index.html'));
if (!existsSync(dist)) { console.error('Falta ' + dist + ': ejecuta python3 hub/build.py'); process.exit(2); }
const course = JSON.parse(readFileSync(resolve(here, '../src/course.json'), 'utf8'));
const subsOf = id => {
  const dir = resolve(here, '../src/content', id);
  const found = existsSync(dir) ? readdirSync(dir).map(f => (f.match(/^\d+-([a-z]+)\.html$/) || [])[1]).filter(Boolean) : [];
  return [...new Set(['resumen', ...found, 'animaciones'])];
};
const ROUTES = (opt('routes', '') || '').split(',').map(s => s.trim()).filter(Boolean);
const routes = ROUTES.length ? ROUTES : ['#/inicio', ...course.units.flatMap(u => subsOf(u.id).map(s => `#/${u.id}/${s}`)), '#/recursos'];
const langs = (opt('lang', 'es,en')).split(',');
const temas = { claro: 'light', oscuro: 'dark' };
const temasPedidos = opt('tema', 'claro,oscuro').split(',').filter(t => temas[t]);
const TABS = +opt('tabs', 40);

// Revisión dentro de la página (se ejecuta en el navegador)
const AUDIT = `(() => {
  const out = [];
  const vis = e => e.checkVisibility ? e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) : e.offsetParent !== null;
  const oculto = e => !!e.closest('[aria-hidden="true"], [hidden], .sr-only');
  const donde = e => {
    const partes = []; let x = e;
    for (let k = 0; x && x.nodeType === 1 && k < 3; k++, x = x.parentElement) {
      partes.unshift(x.tagName.toLowerCase() + (x.id ? '#' + x.id : '') + (x.classList.length ? '.' + [...x.classList].slice(0, 2).join('.') : ''));
    }
    const txt = (e.innerText || e.getAttribute('aria-label') || e.getAttribute('alt') || '').trim().replace(/\\s+/g, ' ').slice(0, 50);
    return partes.join(' > ') + (txt ? ' «' + txt + '»' : '');
  };
  const add = (tipo, gravedad, e, detalle) => out.push({ tipo, gravedad, donde: e ? donde(e) : '', detalle });
  const nombre = e => {
    const lb = e.getAttribute('aria-labelledby');
    if (lb) return lb.split(/\\s+/).map(id => (document.getElementById(id) || {}).textContent || '').join(' ').trim();
    if (e.getAttribute('aria-label')) return e.getAttribute('aria-label').trim();
    if (e.labels && e.labels.length) return [...e.labels].map(l => l.innerText).join(' ').trim();
    const t = (e.innerText || '').trim();
    if (t) return t;
    const img = e.querySelector('img[alt]:not([alt=""]), svg[aria-label], [role="img"][aria-label]');
    if (img) return img.getAttribute('alt') || img.getAttribute('aria-label');
    return (e.getAttribute('title') || e.getAttribute('value') || e.getAttribute('placeholder') || '').trim();
  };

  // Imágenes y lienzos
  for (const e of document.querySelectorAll('img')) {
    if (!vis(e) || oculto(e)) continue;
    if (!e.hasAttribute('alt')) add('imagen sin alt', 'error', e, 'Añade alt con lo que muestra, o alt="" si es decorativa.');
  }
  for (const e of document.querySelectorAll('canvas')) {
    if (!vis(e) || oculto(e)) continue;
    const d = e.getAttribute('aria-label') || e.getAttribute('aria-labelledby') || e.getAttribute('aria-describedby');
    if (!d) add('lienzo sin descripción', 'error', e, 'Una animación necesita role="img" y aria-label con lo que representa.');
  }
  for (const e of document.querySelectorAll('svg')) {
    if (!vis(e) || oculto(e) || e.closest('button, a, label')) continue;
    if (e.getAttribute('role') === 'img' && !e.getAttribute('aria-label') && !e.querySelector('title')) add('figura SVG sin nombre', 'error', e, 'role="img" requiere aria-label o <title>.');
  }
  // Controles con nombre
  for (const e of document.querySelectorAll('a[href], button, input:not([type="hidden"]), select, textarea, [role="button"], [role="switch"], [role="tab"]')) {
    if (!vis(e) || oculto(e)) continue;
    if (!nombre(e)) add('control sin nombre', 'error', e, 'Un lector de pantalla no sabría qué hace: añade texto o aria-label.');
  }
  for (const e of document.querySelectorAll('iframe')) {
    if (vis(e) && !oculto(e) && !e.getAttribute('title')) add('iframe sin title', 'error', e, 'Describe el contenido incrustado con title.');
  }
  // Encabezados
  const hs = [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')].filter(e => vis(e) && !oculto(e));
  const h1 = hs.filter(e => e.tagName === 'H1');
  if (h1.length !== 1) add('h1', 'aviso', h1[1] || null, 'Debe haber un único h1 visible por vista (hay ' + h1.length + ').');
  for (let i = 1; i < hs.length; i++) {
    const a = +hs[i - 1].tagName[1], b = +hs[i].tagName[1];
    if (b > a + 1) add('salto de encabezado', 'aviso', hs[i], 'Pasa de h' + a + ' a h' + b + ' sin nivel intermedio.');
  }
  // Videos
  for (const v of document.querySelectorAll('video')) {
    if (vis(v) && !v.querySelector('track[kind="subtitles"], track[kind="captions"]') && !(v.textTracks && v.textTracks.length))
      add('video sin subtítulos', 'aviso', v, 'Añade subtítulos (hub/tools/subtitulos.py).');
  }
  // Contraste
  const rgba = s => { const m = s.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const mezcla = (arriba, abajo) => { const a = arriba[3]; return [0, 1, 2].map(i => arriba[i] * a + abajo[i] * (1 - a)).concat(1); };
  const fondo = e => {
    const capas = [];
    for (let x = e; x; x = x.parentElement) {
      const cs = getComputedStyle(x);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;          // degradado o imagen: no evaluable
      const c = rgba(cs.backgroundColor);
      if (c && c[3] > 0) { capas.push(c); if (c[3] >= 1) break; }
    }
    let base = [255, 255, 255, 1];
    for (let i = capas.length - 1; i >= 0; i--) base = mezcla(capas[i], base);
    return base;
  };
  const vistos = new Set(); let evaluados = 0, sinEvaluar = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walker.nextNode());) {
    if (!n.textContent.trim()) continue;
    const e = n.parentElement;
    if (!e || !vis(e) || oculto(e) || e.closest('canvas, svg, script, style, noscript')) continue;
    const cs = getComputedStyle(e);
    const fg = rgba(cs.color); if (!fg) continue;
    const bg = fondo(e);
    if (!bg) { sinEvaluar++; continue; }
    const fgc = fg[3] < 1 ? mezcla(fg, bg) : fg;
    const L1 = lum(fgc), L2 = lum(bg), r = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    const px = parseFloat(cs.fontSize), negrita = +cs.fontWeight >= 700;
    const grande = px >= 24 || (negrita && px >= 18.66);
    const min = grande ? 3 : 4.5;
    evaluados++;
    if (r + 0.01 < min) {
      const clave = cs.color + '|' + bg.join(',') + '|' + grande;
      if (vistos.has(clave)) continue;
      vistos.add(clave);
      add('contraste', 'error', e, 'Contraste ' + r.toFixed(2) + ':1 (mínimo ' + min + ':1) · texto ' + cs.color + ' sobre rgb(' + bg.slice(0, 3).map(Math.round).join(', ') + ')');
    }
  }
  return { hallazgos: out, contraste: { evaluados, sin_evaluar: sinEvaluar } };
})()`;

const FOCO = `(() => {
  const e = document.activeElement;
  if (!e || e === document.body || e === document.documentElement) return null;
  const cs = getComputedStyle(e);
  const contorno = cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0 && !/rgba\\(\\s*0,\\s*0,\\s*0,\\s*0\\s*\\)|transparent/.test(cs.outlineColor);
  const sombra = cs.boxShadow && cs.boxShadow !== 'none';
  const r = e.getBoundingClientRect();
  const visible = (e.checkVisibility ? e.checkVisibility() : e.offsetParent !== null) && r.width > 0 && r.height > 0;
  const txt = (e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ').slice(0, 50);
  return { donde: e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.classList.length ? '.' + [...e.classList].slice(0, 2).join('.') : '') + (txt ? ' «' + txt + '»' : ''),
           visible, indicador: contorno || sombra };
})()`;

const drv = await launch({ width: 1440, height: 900 });
const resultados = [];
try {
  for (const tema of temasPedidos) for (const lang of langs) for (const ruta of routes) {
    await drv.navigate('about:blank'); await sleep(80);
    await drv.navigate(pathToFileURL(dist).href + '?lang=' + lang + ruta);
    await sleep(900);
    await drv.ev(`document.documentElement.setAttribute('data-theme', '${temas[tema]}'); window.Hub && Hub.emit && Hub.emit('theme', '${temas[tema]}'); true`);
    await sleep(250);
    const r = await drv.ev(AUDIT);
    // Teclado: recorre con Tab desde el inicio de la página
    await drv.ev('document.activeElement && document.activeElement.blur(); window.scrollTo(0, 0); true');
    const vistos = new Set(); let sinFoco = 0;
    for (let k = 0; k < TABS; k++) {
      await drv.key('Tab'); await sleep(30);
      const f = await drv.ev(FOCO);
      if (!f) continue;
      if (vistos.has(f.donde)) continue;
      vistos.add(f.donde);
      if (!f.visible) r.hallazgos.push({ tipo: 'foco en elemento oculto', gravedad: 'aviso', donde: f.donde, detalle: 'El teclado llega a un elemento que no se ve.' });
      else if (!f.indicador) { sinFoco++; r.hallazgos.push({ tipo: 'foco invisible', gravedad: 'error', donde: f.donde, detalle: 'Al llegar con Tab no se ve dónde está el foco (contorno o sombra).' }); }
    }
    resultados.push({ ruta, lang, tema, ...r, teclado: { elementos: vistos.size, sin_foco_visible: sinFoco } });
    const e = r.hallazgos.filter(h => h.gravedad === 'error').length, a = r.hallazgos.length - e;
    console.log(`${e ? '✗' : '✓'} ${tema.padEnd(6)} ${lang} ${ruta.padEnd(24)} errores ${e} · avisos ${a} · contraste ${r.contraste.evaluados} textos · teclado ${vistos.size}`);
  }
  // Reducir movimiento: sin animaciones CSS infinitas
  await drv.send('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-reduced-motion', value: 'reduce' }] });
  const movimiento = [];
  for (const ruta of routes.filter(r => /inicio|animaciones|presentacion/.test(r))) {
    await drv.navigate(pathToFileURL(dist).href + '?lang=es' + ruta); await sleep(1200);
    const n = await drv.ev(`document.getAnimations().filter(a => a.playState === 'running' && a.effect && a.effect.getTiming().iterations === Infinity).map(a => (a.animationName || a.constructor.name) + ' en ' + (a.effect.target ? a.effect.target.tagName.toLowerCase() + '.' + [...a.effect.target.classList].join('.') : '?'))`);
    if (n.length) movimiento.push({ ruta, animaciones: n });
  }
  const errores = resultados.flatMap(r => r.hallazgos.filter(h => h.gravedad === 'error').map(h => ({ ...h, ruta: r.ruta, lang: r.lang, tema: r.tema })));
  const avisos = resultados.flatMap(r => r.hallazgos.filter(h => h.gravedad !== 'error').map(h => ({ ...h, ruta: r.ruta, lang: r.lang, tema: r.tema })));
  for (const m of movimiento) avisos.push({ tipo: 'movimiento con «reducir movimiento»', gravedad: 'aviso', ruta: m.ruta, lang: 'es', tema: '', donde: m.animaciones.slice(0, 3).join('; '), detalle: 'Detén las animaciones infinitas con prefers-reduced-motion.' });
  // Agrupar: el mismo problema en el mismo elemento se informa una vez, con las vistas donde aparece
  const agrupar = lista => {
    const g = new Map();
    for (const h of lista) {
      const k = h.tipo + '|' + h.donde + '|' + h.detalle;
      if (!g.has(k)) g.set(k, { ...h, vistas: [] });
      g.get(k).vistas.push(`${h.ruta} ${h.lang}${h.tema ? ' ' + h.tema : ''}`);
    }
    return [...g.values()];
  };
  const E = agrupar(errores), A = agrupar(avisos);
  const informe = { fecha: new Date().toISOString(), archivo: dist.replace(root, '').replace(/^[\\/]/, ''), rutas: routes.length, idiomas: langs, temas: temasPedidos,
    textos_contraste: resultados.reduce((s, r) => s + r.contraste.evaluados, 0), textos_sin_evaluar: resultados.reduce((s, r) => s + r.contraste.sin_evaluar, 0),
    errores: E, avisos: A, resultado: E.length ? 'con_errores' : 'sin_errores' };
  mkdirSync(resolve(root, 'control'), { recursive: true });
  writeFileSync(resolve(root, 'control/accesibilidad.json'), JSON.stringify(informe, null, 1) + '\n');
  const fila = h => `| ${h.tipo} | ${h.donde.replace(/\|/g, '\\|')} | ${h.detalle.replace(/\|/g, '\\|')} | ${h.vistas.slice(0, 4).join(', ')}${h.vistas.length > 4 ? ` y ${h.vistas.length - 4} más` : ''} |`;
  const md = [`# Accesibilidad del aula`, '',
    `Revisión automática del ${informe.fecha.slice(0, 10)} sobre \`${informe.archivo}\`: ${routes.length} vistas × ${langs.join('/')} × tema ${temasPedidos.join('/')}. ` +
    `${informe.textos_contraste} textos medidos para contraste (${informe.textos_sin_evaluar} sobre degradados o imágenes, sin medir).`, '',
    `**Resultado:** ${E.length ? `${E.length} problema(s) que corregir` : 'sin errores automáticos'} · ${A.length} aviso(s).`, '',
    'Esta revisión no sustituye probar el aula con un lector de pantalla (NVDA, VoiceOver o Lector de Windows) ni la valoración pedagógica del docente (`control/CALIDAD.md`).', '',
    ...(E.length ? ['## Por corregir', '', '| Qué | Dónde | Detalle | Vistas |', '|---|---|---|---|', ...E.map(fila), ''] : []),
    ...(A.length ? ['## Avisos', '', '| Qué | Dónde | Detalle | Vistas |', '|---|---|---|---|', ...A.map(fila), ''] : [])].join('\n');
  writeFileSync(resolve(root, 'control/ACCESIBILIDAD.md'), md + '\n');
  console.log(`\n${E.length ? '✗' : '✓'} ${E.length} error(es) y ${A.length} aviso(s) → control/ACCESIBILIDAD.md`);
  process.exitCode = E.length ? 1 : 0;
} finally {
  drv.close();
}
