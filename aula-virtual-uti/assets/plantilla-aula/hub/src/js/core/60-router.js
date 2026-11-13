/* Enrutador por hash. Formato: #/<vista>/<subvista>/<ancla>
   Ejemplos: #/inicio · #/u2 · #/u2/animaciones · #/u2/animaciones/anim-A2-1 · #/u2/manual/m2-3
   Los hash que no empiezan con "#/" (p. ej. #main del enlace "saltar") no cambian la vista.
   IMPORTANTE para autores: los enlaces internos SIEMPRE con el formato #/vista/subvista/ancla. */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { $$ } = Hub.util;
  let last = { view: null, sub: null };

  function parse(hash) {
    const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
    return { view: parts[0] || 'inicio', sub: parts[1] || null, anchor: parts[2] || null };
  }

  function apply() {
    const hash = location.hash || '#/inicio';
    if (!hash.startsWith('#/')) return;
    const r = parse(hash);
    const views = $$('main > .view');
    const view = views.find(v => v.dataset.view === r.view) || views.find(v => v.dataset.view === 'inicio');
    if (!view) return;
    views.forEach(v => { v.hidden = v !== view; });

    $$('.main-nav a').forEach(a => {
      if (a.dataset.nav === view.dataset.view) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });

    let sub = null;
    const subs = $$('.sub', view);
    if (!subs.length && r.sub && !r.anchor) r.anchor = r.sub;   // vistas sin subsecciones: #/inicio/ancla
    if (subs.length) {
      sub = subs.find(s => s.dataset.sub === r.sub) || subs[0];
      subs.forEach(s => { s.hidden = s !== sub; });
      $$('.week-nav a', view).forEach(a => a.setAttribute('aria-current', a.dataset.sub === sub.dataset.sub ? 'true' : 'false'));
      const active = view.querySelector('.week-nav a[aria-current="true"]');
      if (active && active.scrollIntoView && window.innerWidth <= 960) active.scrollIntoView({ block: 'nearest', inline: 'center' });
    }

    const changed = last.view !== view.dataset.view || last.sub !== (sub && sub.dataset.sub);
    last = { view: view.dataset.view, sub: sub && sub.dataset.sub };

    const heading = view.dataset.view === 'inicio' ? null : (sub && sub.querySelector('h2')) || view.querySelector('h1');
    const ct = (window.HUB_COURSE || {}).title || {};
    const course = Hub.i18n.t((ct.es || 'Aula interactiva') + ' · UTI', (ct.en || ct.es || 'Interactive classroom') + ' · UTI');
    document.title = (heading ? Hub.i18n.text(heading) + ' · ' : '') + course;

    Hub.emit('route', { view: view.dataset.view, sub: sub && sub.dataset.sub, el: sub || view, anchor: r.anchor });

    if (r.anchor) {
      const el = document.getElementById(r.anchor);
      if (el) requestAnimationFrame(() => el.scrollIntoView({ behavior: Hub.util.reducedMotion() ? 'auto' : 'smooth', block: 'start' }));
    } else if (changed) {
      window.scrollTo({ top: 0, behavior: 'auto' });
    }
  }

  Hub.router = { apply, parse };
  Hub.on('lang', () => { last = { view: null, sub: null }; apply(); });   // título de la pestaña en el nuevo idioma
  window.addEventListener('hashchange', apply);
})();
