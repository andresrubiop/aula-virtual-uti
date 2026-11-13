/* Tema claro/oscuro y colores para canvas.
   Hub.colors() lee los tokens de identidad-uti/tokens.css; se recalcula al cambiar el tema
   y se emite Hub.emit('theme') para que cada animación se redibuje. */
(function () {
  'use strict';
  const Hub = window.Hub;
  const root = document.documentElement;
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  let cache = null;

  const TOKENS = {
    bg: '--bg', surface: '--surface', surface2: '--surface-2', surface3: '--surface-3',
    ink: '--ink', ink2: '--ink-2', ink3: '--ink-3', line: '--line', lineStrong: '--line-strong',
    accent: '--accent', accentFill: '--accent-fill', accentTint: '--accent-tint',
    ok: '--ok', warn: '--warn', err: '--err',
    c1: '--c1', c2: '--c2', c3: '--c3', c4: '--c4', neutral: '--c-neutral',
    plotBg: '--plot-bg', grid: '--plot-grid', axis: '--plot-axis', text: '--plot-text', plotInk: '--plot-ink',
    morado: '--uti-morado', naranja: '--uti-naranja', accent2: '--accent-2', accent2Fill: '--accent-2-fill',
  };

  Hub.theme = {
    current() {
      const t = root.getAttribute('data-theme');
      if (t === 'dark' || t === 'light') return t;
      return mq.matches ? 'dark' : 'light';
    },
    set(t) {
      root.setAttribute('data-theme', t);
      try { localStorage.setItem('@@KEY@@:theme', t); } catch (e) { /* nada */ }
      cache = null; slideCache = null;
      Hub.emit('theme', t);
    },
    toggle() { Hub.theme.set(Hub.theme.current() === 'dark' ? 'light' : 'dark'); },
  };

  // Hub.colors(el?) — paleta de tokens. Dentro de una presentación (.deck__viewport) se usa la paleta
  // clara fija de las slides, sin importar el tema del sitio.
  let slideCache = null;
  Hub.colors = function (el) {
    const inSlide = el && el.closest && el.closest('.deck__viewport');
    if (inSlide ? slideCache : cache) return inSlide ? slideCache : cache;
    const cs = getComputedStyle(inSlide || root);
    const pal = {};
    for (const [k, v] of Object.entries(TOKENS)) pal[k] = cs.getPropertyValue(v).trim() || '#888888';
    pal.dark = !inSlide && Hub.theme.current() === 'dark';
    if (inSlide) slideCache = pal; else cache = pal;
    return pal;
  };

  mq.addEventListener('change', () => {
    if (!root.getAttribute('data-theme')) { cache = null; slideCache = null; Hub.emit('theme', Hub.theme.current()); }
  });
})();
