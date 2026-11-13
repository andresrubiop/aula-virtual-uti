/* Idiomas del aula: español (por defecto) e inglés.
 *
 * El contenido se escribe en los dos idiomas, uno al lado del otro:
 *   <span lang="es">…</span><span lang="en">…</span>  ·  <div lang="es">…</div><div lang="en">…</div>
 * El CSS (10-base.css) oculta el idioma inactivo: cambiar de idioma no reconstruye nada ni pierde estado.
 * JavaScript:
 *   L(es, en)        → {es, en}: texto bilingüe para el DOM
 *   t(es, en)        → cadena en el idioma ACTUAL (canvas, atributos); redibuja al recibir Hub.on('lang')
 *   tr(x)            → x si es cadena; x[idioma] si es {es, en}
 *   html(x, tag)     → HTML con los dos idiomas (<span lang="es">…</span><span lang="en">…</span>)
 *   node(x, tag)     → lo mismo, como nodo del DOM
 *   bind(el, attr, x)→ fija un atributo ('title', 'aria-label', 'placeholder' o 'text') y lo actualiza al cambiar
 *   text(el)         → texto visible de un elemento bilingüe (solo el idioma que se ve)
 *   locale(l?)       → es-EC o en-US (para toLocaleString) · comma: ¿coma decimal?
 *   num(x, d, l?)    → cifra con el formato del idioma l: en cada versión de una narración, el suyo
 * El idioma se elige en la cabecera (ES / EN), se recuerda en el navegador y ?lang=en lo fuerza.
 * (El motor conserva el soporte de idiomas extra por memoria de traducción —EXTRA, HUB_I18N—, apagado aquí.)
 */
(function () {
  'use strict';
  const Hub = window.Hub;
  const root = document.documentElement;
  const KEY = '@@KEY@@:lang';
  const LANGS = ['es', 'en'];      // el aula UTI es bilingüe: español e inglés
  const EXTRA = [];                // idiomas extra por memoria de traducción (no se usan en esta plantilla)
  const LOCALE = { es: 'es-EC', en: 'en-US', fr: 'fr-FR', ca: 'ca-ES', ja: 'ja-JP' };
  const DICT = window.HUB_I18N || {};
  const missing = new Set();

  function initial() {
    try {
      const q = new URLSearchParams(location.search).get('lang');
      if (LANGS.includes(q)) return q;
    } catch (e) { /* nada */ }
    try {
      const s = localStorage.getItem(KEY);
      if (LANGS.includes(s)) return s;
    } catch (e) { /* nada */ }
    return 'es';
  }

  let cur = initial();
  const bound = new Set();

  const norm = s => String(s).replace(/\s+/g, ' ').trim();
  const isPair = x => x != null && typeof x === 'object' && !Array.isArray(x) && ('es' in x || 'en' in x);

  /* Plantillas de la memoria (window.HUB_I18N_T, de las entradas .tr con {1}, {2}…): traducen cadenas con variables
     ("read dir 12: "home" → inode 15") sin tocar el código. Cada {n} se reconoce en el texto inglés y se copia a la
     traducción; si el valor es a su vez un texto de la memoria, se traduce, y si es una cifra en formato inglés
     (1,234.5) toma el formato del idioma. */
  const TPL = (window.HUB_I18N_T || []).map(([key, tr]) => {
    const parts = key.split(/\{(\d+)\}/);                    // literal, n, literal, n, …
    const lits = parts.filter((_, i) => i % 2 === 0);
    // un valor pegado al siguiente ({4}{5}: «3» + « (append)») toma una sola palabra; si no, el perezoso lo dejaría vacío
    const re = new RegExp('^' + parts.map((p, i) => (i % 2 ? (parts[i + 1] === '' && i + 2 < parts.length ? '(\\S*)' : '([\\s\\S]*?)')
      : p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))).join('') + '$');
    const longest = lits.reduce((a, b) => (b.length > a.length ? b : a), '');
    return { re, nums: parts.filter((_, i) => i % 2).map(Number), tr, longest };
  });
  const tcache = new Map();
  // Una cifra en formato inglés (1,234.5) con el formato del idioma l; f = decimales que traía
  const renum = (n, l) => {
    const f = (n.split('.')[1] || '').length;
    return Number(n.replace(/,/g, '')).toLocaleString(LOCALE[l], { minimumFractionDigits: f, maximumFractionDigits: f, useGrouping: n.includes(',') });
  };
  function fmtCapture(v, l, depth) {
    const lead = v.match(/^\s*/)[0], trail = v.match(/\s*$/)[0], t = v.trim();
    if (!t) return v;
    const d = depth < 3 ? lookup(t, depth + 1) : DICT[norm(t)];        // un texto de la memoria (o de otra plantilla)
    if (d && d[l] != null) return (l === 'ja' ? '' : lead) + d[l] + trail;   // japonés: sin el espacio inglés entre frases
    // cifra suelta o con unidad: 0.7 · 8,388,609 · 1.5 MiB · 6.50 s · 25.6 million (no toca versiones como 7.0.1)
    const m = /^(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d+|-?\d+)(\s*[A-Za-zµ%/]+(?:\/s)?)?$/.exec(t);
    if (m && /[.,]/.test(m[1])) return lead + renum(m[1], l) + (m[2] || '') + trail;
    // varias cifras con operadores (26,622 + 23,037 + …): cada una con el formato del idioma
    if (/^[-−\d.,\s+×=]+$/.test(t) && /\d,\d{3}|\d\.\d/.test(t)) return lead + t.replace(/\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+/g, n => renum(n, l)) + trail;
    return v;
  }
  /** {fr, ca, ja} para un texto inglés: entrada exacta de la memoria o, si no, una plantilla que encaje. */
  function lookup(en, depth = 0) {
    const k = norm(en);
    if (DICT[k]) return DICT[k];
    if (!TPL.length || !k) return null;
    if (tcache.has(k)) return tcache.get(k);
    let out = null;
    for (const t of TPL) {
      if (t.longest && !k.includes(t.longest)) continue;
      const m = t.re.exec(k);
      if (!m) continue;
      out = {};
      for (const l of EXTRA) {
        if (t.tr[l] == null) continue;
        out[l] = t.tr[l].replace(/\{(\d+)\}/g, (_, n) => { const i = t.nums.indexOf(+n); return i < 0 ? '' : fmtCapture(m[i + 1], l, depth); });
      }
      break;
    }
    if (tcache.size > 5000) tcache.clear();          // textos con cifras que cambian en cada cuadro
    tcache.set(k, out);
    return out;
  }
  /** Completa fr/ca/ja desde la memoria de traducción (sin tocar los que ya trae). */
  function full(x) {
    if (!isPair(x) || x.en == null) return x;
    const d = lookup(x.en);
    if (!d) return x;
    let out = x;
    for (const l of EXTRA) if (out[l] == null && d[l] != null) { if (out === x) out = { ...x }; out[l] = d[l]; }
    return out;
  }
  function pick(x, l) {
    if (x[l] != null) return x[l];
    if (x.en != null) {
      const d = lookup(x.en);
      if (d && d[l] != null) return d[l];
      if (l === cur && l !== 'en' && l !== 'es' && x.es !== x.en && norm(x.en)) missing.add(norm(x.en));   // solo lo que se ve en inglés ahora (igual en es y en = neutro: código, nombres)
      return x.en;
    }
    return x.es;
  }
  const tr = x => (isPair(x) ? (cur === 'es' && x.es != null ? x.es : pick(x, cur)) : x);
  const L = (es, en, o) => full(o ? { es, en, ...o } : { es, en });

  /** ¿Se ve este bloque con lang en el idioma activo? (el inglés se ve si falta la traducción) */
  function shows(el) {
    const l = el.getAttribute('lang');
    if (l === cur) return true;
    return l === 'en' && EXTRA.includes(cur) && !(el.dataset.tr || '').split(' ').includes(cur);
  }

  function apply() {
    root.lang = cur;
    root.setAttribute('data-lang', cur);
  }

  function setAttr(el, attr, value) {
    if (attr === 'text') el.textContent = value;
    else el.setAttribute(attr, value);
  }
  // Atributos multilingües escritos en el HTML: data-i18n='{"title": ["es", "en"]}' (fr/ca/ja: de la memoria,
  // o en un tercer elemento {"fr": …, "ca": …, "ja": …} si el texto lleva números que cambian)
  function attrs(el) {
    for (const [attr, p] of Object.entries(JSON.parse(el.dataset.i18n))) setAttr(el, attr, tr({ es: p[0], en: p[1], ...(p[2] || {}) }));
  }

  Hub.i18n = {
    get lang() { return cur; },
    LANGS,
    EXTRA,
    missing,
    L,
    t: (es, en, o) => tr(L(es, en, o)),
    tr,
    isPair,
    /** {es, en, fr, ca, ja} con todos los idiomas resueltos (respaldo inglés): para componer cadenas con variables. */
    all(x) {
      if (!isPair(x)) return Object.fromEntries(LANGS.map(l => [l, x == null ? '' : String(x)]));
      return Object.fromEntries(LANGS.map(l => [l, l === 'es' ? (x.es != null ? x.es : x.en) : pick(x, l)]));
    },
    shows,
    locale: (l = cur) => LOCALE[l],
    /** Cifra con el formato de un idioma CONCRETO (por omisión el activo): en una narración L(es, en, {fr…}) cada
     *  versión usa el suyo, así el texto es correcto aunque se haya evaluado con otro idioma activo.
     *  d = decimales fijos (sin d: hasta 1 decimal) · grupos de miles solo con group: true */
    num(x, d, l = cur, group = false) {
      const o = d == null ? { maximumFractionDigits: 1 } : { minimumFractionDigits: d, maximumFractionDigits: d };
      return Number(x).toLocaleString(LOCALE[l], { ...o, useGrouping: group });
    },
    get comma() { return cur === 'es' || cur === 'fr' || cur === 'ca'; },
    html(x, tag = 'span') {
      if (!isPair(x)) return x == null ? '' : String(x);
      x = full(x);
      // igual en español e inglés y sin otras traducciones (cifras, código): un solo texto, sin marca de idioma
      if (x.es === x.en && !EXTRA.some(l => x[l] != null && x[l] !== x.en)) return x.en == null ? '' : String(x.en);
      const has = EXTRA.filter(l => x[l] != null);
      // lo que se verá en inglés en el idioma activo (pruebas: también lo que pasa por html, como las narraciones)
      if (EXTRA.includes(cur) && x[cur] == null && x.en != null && norm(x.en)) missing.add(norm(x.en));
      let s = `<${tag} lang="es">${x.es != null ? x.es : x.en}</${tag}><${tag} lang="en"${has.length ? ` data-tr="${has.join(' ')}"` : ''}>${x.en != null ? x.en : x.es}</${tag}>`;
      for (const l of has) s += `<${tag} lang="${l}">${x[l]}</${tag}>`;
      return s;
    },
    node(x, tag = 'span') {
      if (!isPair(x)) return document.createTextNode(x == null ? '' : String(x));
      const t = document.createElement('template');
      t.innerHTML = Hub.i18n.html(x, tag);
      return t.content;
    },
    bind(el, attr, x) {
      setAttr(el, attr, tr(x));
      if (isPair(x)) bound.add({ ref: new WeakRef(el), attr, x });
      return el;
    },
    text(el) {
      if (!el) return '';
      const c = el.cloneNode(true);
      c.querySelectorAll('[lang]').forEach(n => { if (LANGS.includes(n.getAttribute('lang')) && !shows(n)) n.remove(); });
      return c.textContent.replace(/\s+/g, ' ').trim();
    },
    set(l) {
      if (!LANGS.includes(l) || l === cur) return;
      cur = l;
      apply();
      try { localStorage.setItem(KEY, l); } catch (e) { /* sin persistencia */ }
      for (const b of bound) {
        const el = b.ref.deref();
        if (!el) bound.delete(b);
        else setAttr(el, b.attr, tr(b.x));
      }
      document.querySelectorAll('[data-i18n]').forEach(el => { try { attrs(el); } catch (e) { /* nada */ } });
      Hub.emit('lang', l);
    },
    /** Pasa al siguiente idioma (ES → EN → FR → CA → JA → ES). */
    toggle() { Hub.i18n.set(LANGS[(LANGS.indexOf(cur) + 1) % LANGS.length]); },
    /** Aplica los data-i18n del HTML una vez al arrancar. */
    init() {
      document.querySelectorAll('[data-i18n]').forEach(el => {
        try { attrs(el); } catch (e) { console.warn('[i18n] data-i18n inválido', el); }
      });
    },
  };
  apply();
})();
