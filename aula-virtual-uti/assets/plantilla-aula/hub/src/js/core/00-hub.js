/* Hub · espacio de nombres global, utilidades y bus de eventos.
   Todo el JS del hub se concatena en un solo <script>; cada archivo es un IIFE. */
(function () {
  'use strict';
  const Hub = (window.Hub = window.Hub || {});
  const U = (Hub.util = {});

  U.$ = (sel, root = document) => root.querySelector(sel);
  U.$$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /** Crea un elemento: h('div', {class:'x', onclick: fn, html:'<b>..</b>'}, hijo1, 'texto') */
  U.h = function (tag, attrs, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'html') el.innerHTML = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'style' && typeof v === 'object') {
        for (const [p, x] of Object.entries(v)) { if (p.startsWith('--')) el.style.setProperty(p, x); else el.style[p] = x; }
      }
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return el;
  };

  U.clamp = (x, a, b) => Math.min(b, Math.max(a, x));
  U.lerp = (a, b, t) => a + (b - a) * t;
  U.invlerp = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
  U.ease = {
    linear: t => t,
    in: t => t * t * t,
    out: t => 1 - Math.pow(1 - t, 3),
    inOut: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outBack: t => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2); },
    outQuad: t => 1 - (1 - t) * (1 - t),
  };

  /** Número con decimales fijos (punto decimal, igual que Python). */
  U.fmt = (x, d = 2) => (Number.isFinite(x) ? x.toFixed(d) : '—');
  U.pct = (x, d = 0) => (Number.isFinite(x) ? (x * 100).toFixed(d) + '\u00a0%' : '—');
  U.sign = (x, d = 2) => (x >= 0 ? '+' : '−') + Math.abs(x).toFixed(d);
  /** Dos cifras significativas sin notación científica: 1000 → "1000", 0.031 → "0.031". */
  U.sig = (x, d = 2) => (Number.isFinite(x) ? String(+x.toPrecision(d)) : '—');

  /** Escala lineal: s = U.scale(d0, d1, r0, r1); s(x); s.inv(y) */
  U.scale = function (d0, d1, r0, r1) {
    const f = x => r0 + ((x - d0) / (d1 - d0)) * (r1 - r0);
    f.inv = y => d0 + ((y - r0) / (r1 - r0)) * (d1 - d0);
    f.domain = [d0, d1];
    f.range = [r0, r1];
    return f;
  };

  /** Marcas "bonitas" para ejes. */
  U.ticks = function (a, b, n = 5) {
    const span = Math.abs(b - a) || 1;
    const step0 = Math.pow(10, Math.floor(Math.log10(span / n)));
    const err = (span / n) / step0;
    const step = step0 * (err >= 7.5 ? 10 : err >= 3.5 ? 5 : err >= 1.5 ? 2 : 1);
    const out = [];
    for (let v = Math.ceil(Math.min(a, b) / step) * step; v <= Math.max(a, b) + step * 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  };

  U.mean = arr => arr.reduce((s, x) => s + x, 0) / (arr.length || 1);
  U.std = arr => { const m = U.mean(arr); return Math.sqrt(U.mean(arr.map(x => (x - m) * (x - m)))); };
  U.sigmoid = z => 1 / (1 + Math.exp(-z));
  U.range = (n, f = i => i) => Array.from({ length: n }, (_, i) => f(i));

  U.reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  U.debounce = (fn, ms = 120) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  U.escape = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // Bus de eventos mínimo: Hub.on('theme', fn) · Hub.emit('theme', datos)
  const listeners = {};
  Hub.on = (ev, fn) => { (listeners[ev] = listeners[ev] || []).push(fn); };
  Hub.emit = (ev, data) => (listeners[ev] || []).slice().forEach(fn => {
    try { fn(data); } catch (e) { console.error('[Hub] error en evento', ev, e); }
  });
})();
