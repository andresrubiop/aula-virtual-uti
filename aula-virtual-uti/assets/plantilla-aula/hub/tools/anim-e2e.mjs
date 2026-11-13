#!/usr/bin/env node
/* Modos y botones de las 35 animaciones (components/10-stage.js): recorrido guiado, de corrido, libre y «Simular:».
 *
 *   node hub/tools/anim-e2e.mjs                 → Chrome · todas las animaciones, en su página y en su diapositiva
 *   node hub/tools/anim-e2e.mjs --firefox       → Firefox
 *   node hub/tools/anim-e2e.mjs A4.4 A2.1       → solo esas · --lang en|fr|ca|ja · --shots (capturas en hub/tools/shots/modos-*.png)
 *   (en francés, catalán y japonés, en las unidades traducidas: ninguna cadena del recorrido puede salir en inglés)
 *
 * En cada animación (la simulación se acelera ×40 para no esperar el tiempo real):
 *   · arranca en «Recorrido guiado» a 0,5×; al terminar el paso 1 se detiene con la tarjeta y «Siguiente» pasa al 2;
 *     en el último paso la tarjeta ofrece «Recorrido de nuevo», «Verlo de corrido» y «Probar tú»;
 *   · «De corrido» pasa de escena sola, sin tarjeta;
 *   · «Libre»: en pausa, «⏭ paso» avanza la simulación sin cambiar de escena, y reproducir tampoco la cambia;
 *   · cada botón «Simular:» deja la animación corriendo en su escena / con sus opciones (o recorriendo las escenas);
 *   · en la diapositiva, la nota del paso se ve como subtítulo sobre el lienzo.
 * Código de salida 1 si algo falla (también si hay errores de consola).
 */
import { mkdirSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { launch, sleep } from './lib/browser.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const dist = resolve(here, '../dist/index.html');
const shotsDir = resolve(here, 'shots');
const argv = process.argv.slice(2);
const FIREFOX = argv.includes('--firefox');
const shots = argv.includes('--shots');
const lang = argv.includes('--lang') ? argv[argv.indexOf('--lang') + 1] : 'es';
const only = argv.filter(a => /^A\d+\.\d+$/.test(a));
let fails = 0, oks = 0;
const check = (desc, ok, detail = '') => { if (!ok) { console.log(`  ✘ ${desc}${detail ? ' · ' + detail : ''}`); fails++; } else oks++; };

const drv = await launch({ firefox: FIREFOX });
console.log(`Navegador: ${drv.name} · idioma: ${lang}`);
const ev = expr => drv.ev(expr);
const until = async (expr, ms = 6000) => { const end = Date.now() + ms; while (Date.now() < end) { if (await ev(expr)) return true; await sleep(80); } return false; };

await drv.navigate(`file://${dist}?lang=${lang}#/inicio`);
await until('!!window.Hub && document.documentElement.classList.contains("hub-ready")');
const ids = only.length ? only : await ev('Hub.anim.ids()');

for (const id of ids) {
  const u = id.match(/^A(\d+)/)[1];
  const err0 = drv.errors().length;
  // ---------- en su página (con panel de narración) ----------
  await drv.navigate(`file://${dist}?lang=${lang}#/u${u}/animaciones`);
  await until('!!window.Hub && document.documentElement.classList.contains("hub-ready")');
  const H = `[...document.querySelectorAll('[data-anim="${id}"]')].find(e => !e.closest('.slide'))`;
  await ev(`(() => { const h = ${H}; h.scrollIntoView({ block: 'center', behavior: 'instant' }); return true; })()`);
  if (!await until(`!!(${H})?._stage?.booted && (${H})._stage.scene >= 0`)) { check(`${id}: se monta`, false); continue; }
  const S = `(${H})._stage`;
  const n = await ev(`${S}.spec.scenes.length`);
  check(`${id}: arranca en «Recorrido guiado» a 0,5×`, await ev(`${S}.mode === 'guia' && ${S}.speed === 0.5 && ${S}.root.querySelector('[data-mode=guia]').getAttribute('aria-pressed') === 'true'`));

  // Recorrido guiado: paso 1 → tarjeta → «Siguiente» → paso 2
  await ev(`(() => { ${S}.root.querySelector('[data-mode=guia]').click(); ${S}.speed = 40; return true; })()`);
  const tarjeta = await until(`!${S}.cardEl.hidden && !${S}.playing && ${S}.scene === 0`, 8000);
  check(`${id}: guiado: al terminar el paso 1 se detiene con su tarjeta`, tarjeta, JSON.stringify(await ev(`({ scene: ${S}.scene, playing: ${S}.playing, card: !${S}.cardEl.hidden, t: ${S}.sceneT })`)));
  if (tarjeta && n > 1) {
    await ev(`[...${S}.cardEl.querySelectorAll('button')].pop().click()`);
    check(`${id}: guiado: «Siguiente» pasa al paso 2 y sigue`, await until(`${S}.scene === 1 && ${S}.cardEl.hidden && (${S}.playing || !${S}.cardEl.hidden)`, 3000));
  }
  await ev(`(() => { ${S}.speed = 40; ${S}.go(${n - 1}, true); ${S}.play(); return true; })()`);
  const fin = await until(`!${S}.cardEl.hidden && ${S}.cardEl.querySelectorAll('button').length === 3`, 9000);
  check(`${id}: guiado: el último paso ofrece «de nuevo», «de corrido» y «probar tú»`, fin);
  if (shots && id === ids[0]) { mkdirSync(shotsDir, { recursive: true }); await drv.shot(join(shotsDir, `modos-${id.replace('.', '-')}-fin.png`)); }

  // De corrido: pasa de escena sola, sin tarjeta
  await ev(`(() => { ${S}.root.querySelector('[data-mode=corrido]').click(); ${S}.speed = 40; return true; })()`);
  check(`${id}: de corrido: pasa de escena sin detenerse`, n < 2 || await until(`${S}.scene >= 1 && ${S}.cardEl.hidden && ${S}.playing`, 8000), JSON.stringify(await ev(`({ scene: ${S}.scene, playing: ${S}.playing })`)));

  // Libre: pausa, ⏭ paso avanza sin cambiar de escena; reproducir tampoco cambia de escena
  await ev(`${S}.root.querySelector('[data-mode=libre]').click()`);
  const l0 = await ev(`({ scene: ${S}.scene, t: ${S}.t, playing: ${S}.playing, step: !${S}.stepBtn.hidden })`);
  check(`${id}: libre: en pausa y con «⏭ paso»`, !l0.playing && l0.step, JSON.stringify(l0));
  await ev(`${S}.stepBtn.click()`);
  const l1 = await ev(`({ scene: ${S}.scene, t: ${S}.t, playing: ${S}.playing })`);
  check(`${id}: libre: «⏭ paso» avanza la simulación y queda en pausa`, l1.t > l0.t && !l1.playing && l1.scene === l0.scene, JSON.stringify([l0, l1]));
  await ev(`(() => { ${S}.play(); ${S}.speed = 40; return true; })()`);
  await sleep(700);
  check(`${id}: libre: reproduciendo, no salta de escena`, await ev(`${S}.scene === ${l0.scene}`), String(await ev(`${S}.scene`)));

  // «Simular:»: cada botón
  const nb = await ev(`${S}.presetBtns.length`);
  check(`${id}: tiene botones «Simular:»`, nb >= 2, String(nb));
  for (let k = 0; k < nb; k++) {
    const p = await ev(`(() => { const st = ${S}, b = st.presetBtns[${k}], p = st.presetList()[${k}]; b.click(); return { scene: p.scene ?? null, run: !!p.run, params: p.params || {}, label: b.textContent.trim().slice(0, 30) }; })()`);
    await sleep(150);
    const r = await ev(`({ mode: ${S}.mode, scene: ${S}.scene, playing: ${S}.playing, on: ${S}.presetBtns[${k}].classList.contains('is-on'), params: ${S}.params })`);
    const paramsOk = Object.entries(p.params).every(([kk, v]) => String(r.params[kk]) === String(v));
    const sceneOk = p.scene == null || r.scene === p.scene;
    // la nota (título del panel) corresponde a lo que se simula
    if (p.scene != null) check(`${id}: «Simular: ${p.label}»: la nota es la de esa escena`, await ev(`${S}.narrTitle.textContent.trim().startsWith('${p.scene + 1}.')`), await ev(`${S}.narrTitle.textContent`));
    check(`${id}: «Simular: ${p.label}» la lanza (${p.run ? 'recorriendo las escenas' : 'modo libre'})`,
      r.mode === (p.run ? 'corrido' : 'libre') && r.on && sceneOk && paramsOk && (r.playing || await ev(`${S}.t > 0`)), JSON.stringify([p, r]));
  }
  // A4.1: una simulación elegida (zona) explica esa traducción, no la escena de fondo (revisión de Codex)
  if (id === 'A4.1') {
    await ev(`(() => { const st = ${S}; st.setMode('libre', true); st.scene = -1; st.go(3, false); st.speed = 40; return true; })()`);
    const k = await ev(`${S}.presetList().findIndex(p => p.params && p.params.zone === 'stack')`);
    await ev(`${S}.presetBtns[${k}].click()`);
    await ev(`${S}.speed = 40`);
    await sleep(900);
    const nota = await ev(`({ t: Hub.i18n.text(${S}.narrTitle), b: Hub.i18n.text(${S}.narrBody) })`);
    check('A4.1: tras «Simular: pila» en la escena «Fallo de página», la nota explica la pila (no malloc de 64 MiB)',
      /simulaci|simulation|シミュレーション/i.test(nota.t) && /(pila|stack|pile|スタック)/i.test(nota.b) && !/64 MiB/.test(nota.b), JSON.stringify(nota));
    await ev(`${S}.go(2, true)`);
    check('A4.1: al volver a una escena, la nota vuelve a ser la de la escena', await ev(`${S}.narrTitle.textContent.trim().startsWith('3.')`));
  }
  const errs = drv.errors().slice(err0);
  check(`${id}: sin errores de consola`, errs.length === 0, JSON.stringify(errs.slice(0, 2)));
  // francés, catalán y japonés: si la unidad está traducida (data-l10n), ninguna cadena del recorrido sale en inglés
  if (['fr', 'ca', 'ja'].includes(lang) && await ev(`(document.querySelector('[data-view=u${u}]').dataset.l10n || '').split(' ').includes('${lang}')`)) {
    // (sin los data-i18n de otras vistas: se aplican todos al cargar la página)
    const faltan = await ev(`(() => { const v = document.querySelector('[data-view=u${u}]');
      const ajenos = new Set([...document.querySelectorAll('main [data-i18n]')].filter(e => !v.contains(e))
        .flatMap(e => { try { return Object.values(JSON.parse(e.dataset.i18n)).map(p => String(p[1]).replace(/\\s+/g, ' ').trim()); } catch (x) { return []; } }));
      return [...Hub.i18n.missing].filter(k => !ajenos.has(k)); })()`);
    check(`${id}: todas sus cadenas traducidas (${lang})`, faltan.length === 0, faltan.slice(0, 8).join(' | '));
    await ev('Hub.i18n.missing.clear()');
  }

  // ---------- en su diapositiva: la nota del paso como subtítulo ----------
  const slide = await ev(`(() => { const d = document.querySelector('[data-view=u${u}] .deck'); if (!d) return -1; return d._deck ? d._deck.slides.findIndex(s => s.querySelector('[data-anim="${id}"]')) : -2; })()`);
  if (slide === -2 || slide >= 0) {
    await drv.navigate(`file://${dist}?lang=${lang}#/u${u}/presentacion`);
    await until('!!document.querySelector("[data-view=u' + u + '] .deck")?._deck');
    const k = await ev(`document.querySelector('[data-view=u${u}] .deck')._deck.slides.findIndex(s => s.querySelector('[data-anim="${id}"]'))`);
    if (k < 0) continue;
    await ev(`(() => { const d = document.querySelector('[data-view=u${u}] .deck'); d._deck.show(${k}); d.scrollIntoView({ block: 'center', behavior: 'instant' }); return true; })()`);
    const C = `document.querySelector('[data-view=u${u}] .slide.is-active [data-anim="${id}"]')._stage`;
    const cap = await until(`(() => { const st = ${C}; return st && st.mode === 'guia' && !st.capEl.hidden && st.capTitle.textContent.startsWith('1/') && st.capBody.textContent.trim().length > 10; })()`, 6000);
    check(`${id}: en la diapositiva, el recorrido guiado muestra la nota del paso sobre el lienzo`, cap, JSON.stringify(await ev(`(() => { const st = ${C}; return st ? { mode: st.mode, cap: !st.capEl.hidden, t: st.capTitle.textContent } : null; })()`)));
    if (shots && id === ids[0]) await drv.shot(join(shotsDir, `modos-${id.replace('.', '-')}-diapositiva.png`));
    // la animación (con su fila de modos, «Simular:» y controles) no debe pisar el pie de la diapositiva
    const pie = await ev(`(() => { const st = ${C}, sl = st.root.closest('.slide'), f = sl.querySelector('.slide__foot'); if (!f) return null;
      return { abajo: Math.round(st.root.getBoundingClientRect().bottom), pie: Math.round(f.getBoundingClientRect().top), filas: Math.round(st.root.querySelector('.stage__controls').getBoundingClientRect().height) }; })()`);
    check(`${id}: en la diapositiva no pisa el pie (una sola fila de controles)`, !pie || (pie.abajo <= pie.pie + 1 && pie.filas < 60), JSON.stringify(pie));
    const e2 = drv.errors().slice(err0);
    check(`${id}: diapositiva sin errores de consola`, e2.length === 0, JSON.stringify(e2.slice(0, 2)));
  }
  console.log(`  ${id}: ok`);
}
drv.close();
console.log(fails ? `\n${fails} problema(s), ${oks} comprobaciones bien.` : `\nModos de las animaciones (${drv.name}): ${oks} comprobaciones, todo en orden.`);
process.exit(fails ? 1 : 0);
