/* Deck · presentaciones de clase (P1–P9) con plantilla institucional UTI. Bilingüe: el contenido de cada
 * diapositiva lleva sus bloques lang="es" / lang="en"; data-title-en y data-foot-en dan el título y el pie en inglés.
 *
 *   <div class="deck" data-deck="P1" data-title="…" data-foot="Semana 1 · Tutoría sincrónica">
 *     <section class="slide slide--cover"> … </section>
 *     <section class="slide" data-title="Título corto para el índice">
 *        <h2>…</h2> <p class="fragment">aparece al avanzar</p>
 *        <div class="anim anim-slot" data-anim="A1.3" data-compact></div>
 *        <aside class="notes">Notas del docente…</aside>
 *     </section>
 *   </div>
 *
 * Teclado (con el foco en cualquier parte de la presentación, también en su barra): → / Espacio / AvPág = siguiente ·
 * ← / RePág = anterior · Inicio / Fin · F = pantalla completa · N = notas del docente.
 * Deslizar con el dedo o el lápiz (no con el ratón) cambia de diapositiva, salvo mientras se anota a mano.
 */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { h, $, $$, clamp } = Hub.util;
  const I = Hub.i18n;
  const { L } = I;

  const ICON = {
    prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    full: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.5V4h5.5M20 9.5V4h-5.5M4 14.5V20h5.5M20 14.5V20h-5.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    notes: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14v16H5zM8.5 8.5h7M8.5 12h7M8.5 15.5h4.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
  };

  class Deck {
    constructor(el) {
      this.el = el;
      this.slides = $$(':scope > .slide', el);
      this.i = -1;
      this.frag = 0;
      const total = this.slides.length;
      const logoColor = ($('.brand__logo--light') || {}).src || '';
      const logoWhite = ($('.brand__logo--dark') || {}).src || '';

      this.vp = h('div', { class: 'deck__viewport', tabindex: '0', role: 'region' });
      I.bind(this.vp, 'aria-roledescription', L('presentación', 'presentation'));
      I.bind(this.vp, 'aria-label', L(el.dataset.title || 'Presentación', el.dataset.titleEn || el.dataset.title || 'Presentation'));
      const foot = L(el.dataset.foot || '', el.dataset.footEn || el.dataset.foot || '');
      this.slides.forEach((s, k) => {
        s.setAttribute('role', 'group');
        I.bind(s, 'aria-roledescription', L('diapositiva', 'slide'));
        I.bind(s, 'aria-label', L(`${k + 1} de ${total}`, `${k + 1} of ${total}`, { fr: `${k + 1} sur ${total}`, ca: `${k + 1} de ${total}`, ja: `${k + 1} / ${total}` }));
        if (s.classList.contains('slide--cover') || s.classList.contains('slide--closing')) {
          s.prepend(h('img', { class: 'cover-logo', src: logoWhite, alt: 'Universidad Tecnológica Indoamérica' }));
        } else {
          s.append(h('div', { class: 'slide__foot' }, h('img', { src: logoColor, alt: '' }), h('span', { html: I.html(foot) }), h('span', { class: 'pg' }, `${k + 1} / ${total}`)));
        }
        this.vp.append(s);
      });

      const btn = (icon, label, fn) => {
        const b = h('button', { type: 'button', class: 'tbtn', html: icon });
        I.bind(b, 'aria-label', label);
        I.bind(b, 'title', label);
        b.addEventListener('click', fn);
        return b;
      };
      this.count = h('span', { class: 'deck__count' });
      this.bar = h('span');
      this.jump = h('select', { class: 'deck__jump', id: 'jump-' + (el.dataset.deck || 'deck') },
        this.slides.map((s, k) => h('option', { value: k }, `${k + 1}. ${this.titleOf(s)}`)));
      I.bind(this.jump, 'aria-label', L('Ir a la diapositiva', 'Go to slide'));
      this.jump.addEventListener('change', () => this.show(+this.jump.value));
      Hub.on('lang', () => Array.from(this.jump.options).forEach((o, k) => { o.textContent = `${k + 1}. ${this.titleOf(this.slides[k])}`; }));
      this.notesBody = h('div');
      this.notes = h('div', { class: 'deck__notes', hidden: true }, h('div', { class: 'deck__notes-t', html: I.html(L('Notas del docente', 'Instructor notes')) }), this.notesBody);
      const ctrl = h('div', { class: 'ctrl' }, this.jump);
      const bar = h('div', { class: 'deck__bar' },
        btn(ICON.prev, L('Anterior (←)', 'Previous (←)'), () => this.prev()), this.count, btn(ICON.next, L('Siguiente (→)', 'Next (→)'), () => this.next()),
        h('div', { class: 'deck__progress' }, this.bar), ctrl,
        btn(ICON.notes, L('Notas del docente (N)', 'Instructor notes (N)'), () => this.toggleNotes()),
        btn(ICON.full, L('Pantalla completa (F)', 'Full screen (F)'), () => this.fullscreen()));
      el.replaceChildren(this.vp, bar, this.notes);

      // En todo el deck, no solo en el visor: después de tocar un botón de la barra (siguiente, una herramienta de
      // anotación…) las flechas deben seguir navegando. Espacio/Intro sobre un botón siguen siendo del botón.
      el.addEventListener('keydown', e => {
        if (e.defaultPrevented || e.target.closest('input, select, textarea, .stage')) return;
        const k = e.key;
        if (e.target.closest('button') && (k === ' ' || k === 'Enter')) return;
        if (k === 'ArrowRight' || k === 'PageDown' || k === ' ') { e.preventDefault(); this.next(); }
        else if (k === 'ArrowLeft' || k === 'PageUp') { e.preventDefault(); this.prev(); }
        else if (k === 'Home') { e.preventDefault(); this.show(0); }
        else if (k === 'End') { e.preventDefault(); this.show(total - 1); }
        else if (k === 'f' || k === 'F') this.fullscreen();
        else if (k === 'n' || k === 'N') this.toggleNotes();
      });
      // Deslizar: solo dedo o lápiz, del mismo puntero, y nunca mientras se anota (la palma no debe pasar de diapositiva)
      let sw = null;
      this.vp.addEventListener('pointerdown', e => {
        // tocar la diapositiva (también dibujando, que cancela el foco nativo) deja el teclado en la presentación
        if (!el.contains(document.activeElement) && !e.target.closest('.stage')) this.vp.focus({ preventScroll: true });
        sw = e.pointerType === 'mouse' || e.target.closest('.stage, button') || el.classList.contains('is-inking') ? null : { x: e.clientX, id: e.pointerId };
      });
      this.vp.addEventListener('pointerup', e => {
        if (!sw || e.pointerId !== sw.id) return;
        const dx = e.clientX - sw.x; sw = null;
        if (el.classList.contains('is-inking')) return;
        if (Math.abs(dx) > 60) (dx < 0 ? this.next() : this.prev());
      });
      this.vp.addEventListener('pointercancel', () => { sw = null; });
      this.show(0);
    }

    titleOf(s) {
      if (s.dataset.title) return I.tr({ es: s.dataset.title, en: s.dataset.titleEn || s.dataset.title });
      const t = s.querySelector('h1, h2');
      return t ? I.text(t).slice(0, 60) : I.t('Diapositiva', 'Slide');
    }
    frags() { return $$('.fragment', this.slides[this.i]); }
    next() {
      const fr = this.frags();
      if (this.frag < fr.length) { fr[this.frag].classList.add('is-shown'); this.frag++; this.markPast(fr); return; }
      this.show(this.i + 1);
    }
    prev() {
      const fr = this.frags();
      if (this.frag > 0) { this.frag--; fr[this.frag].classList.remove('is-shown'); this.markPast(fr); return; }
      this.show(this.i - 1, true);
    }
    markPast(fr) { fr.forEach((f, k) => f.classList.toggle('is-past', k < this.frag - 1)); }

    show(i, fromEnd) {
      i = clamp(i, 0, this.slides.length - 1);
      if (i === this.i && !fromEnd) return;
      this.i = i;
      this.slides.forEach((s, k) => {
        const on = k === i;
        s.classList.toggle('is-active', on);
        s.setAttribute('aria-hidden', on ? 'false' : 'true');
        $$('[data-anim]', s).forEach(a => {
          if (on && !a.hasAttribute('data-mounted')) Hub.anim.mount(a);
          if (a._stage) a._stage.setSuspended(!on);
        });
      });
      const fr = this.frags();
      fr.forEach(f => f.classList.toggle('is-shown', !!fromEnd));
      this.frag = fromEnd ? fr.length : 0;
      this.markPast(fr);
      const s = this.slides[i];
      if (Hub.math) Hub.math.render(s);
      this.count.textContent = `${i + 1} / ${this.slides.length}`;
      this.bar.style.width = ((i + 1) / this.slides.length) * 100 + '%';
      this.jump.value = String(i);
      const n = s.querySelector('aside.notes');
      this.notesBody.innerHTML = n ? n.innerHTML : `<p class="muted">${I.html(L('Sin notas para esta diapositiva.', 'No notes for this slide.'))}</p>`;
      Hub.emit('deck:slide', { deck: this, i });       // lo escucha la capa de anotación (80-ink.js)
    }
    toggleNotes() { this.notes.hidden = !this.notes.hidden; }
    fullscreen() {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (this.el.requestFullscreen) this.el.requestFullscreen().then(() => this.vp.focus()).catch(() => {});
    }
  }

  Hub.deck = {
    mountAll(root = document) {
      $$('.deck:not([data-mounted])', root).forEach(el => { el.setAttribute('data-mounted', ''); el._deck = new Deck(el); });
    },
  };
})();
