/* Progreso del estudiante (solo en este navegador).
 *   <label class="check"><input type="checkbox" data-check="s1-v1"> <span class="check__text">
 *     <span class="check__title">Ver V1.1</span><small>6–8 min</small></span></label>
 * El prefijo del id (s1-, s2-, …) define la semana. Varias casillas con el mismo id se sincronizan.
 * Actualiza: anillo de la cabecera, barras de las tarjetas de semana, marcas del menú lateral, ruta. */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { $, $$ } = Hub.util;
  let state = {};

  function ids(prefix) {
    const set = new Set($$('input[data-check]').map(i => i.dataset.check).filter(id => !prefix || id.startsWith(prefix + '-')));
    return Array.from(set);
  }
  function ratio(prefix) {
    const all = ids(prefix);
    return all.length ? all.filter(id => state[id]).length / all.length : 0;
  }

  function paint() {
    $$('input[data-check]').forEach(inp => {
      const on = !!state[inp.dataset.check];
      inp.checked = on;
      const label = inp.closest('.check');
      if (label) label.classList.toggle('is-done', on);
    });
    // pasos de la ruta: completos si todas sus casillas lo están
    $$('.route > li').forEach(li => {
      const boxes = $$('input[data-check]', li);
      li.classList.toggle('is-done', boxes.length > 0 && boxes.every(b => b.checked));
    });
    // menú lateral: subvista completa si todas sus casillas lo están
    $$('.week-nav a[data-sub]').forEach(a => {
      const view = a.closest('.view');
      const sub = view && view.querySelector(`.sub[data-sub="${a.dataset.sub}"]`);
      const mark = a.querySelector('.nav-done');
      if (!sub || !mark) return;
      const boxes = $$('input[data-check]', sub);
      mark.classList.toggle('is-done', boxes.length > 0 && boxes.every(b => b.checked));
      mark.hidden = boxes.length === 0;
    });
    // tarjetas de semana
    $$('[data-week-progress]').forEach(el => {
      const r = ratio(el.dataset.weekProgress);
      const fill = el.querySelector('span');
      if (fill) fill.style.width = Math.round(r * 100) + '%';
      const lab = document.querySelector(`[data-week-progress-label="${el.dataset.weekProgress}"]`);
      const pc = Math.round(r * 100);
      if (lab) lab.innerHTML = Hub.i18n.html(Hub.i18n.L(`${pc} % completado`, `${pc}% complete`, { fr: `${pc} % terminé`, ca: `${pc} % completat`, ja: `${pc}% 完了` }));
    });
    // anillo global
    const g = ratio(null);
    const ring = $('#global-progress .ring-fill');
    if (ring) ring.setAttribute('stroke-dasharray', `${Math.round(g * 100)} 100`);
    const pct = $('#global-progress [data-progress-pct]');
    if (pct) pct.textContent = Math.round(g * 100) + '%';
  }

  Hub.progress = {
    init() {
      state = Hub.store.get('progress', {});
      document.addEventListener('change', e => {
        const inp = e.target.closest('input[data-check]');
        if (!inp) return;
        Hub.progress.set(inp.dataset.check, inp.checked);
      });
      // marcador de estado en cada enlace del menú lateral
      $$('.week-nav a[data-sub]').forEach(a => { if (!a.querySelector('.nav-done')) a.append(Object.assign(document.createElement('span'), { className: 'nav-done', hidden: true })); });
      paint();
    },
    set(id, value) {
      if (value) state[id] = true; else delete state[id];
      Hub.store.set('progress', state);
      paint();
    },
    get: id => !!state[id],
    ratio,
  };
})();
