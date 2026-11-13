/* Widgets pequeños: cuenta regresiva, paginador de secciones, código (C, bash, Python), fórmulas y glosario. */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { h, $, $$ } = Hub.util;
  const I = Hub.i18n;
  const { L } = I;

  /* ---------- Cuenta regresiva al próximo hito (Hub.course.deadlines) ---------- */
  Hub.countdown = {
    init() {
      const els = $$('[data-countdown]');
      if (!els.length) return;
      const tick = () => {
        const now = new Date();
        const nx = Hub.course.next(now);
        els.forEach(el => {
          if (!nx) {
            el.innerHTML = `<div class="next-up"><span class="next-up__label">${I.html(L('Calendario', 'Calendar'))}</span>
              <span class="next-up__title">${I.html(Hub.course.deadlines.length
                ? L('El período académico terminó.', 'The academic term is over.')
                : L('Fechas del período por confirmar con el sílabo.', 'Term dates to be confirmed with the syllabus.'))}</span></div>`;
            return;
          }
          const ms = nx.when - now;
          const d = Math.floor(ms / 864e5), hh = Math.floor((ms % 864e5) / 36e5), mm = Math.floor((ms % 36e5) / 6e4);
          const date = loc => nx.when.toLocaleDateString(loc, { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'America/Guayaquil' });
          const hour = loc => nx.when.toLocaleTimeString(loc, { hour: '2-digit', minute: '2-digit', timeZone: 'America/Guayaquil' });
          const tbc = nx.time === false;
          const when = L(`${date('es-EC')} · ${tbc ? 'hora por confirmar' : hour('es-EC') + ' (hora de Ecuador)'}`,
            `${date('en-US')} · ${tbc ? 'time to be confirmed' : hour('en-US') + ' (Ecuador time)'}`,
            { fr: `${date('fr-FR')} · ${tbc ? 'heure à confirmer' : hour('fr-FR') + ' (heure de l’Équateur)'}`,
              ca: `${date('ca-ES')} · ${tbc ? 'hora per confirmar' : hour('ca-ES') + ' (hora de l’Equador)'}`,
              ja: `${date('ja-JP')} · ${tbc ? '時刻未定' : hour('ja-JP') + '（エクアドル時間）'}` });
          el.innerHTML = `
            <div class="next-up">
              <span class="next-up__label">${I.html(L('Próximo hito', 'Next milestone'))}</span>
              <span class="next-up__title">${I.html(nx.label)}</span>
              <span class="next-up__more">${I.html(when)}</span>
              <div class="next-up__count">
                <div><strong>${d}</strong><span>${I.html(L('días', 'days'))}</span></div>
                <div><strong>${hh}</strong><span>${I.html(L('horas', 'hours'))}</span></div>
                <div><strong>${mm}</strong><span>min</span></div>
              </div>
              <a class="btn btn--sm next-up__go" href="${nx.href}">${I.html(L('Ir a la actividad', 'Go to the activity'))}</a>
            </div>`;
        });
      };
      tick();
      setInterval(tick, 30000);
    },
  };

  /* ---------- Paginador "anterior / siguiente sección" de cada unidad ---------- */
  Hub.pager = {
    init() {
      $$('.view').forEach(view => {
        const links = $$('.week-nav a[data-sub]', view);
        links.forEach((a, i) => {
          const sub = view.querySelector(`.sub[data-sub="${a.dataset.sub}"]`);
          if (!sub || sub.querySelector('.pager')) return;
          const prev = links[i - 1], next = links[i + 1];
          // el texto del enlace ya es bilingüe: se copia su contenido (sin el número ni la marca de avance)
          const label = el => {
            const c = el.cloneNode(true);
            c.querySelectorAll('svg, .nav-done, .week-nav__n').forEach(n => n.remove());
            return h('span', { html: c.innerHTML });
          };
          const nav = h('nav', { class: 'pager' },
            prev ? h('a', { href: prev.getAttribute('href') }, h('small', { html: I.html(L('← Anterior', '← Previous')) }), label(prev)) : null,
            next ? h('a', { href: next.getAttribute('href'), class: 'pager__next' }, h('small', { html: I.html(L('Siguiente →', 'Next →')) }), label(next)) : null);
          I.bind(nav, 'aria-label', L('Navegación entre secciones', 'Section navigation'));
          sub.append(nav);
        });
      });
    },
  };

  /* ---------- Bloques de código con resaltado mínimo y botón copiar ---------- */
  const KW = {
    python: /\b(def|return|import|from|as|for|in|if|elif|else|while|class|with|try|except|finally|lambda|None|True|False|and|or|not|is|pass|break|continue|yield|raise|assert|print)\b/g,
    c: /\b(int|char|long|short|unsigned|signed|void|float|double|const|static|volatile|struct|union|enum|typedef|sizeof|return|if|else|for|while|do|switch|case|default|break|continue|goto|extern|NULL|ssize_t|size_t|pid_t|off_t|mode_t|uid_t|key_t|sig_atomic_t|pthread_t|pthread_mutex_t|sem_t|sigset_t|bool)\b/g,
    bash: /\b(if|then|else|fi|for|do|done|while|case|esac|in|echo|export|cd|make|gcc|kill|wait|sleep|sudo)\b/g,
  };
  const LABEL = { python: 'Python', c: 'C', bash: 'Bash', sh: 'Shell', text: L('Texto', 'Text'), diagram: L('Diagrama', 'Diagram'), out: L('Salida real', 'Real output'), prompt: 'Prompt' };

  function highlight(esc, lang) {
    const store = [];
    const keep = (cls, s) => { store.push(`<span class="tok-${cls}">${s}</span>`); return '' + String.fromCharCode(0xE100 + store.length - 1) + ''; };
    let out = esc;
    if (lang === 'c') {
      out = out
        .replace(/(\/\*[\s\S]*?\*\/|\/\/[^\n]*)/g, m => keep('c', m))
        .replace(/(&quot;(?:[^&\n]|&(?!quot;))*?&quot;|'(?:\\.|[^'\\\n])')/g, m => keep('s', m))
        .replace(/^(\s*#\s*\w+)/gm, m => keep('k', m));
    } else if (lang === 'bash' || lang === 'sh') {
      out = out
        .replace(/(^|\s)(#[^\n]*)/g, (m, a, b) => a + keep('c', b))
        .replace(/(&quot;[^\n]*?&quot;|'[^'\n]*')/g, m => keep('s', m))
        .replace(/^(\$ )/gm, m => keep('k', m));
    } else {
      out = out
        .replace(/(&quot;&quot;&quot;[\s\S]*?&quot;&quot;&quot;|&quot;[^\n]*?&quot;|'[^'\n]*')/g, m => keep('s', m))
        .replace(/(#[^\n]*)/g, m => keep('c', m));
    }
    out = out
      .replace(/\b(0x[0-9a-fA-F]+|\d+\.?\d*(e-?\d+)?)\b/g, m => keep('n', m))
      .replace(/\b([A-Za-z_]\w*)(?=\()/g, m => keep('f', m));
    if (KW[lang]) out = out.replace(KW[lang], m => keep('k', m));
    for (let k = 0; k < 4 && out.includes(''); k++) out = out.replace(/([\s\S])/g, (_, ch) => store[ch.charCodeAt(0) - 0xE100]);
    return out;
  }

  Hub.code = {
    init(root = document) {
      $$('pre > code[class*="lang-"]', root).forEach(code => {
        const pre = code.parentElement;
        if (pre.parentElement.classList.contains('code')) return;
        const lang = (code.className.match(/lang-(\w+)/) || [])[1] || 'code';
        const src = code.textContent.replace(/^\n+|\s+$/g, '');
        if (KW[lang] || lang === 'sh') code.innerHTML = highlight(Hub.util.escape(src), lang);
        else code.textContent = src;
        const copy = h('button', { type: 'button', class: 'code__copy', html: I.html(L('Copiar', 'Copy')) });
        copy.addEventListener('click', () => {
          const done = () => { copy.innerHTML = I.html(L('Copiado ✓', 'Copied ✓')); setTimeout(() => { copy.innerHTML = I.html(L('Copiar', 'Copy')); }, 1600); };
          const fail = () => { copy.innerHTML = I.html(L('Selecciona y copia', 'Select and copy')); };
          if (navigator.clipboard) navigator.clipboard.writeText(src).then(done, fail); else fail();
        });
        const file = pre.dataset.file ? h('span', { class: 'code__file' }, pre.dataset.file) : null;
        const lab = LABEL[lang] || lang;
        // code--long: no cabe en una página A4; al imprimir puede partirse (los cortos se mantienen enteros)
        const long = src.split('\n').length > 45;
        const wrap = h('div', { class: 'code' + (lang === 'out' || lang === 'text' ? ' code--out' : '') + (long ? ' code--long' : '') },
          h('div', { class: 'code__bar' }, h('span', { html: I.html(lab) }), file, h('span', { class: 'grow' }), copy));
        // <pre lang="es|en">: el idioma pasa al envoltorio para que se oculte también la barra
        if (pre.lang) {
          wrap.lang = pre.lang; pre.removeAttribute('lang');
          // la marca de traducciones (fr/ca/ja) viaja también: sin ella el inglés se vería junto a la traducción
          if (pre.dataset.tr != null) { wrap.dataset.tr = pre.dataset.tr; delete pre.dataset.tr; }
        }
        pre.replaceWith(wrap);
        wrap.append(pre);
      });
    },
  };

  /* ---------- Fórmulas (KaTeX) bajo demanda: \( … \) en línea, \[ … \] o $$ … $$ en bloque ---------- */
  Hub.math = {
    render(el, force) {
      if (!el || !window.renderMathInElement) return;
      if (el.hasAttribute('data-math-done') && !force) return;
      el.setAttribute('data-math-done', '');
      try {
        window.renderMathInElement(el, {
          delimiters: [
            { left: '$$', right: '$$', display: true },
            { left: '\\[', right: '\\]', display: true },
            { left: '\\(', right: '\\)', display: false },
          ],
          ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'canvas'],
          throwOnError: false,
          strict: 'ignore',
        });
      } catch (e) { console.error('[math]', e); }
    },
  };

  /* ---------- Glosario: filtro por texto (busca en los dos idiomas) ---------- */
  Hub.glossary = {
    init() {
      const input = $('#gloss-search');
      if (!input) return;
      I.bind(input, 'placeholder', L('Buscar un término…', 'Search a term…'));
      const items = $$('.gloss__item');
      const norm = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
      const count = () => {
        const q = norm(input.value.trim());
        let n = 0;
        items.forEach(it => { const on = !q || norm(it.textContent).includes(q); it.hidden = !on; n += on; });
        const out = $('#gloss-count');
        if (out) out.innerHTML = I.html(L(`${n} término${n === 1 ? '' : 's'}`, `${n} term${n === 1 ? '' : 's'}`,
          { fr: `${n} terme${n > 1 ? 's' : ''}`, ca: `${n} terme${n === 1 ? '' : 's'}`, ja: `${n} 件の用語` }));
      };
      input.addEventListener('input', count);
      count();
    },
  };
})();
