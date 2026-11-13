/* Stage · escenario de animaciones explicativas (contrato completo en AGENTS.md §5).
 * Bilingüe: toda cadena visible (title, subtitle, labels, scenes, observe, narración, métricas, tip, badge)
 * puede ser {es, en} (Hub.i18n.L / api.L). Los textos que se DIBUJAN en el lienzo usan api.t(es, en) y se
 * redibujan solos al cambiar de idioma.
 *
 *   <div class="anim" data-anim="A1.3"></div>            ← en el contenido
 *   <div class="anim" data-anim="A1.3" data-compact data-aspect="2.6" data-scene="3"></div>
 *        ← versión compacta (slides): sin narración, proporción y escena inicial opcionales
 *   data-mode="corrido"  ← modo con que arranca (por omisión, guia)
 *   data-print="3:6"  ← en el PDF de la presentación, la foto de quien la deja correr desde el inicio hasta llevar
 *                        6 s en la escena 3 (Stage.still: tiempo simulado, determinista; por defecto 0:0)
 *
 *   Hub.anim.define({
 *     id, title, subtitle, theory:{label,href}, practice:{label,href}, alt,
 *     aspect: 16/9, aspectNarrow: 4/3, autoplay: true, loop: false, wide: false (lienzo a todo el ancho),
 *     controls: [{id,type:'range'|'toggle'|'select'|'button'|'text',label,min,max,step,value,options,format,placeholder}],
 *     presets: botones «Simular:». Por omisión, una por escena (casi siempre cada escena es una configuración con nombre:
 *              FCFS, SJF, Round Robin…). O bien una lista de {label, params, scene, run} y/o ids de un control select
 *              (un botón por opción). run: true = recorrer las escenas con esa opción; si no, se queda en la escena.
 *     presetBase: {id: valor} que se aplica antes de cada preset · stepSecs: lo que avanza «⏭ paso» (0.5 s)
 *                             compact: false → el control se oculta dentro de las presentaciones (las escenas lo siguen fijando)
 *     scenes: [{title, text: html | (S, api) => html, dur?: seg, params?: {id: valor}}],
 *     observe: ['…'],
 *     init(S, api)            → crea el estado S
 *     layout(S, api)          → recalcula geometría al cambiar el tamaño (api.w, api.h)
 *     scene(S, i, api, user)  → al entrar en la escena i
 *     tick(S, dt, api)        → avanza la simulación (dt en segundos × velocidad), solo en reproducción
 *     draw(S, g, api)         → dibuja (se llama cuando hay cambios)
 *     control(S, id, v, api)  → al mover un control
 *     pointer(S, ev, api)     → ev = {type:'down'|'move'|'up'|'leave', x, y}; devolver true para capturar
 *     lang(S, api)            → al cambiar de idioma, si el estado depende de él (p. ej. peticiones de ejemplo al micro-LLM)
 *
 *   Modos (barra de la animación; los tres para todas):
 *     guia    · Recorrido guiado (el de entrada): escenas en orden, a 0,5×, y al terminar cada una se detiene con su
 *               nota y «Siguiente paso». En las diapositivas la nota se ve como subtítulo sobre el lienzo.
 *     corrido · De corrido: todas las escenas seguidas a 1×.
 *     libre   · Libre: no pasa sola de escena; «⏭ paso» avanza un poco la simulación; los botones «Simular:» y los
 *               controles lanzan cada variante.
 *   api.still = true mientras es una foto de Stage.still: no mostrar mediciones del reloj del navegador (no son reproducibles)
 *   });
 */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { h, $$, clamp } = Hub.util;
  const I = Hub.i18n;
  const { L } = I;
  const registry = new Map();
  const instances = [];
  let uid = 0;

  const ICON = {
    play: '<svg class="i-play" viewBox="0 0 24 24" aria-hidden="true"><path d="M7.5 4.8v14.4L19.5 12z"/></svg><svg class="i-pause" viewBox="0 0 24 24" aria-hidden="true"><path d="M6.5 4.5h4v15h-4zM13.5 4.5h4v15h-4z"/></svg>',
    prev: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.5 5h2.6v14H5.5zM19.5 5v14L9.6 12z"/></svg>',
    next: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15.9 5h2.6v14h-2.6zM4.5 5v14l9.9-7z"/></svg>',
    reset: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4.5a7.5 7.5 0 1 1-7.1 5.1" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M3.2 3.6l.9 6.4 6.3-1.3z"/></svg>',
    full: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9.5V4h5.5M20 9.5V4h-5.5M4 14.5V20h5.5M20 14.5V20h-5.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
    eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    step: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 5v14l9-7z"/><path d="M16.5 5h2.6v14h-2.6z"/></svg>',
  };

  Hub.anim = {
    define(spec) {
      if (registry.has(spec.id)) console.warn('[Stage] id de animación duplicado:', spec.id);
      registry.set(spec.id, spec);
    },
    get: id => registry.get(id),
    ids: () => Array.from(registry.keys()),
    instances,
    // Las animaciones dentro de una presentación las monta el Deck cuando su slide se muestra.
    mountAll(root = document) { $$('[data-anim]:not([data-mounted])', root).filter(el => !el.closest('.slide')).forEach(el => Hub.anim.mount(el)); },
    mount(el) {
      el.setAttribute('data-mounted', '');
      const spec = registry.get(el.dataset.anim);
      if (!spec) {
        // Aún no implementada: se muestra su ficha (data-title / data-desc) hasta que exista la spec.
        el.id = 'anim-' + el.dataset.anim.replace(/\./g, '-');   // el índice de la semana ya puede enlazarla
        // data-title / data-desc (español) y data-title-en / data-desc-en (inglés)
        const pair = k => ({ es: el.dataset[k] || '', en: el.dataset[k + 'En'] || el.dataset[k] || '' });
        const t = el.dataset.title ? ' · ' + I.html({ es: Hub.util.escape(pair('title').es), en: Hub.util.escape(pair('title').en) }) : '';
        const d = el.dataset.desc ? `<br>${I.html(pair('desc'))}` : '';
        el.innerHTML = `<div class="pending"><div><strong><code>${Hub.util.escape(el.dataset.anim)}</code>${t}</strong> <span class="status status--planificado">${I.html(L('animación planificada', 'planned animation'))}</span>${d}</div></div>`;
        return null;
      }
      const st = new Stage(el, spec, { compact: el.hasAttribute('data-compact') });
      instances.push(st);
      el._stage = st;
      return st;
    },
  };

  function tbtn(cls, icon, label, onClick) {
    const b = h('button', { type: 'button', class: cls, html: icon });
    I.bind(b, 'aria-label', label);
    I.bind(b, 'title', label);
    b.addEventListener('click', onClick);
    return b;
  }

  class Stage {
    constructor(host, spec, opt) {
      this.spec = spec;
      this.host = host;
      this.compact = !!opt.compact;
      this.uid = ++uid;
      this.speed = 1;
      this.mode = ['guia', 'corrido', 'libre'].includes(host.dataset.mode) ? host.dataset.mode : 'guia';
      this.notas = true;            // subtítulos del recorrido guiado (se pueden cerrar)
      this.playing = false;
      this.visible = false;
      this.suspended = false;
      this.started = false;
      this.scene = -1;
      this.sceneT = 0;
      this.seen = new Set();
      this.timers = [];
      this.tweens = [];
      this.t = 0;
      this.params = {};
      this.ctlSetters = {};
      for (const c of spec.controls || []) if (c.value !== undefined) this.params[c.id] = c.value;
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.w = 0; this.h = 0;
      this.frame = this.frame.bind(this);
      this.build();
      this.api = makeApi(this);
      this.S = {};
      // init (a veces costoso: entrena modelos) se difiere hasta que la animación se acerca a la pantalla.
      this.booted = false;
      this.resize(true);
      this.pause();
      this.observe();
    }

    boot() {
      if (this.booted) return;
      this.booted = true;
      this.safe('init', () => this.spec.init && this.spec.init(this.S, this.api));
      this.resize(true);
      this.go(+this.host.dataset.scene || 0, false);
    }

    /* ---------- construcción del DOM ---------- */
    build() {
      const s = this.spec;
      const slug = s.id.replace(/\./g, '-');
      this.root = h('figure', {
        class: 'stage' + (this.compact ? ' stage--compact' : '') + (s.wide && !this.compact ? ' stage--wide' : ''),
        id: this.compact ? null : 'anim-' + slug,
        tabindex: '0',
      });
      const tt = I.isPair(s.title) ? s.title : { es: s.title, en: s.title };
      const T = I.all(tt);
      I.bind(this.root, 'aria-label', L(`Animación ${s.id}: ${T.es}`, `Animation ${s.id}: ${T.en}`,
        { fr: `Animation ${s.id} : ${T.fr}`, ca: `Animació ${s.id}: ${T.ca}`, ja: `アニメーション ${s.id}：${T.ja}` }));

      let head = null;
      if (!this.compact) {
        const links = h('div', { class: 'stage__links' },
          s.theory ? h('a', { href: s.theory.href, html: I.html(L('Teoría', 'Theory')) + ' · ' + I.html(s.theory.label) }) : null,
          s.practice ? h('a', { href: s.practice.href, class: 'to-practice', html: I.html(L('Practica', 'Practice')) + ' · ' + I.html(s.practice.label) }) : null);
        head = h('div', { class: 'stage__head' },
          h('div', { class: 'stage__titles' },
            h('div', { class: 'stage__titleline' }, h('span', { class: 'chip chip--id' }, s.id), h('h3', { class: 'stage__title', html: I.html(s.title) })),
            s.subtitle ? h('p', { class: 'stage__sub', html: I.html(s.subtitle) }) : null),
          links);
      }

      this.canvas = I.bind(h('canvas', { role: 'img' }), 'aria-label', s.alt || s.title);
      this.tipEl = h('div', { class: 'stage__tip' });
      this.badgeEl = h('div', { class: 'stage__badge', hidden: true });
      this.pausedEl = h('div', { class: 'stage__paused', html: I.html(L('En pausa', 'Paused')) });
      // Recorrido guiado: subtítulo con la nota de cada paso (diapositivas) y tarjeta al terminar cada paso
      this.capTitle = h('div', { class: 'stage__cap-t' });
      this.capBody = h('div', { class: 'stage__cap-b' });
      const capX = tbtn('stage__cap-x', '×', L('Ocultar las notas (vuelven al elegir «Recorrido guiado»)', 'Hide the notes (they come back when you choose «Guided tour»)'), () => { this.notas = false; this.syncCaption(); });
      this.capEl = h('div', { class: 'stage__cap', hidden: true }, capX, this.capTitle, this.capBody);
      this.cardEl = h('div', { class: 'stage__card', hidden: true, role: 'status' });
      this.viz = h('div', { class: 'stage__viz' }, this.canvas, h('div', { class: 'stage__overlay' }, this.tipEl), this.badgeEl, this.pausedEl, this.capEl, this.cardEl);

      this.sceneBtns = (s.scenes || []).map((sc, i) => {
        const b = h('button', { type: 'button', class: 'stage__scene' },
          h('span', { class: 'stage__scene-n' }, String(i + 1)), h('span', { html: I.html(sc.title) }));
        b.addEventListener('click', () => this.go(i, true));
        return b;
      });
      const scenesEl = I.bind(h('ol', { class: 'stage__scenes' }, this.sceneBtns.map(b => h('li', {}, b))), 'aria-label', L('Escenas de la animación', 'Scenes of the animation'));
      this.narrTitle = h('div', { class: 'stage__narr-title' });
      this.narrBody = h('div', { 'aria-live': 'polite' });
      this.metricsEl = h('dl', { class: 'stage__metrics', hidden: true });
      const panel = h('aside', { class: 'stage__panel' }, scenesEl, h('div', { class: 'stage__narr' }, this.narrTitle, this.narrBody), this.metricsEl);

      this.playBtn = tbtn('tbtn tbtn--play', ICON.play, L('Reproducir / pausar (Espacio)', 'Play / pause (Space)'), () => this.toggle());
      const transport = h('div', { class: 'stage__transport' },
        tbtn('tbtn', ICON.prev, L('Escena anterior (←)', 'Previous scene (←)'), () => this.go(this.scene - 1, true)),
        this.playBtn,
        tbtn('tbtn', ICON.next, L('Escena siguiente (→)', 'Next scene (→)'), () => this.go(this.scene + 1, true)),
        tbtn('tbtn', ICON.reset, L('Reiniciar (R)', 'Restart (R)'), () => this.reset()));

      const speeds = [0.5, 1, 2];
      const seg = I.bind(h('div', { class: 'seg', role: 'group' }), 'aria-label', L('Velocidad', 'Speed'));
      this.speedSeg = seg;
      speeds.forEach(v => {
        const b = I.bind(h('button', { type: 'button', 'data-v': v, 'aria-pressed': v === 1 ? 'true' : 'false' }, v + '×'), 'title', L(`Velocidad ${v}×`, `Speed ${v}×`, { fr: `Vitesse ${v}×`, ca: `Velocitat ${v}×`, ja: `速度 ${v}×` }));
        b.addEventListener('click', () => this.setSpeed(v));
        seg.append(b);
      });

      const ctrls = (s.controls || []).map(c => {
        const el = this.makeControl(c);
        if (c.compact === false) el.classList.add('ctrl--full');
        return el;
      });
      const full = this.compact ? null : tbtn('tbtn', ICON.full, L('Pantalla completa', 'Full screen'), () => this.fullscreen());
      // Modos y botones «Simular:»
      const cp = this.compact;
      const modeDefs = [
        ['guia', cp ? L('Guiado', 'Guided') : L('Recorrido guiado', 'Guided tour'), L('Explica despacio, paso a paso, y se detiene en cada paso con su nota', 'Explains slowly, step by step, and stops at every step with its note')],
        ['corrido', L('De corrido', 'Straight through'), L('Todas las escenas seguidas, a velocidad normal', 'Every scene in a row, at normal speed')],
        ['libre', L('Libre', 'Free'), L('Tú mandas: elige una simulación, avanza paso a paso y mueve los controles', 'You are in charge: pick a simulation, step forward and move the controls')],
      ];
      this.modeSeg = I.bind(h('div', { class: 'seg stage__mode', role: 'group' }), 'aria-label', L('Modo', 'Mode'));
      modeDefs.forEach(([m, label, tip]) => {
        const b = h('button', { type: 'button', 'data-mode': m, 'aria-pressed': 'false', html: I.html(label) });
        I.bind(b, 'title', tip);
        b.addEventListener('click', () => this.setMode(m, true));
        this.modeSeg.append(b);
      });
      this.stepBtn = tbtn('tbtn stage__step', ICON.step, L('Avanzar un paso (.)', 'Step forward (.)'), () => this.advance());
      const presets = this.presetList();
      this.presetBtns = presets.map(p => {
        const b = h('button', { type: 'button', class: 'stage__preset', html: I.html(p.label) });
        I.bind(b, 'title', p.run ? L('Recorrer las escenas con esta opción', 'Go through the scenes with this option') : L('Simular esto (modo libre)', 'Simulate this (free mode)'));
        b.addEventListener('click', () => this.applyPreset(p, b));
        return b;
      });
      const presetsEl = presets.length ? h('div', { class: 'stage__presets' },
        h('span', { class: 'stage__presets-t', html: I.html(L('Simular:', 'Simulate:')) }), ...this.presetBtns) : null;
      // En la página: fila de modos y «Simular:» + fila de controles. En una diapositiva (compacto) no hay alto para dos
      // filas sin tapar el pie: todo va en una sola fila que se desplaza en horizontal, y sin velocidad (la fija el modo).
      let modes = null, controls;
      if (this.compact) {
        controls = h('div', { class: 'stage__controls' }, transport, this.modeSeg, this.stepBtn, presetsEl, ...ctrls, h('span', { class: 'grow' }));
        // fila sin barra de desplazamiento: la rueda vertical del ratón la mueve en horizontal
        controls.addEventListener('wheel', e => {
          if (controls.scrollWidth <= controls.clientWidth || Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
          e.preventDefault();
          controls.scrollLeft += e.deltaY;
        }, { passive: false });
      } else {
        modes = h('div', { class: 'stage__modes' }, this.modeSeg, this.stepBtn, presetsEl);
        controls = h('div', { class: 'stage__controls' }, transport, seg, ...ctrls, h('span', { class: 'grow' }), full);
      }

      let observe = null;
      if (!this.compact && s.observe && s.observe.length) {
        observe = h('div', { class: 'stage__observe' },
          h('div', { class: 'stage__observe-t', html: ICON.eye + I.html(L('Qué observar', 'What to watch')) }),
          h('ul', {}, s.observe.map(o => h('li', { html: I.html(o) }))),
          h('div', { class: 'stage__keys', html: I.html(L('Modos: <b>Recorrido guiado</b> (despacio, se detiene en cada paso con su nota) · <b>De corrido</b> · <b>Libre</b> (los botones «Simular:» y ⏭ paso a paso). Atajos con la animación enfocada: <kbd>Espacio</kbd> reproducir/pausar o siguiente paso · <kbd>←</kbd> <kbd>→</kbd> escenas · <kbd>.</kbd> avanzar un paso · <kbd>R</kbd> reiniciar',
            'Modes: <b>Guided tour</b> (slow, stops at every step with its note) · <b>Straight through</b> · <b>Free</b> (the «Simulate:» buttons and ⏭ step by step). Shortcuts with the animation focused: <kbd>Space</kbd> play/pause or next step · <kbd>←</kbd> <kbd>→</kbd> scenes · <kbd>.</kbd> step forward · <kbd>R</kbd> restart')) }));
      }

      this.root.append(...[head, h('div', { class: 'stage__body' }, this.viz, panel), modes, controls, observe].filter(Boolean));
      this.setMode(this.mode);
      this.host.replaceChildren(this.root);

      this.root.addEventListener('keydown', e => {
        if (e.target.closest('input, select, textarea, button')) return;
        if (e.key === ' ') { e.preventDefault(); this.toggle(); }
        else if (e.key === 'ArrowRight') { e.preventDefault(); this.go(this.scene + 1, true); }
        else if (e.key === 'ArrowLeft') { e.preventDefault(); this.go(this.scene - 1, true); }
        else if (e.key === 'r' || e.key === 'R') this.reset();
        else if (e.key === '.') this.advance();
      });
      ['pointerdown', 'pointermove', 'pointerup', 'pointerleave', 'pointercancel'].forEach(t =>
        this.canvas.addEventListener(t, e => this.pointer(t.replace('pointer', ''), e)));
      document.addEventListener('fullscreenchange', () => setTimeout(() => this.resize(true), 60));
    }

    /* Textos que no son HTML bilingüe (opciones de <select>) y lienzo: se actualizan al cambiar de idioma. */
    /** Narración de la escena actual. Se repite al cambiar de idioma (relabel): las cifras con decimales o miles se
     *  formatean con el idioma activo al evaluar el texto, así que hay que evaluarlo de nuevo. */
    sceneNarrate() {
      const sc = this.spec.scenes[this.scene];
      if (!sc) return;
      this.api.narrate(typeof sc.text === 'function' ? this.safe('text', () => sc.text(this.S, this.api)) || '' : sc.text || '');
      this.narrFromScene = true;
    }

    relabel() {
      // si la narración es la de la escena (no una que la animación escribió después con api.narrate), se reevalúa
      if (this.narrFromScene && this.scene >= 0) this.sceneNarrate();
      for (const c of this.spec.controls || []) {
        if (c.type !== 'select') continue;
        const sel = this.root.querySelector(`#ctl-${this.uid}-${c.id}`);
        if (sel) Array.from(sel.options).forEach((o, k) => { o.textContent = I.tr(c.options[k][1]); });
      }
      this.safe('lang', () => this.spec.lang && this.spec.lang(this.S, this.api));
      this.dirty = true;
      this.paint();
    }

    makeControl(c) {
      const id = `ctl-${this.uid}-${c.id}`;
      const fire = v => { this.params[c.id] = v; this.safe('control', () => this.spec.control && this.spec.control(this.S, c.id, v, this.api)); this.dirty = true; this.kick(); };
      if (c.type === 'range') {
        const out = h('output', { for: id });
        const inp = h('input', { type: 'range', id, min: c.min, max: c.max, step: c.step || 1 });
        inp.value = c.value;
        const show = v => {
          out.textContent = c.format ? c.format(+v) : String(v);
          inp.style.setProperty('--fill', ((v - c.min) / (c.max - c.min)) * 100 + '%');
        };
        inp.addEventListener('input', () => { show(+inp.value); fire(+inp.value); });
        show(c.value);
        this.ctlSetters[c.id] = v => { inp.value = v; show(v); };
        return h('div', { class: 'ctrl' }, h('label', { for: id, html: I.html(c.label) }), inp, out);
      }
      if (c.type === 'toggle') {
        const inp = h('input', { type: 'checkbox', id, role: 'switch' });
        inp.checked = !!c.value;
        inp.addEventListener('change', () => fire(inp.checked));
        this.ctlSetters[c.id] = v => { inp.checked = !!v; };
        return h('div', { class: 'ctrl' }, h('span', { class: 'switch' }, inp, h('span')), h('label', { for: id, html: I.html(c.label) }));
      }
      if (c.type === 'text') {                 // texto libre: se aplica con Enter o al salir del campo
        const inp = h('input', { type: 'text', id, class: 'ctrl__text', maxlength: String(c.max || 100), autocomplete: 'off', spellcheck: 'false' });
        inp.value = c.value || '';
        if (c.placeholder) I.bind(inp, 'placeholder', c.placeholder);
        inp.addEventListener('change', () => fire(inp.value));
        inp.addEventListener('keydown', e => { e.stopPropagation(); if (e.key === 'Enter') { e.preventDefault(); fire(inp.value); } });
        this.ctlSetters[c.id] = v => { inp.value = v; };
        return h('div', { class: 'ctrl ctrl--text' }, h('label', { for: id, html: I.html(c.label) }), inp);
      }
      if (c.type === 'select') {
        const sel = h('select', { id }, c.options.map(([v, t]) => h('option', { value: v }, I.tr(t))));
        sel.value = c.value;
        sel.addEventListener('change', () => fire(sel.value));
        this.ctlSetters[c.id] = v => { sel.value = v; };
        return h('div', { class: 'ctrl' }, h('label', { for: id, html: I.html(c.label) }), sel);
      }
      const b = h('button', { type: 'button', class: 'btn btn--sm', id, html: I.html(c.label) });
      b.addEventListener('click', () => fire(true));
      return b;
    }

    /* ---------- escenas ---------- */
    go(i, user) {
      if (!this.booted) { this.boot(); if (i === this.scene && !user) return; }
      const scenes = this.spec.scenes || [];
      if (!scenes.length) return;
      if (i >= scenes.length) { if (this.spec.loop) i = 0; else return; }
      i = clamp(i, 0, scenes.length - 1);
      if (i === this.scene && !user) return;
      this.scene = i;
      this.sceneT = 0;
      this.seen.add(i);
      this.sceneBtns.forEach((b, k) => {
        b.setAttribute('aria-current', k === i ? 'step' : 'false');
        b.classList.toggle('is-seen', this.seen.has(k));
      });
      const b = this.sceneBtns[i];
      if (b && b.parentElement && b.parentElement.parentElement) {
        const list = b.parentElement.parentElement;
        if (list.scrollWidth > list.clientWidth) list.scrollLeft = b.parentElement.offsetLeft - (list.clientWidth - b.parentElement.offsetWidth) / 2;
      }
      const sc = scenes[i];
      this.titleOverride = null;
      this.narrTitle.innerHTML = `${i + 1}. ${I.html(sc.title)}`;
      if (sc.params) for (const [k, v] of Object.entries(sc.params)) this.api.set(k, v, true);
      this.safe('scene', () => this.spec.scene && this.spec.scene(this.S, i, this.api, !!user));
      // El texto se evalúa después de preparar la escena: así puede citar el estado ya configurado.
      this.sceneNarrate();
      this.cardEl.hidden = true;
      this.syncCaption();
      this.dirty = true;
      this.kick();
    }

    /* ---------- reproducción ---------- */
    play() {
      this.stilled = false;
      this.playing = true;
      this.root.classList.add('is-playing');
      this.pausedEl.hidden = true;
      this.kick();
    }
    pause() {
      this.playing = false;
      this.root.classList.remove('is-playing');
      this.pausedEl.hidden = false;
    }
    toggle() {
      if (!this.playing && this.mode === 'guia' && this.pasoTerminado()) { this.siguientePaso(); return; }
      this.playing ? this.pause() : this.play();
    }

    /* ---------- modos: recorrido guiado · de corrido · libre ---------- */
    setSpeed(v) {
      this.speed = v;
      $$('button', this.speedSeg).forEach(x => x.setAttribute('aria-pressed', String(+x.dataset.v === v)));
    }
    setMode(m, fromUser) {
      this.mode = m;
      this.root.dataset.mode = m;
      $$('button', this.modeSeg).forEach(b => b.setAttribute('aria-pressed', String(b.dataset.mode === m)));
      this.setSpeed(m === 'guia' ? 0.5 : 1);
      this.stepBtn.hidden = m !== 'libre';
      this.cardEl.hidden = true;
      if (m === 'guia') this.notas = true;
      this.syncCaption();
      if (!fromUser) return;
      this.presetBtns.forEach(b => b.classList.remove('is-on'));
      if (m === 'libre') { this.pause(); return; }
      this.scene = -1;                       // guiado y de corrido empiezan por el principio
      this.go(0, false);
      this.play();
    }
    /** Botones «Simular:» (cabecera del archivo): por omisión, una por escena. */
    presetList() {
      const s = this.spec, base = s.presetBase || {};
      if (!s.presets) return (s.scenes || []).map((sc, k) => ({ label: sc.title, scene: k }));
      return [].concat(s.presets).flatMap(p => {
        if (typeof p !== 'string') return [{ run: s.presetRun, ...p, params: { ...base, ...(p.params || {}) } }];
        const c = (s.controls || []).find(x => x.id === p);
        return c && c.options ? c.options.map(([v, label]) => ({ label, run: s.presetRun, scene: s.presetScene, params: { ...base, [p]: v } })) : [];
      });
    }
    applyPreset(p, btn) {
      this.boot();
      this.setMode(p.run ? 'corrido' : 'libre');
      if (p.scene != null) { this.scene = -1; this.go(p.scene, false); }
      // como si el estudiante eligiera cada opción: el control de la animación rehace la simulación
      for (const [k, v] of Object.entries(p.params || {})) this.api.set(k, v);
      if (p.run && p.scene == null) { this.scene = -1; this.go(0, false); }
      this.presetBtns.forEach(b => b.classList.toggle('is-on', b === btn));
      this.cardEl.hidden = true;
      this.play();
    }
    pasoTerminado() {
      const sc = (this.spec.scenes || [])[this.scene];
      return !!(sc && sc.dur && this.sceneT >= sc.dur);
    }
    /** Recorrido guiado: terminó un paso → pausa con su nota y la tarjeta para seguir. */
    finPaso() {
      this.pause();
      const n = (this.spec.scenes || []).length, i = this.scene, ultimo = i >= n - 1;
      const btn = (html, fn, cls = '') => {
        const b = h('button', { type: 'button', class: 'btn btn--sm ' + cls, html: I.html(html) });
        b.addEventListener('click', e => { e.stopPropagation(); fn(); });
        return b;
      };
      const sig = ultimo ? null : this.spec.scenes[i + 1];
      this.cardEl.replaceChildren(
        h('div', { class: 'stage__card-t', html: ultimo ? I.html(L('Fin del recorrido guiado', 'End of the guided tour'))
          : I.html(L(`Paso ${i + 1} de ${n} listo`, `Step ${i + 1} of ${n} done`,
            { fr: `Étape ${i + 1} sur ${n} terminée`, ca: `Pas ${i + 1} de ${n} fet`, ja: `ステップ ${i + 1}/${n} 完了` })) }),
        h('div', { class: 'stage__card-acc' }, ...(ultimo
          ? [btn(L('↻ Recorrido de nuevo', '↻ Tour again'), () => this.setMode('guia', true)),
             btn(L('▶ Verlo de corrido', '▶ Watch it straight through'), () => this.setMode('corrido', true), 'btn--primary'),
             btn(L('Probar tú (libre)', 'Try it yourself (free)'), () => this.setMode('libre', true))]
          : [btn(L('↻ Repetir', '↻ Repeat'), () => { this.go(i, true); this.play(); }),
             btn(I.isPair(sig.title) ? (T => L(`Siguiente: ${T.es} ▶`, `Next: ${T.en} ▶`,
               { fr: `Suivant : ${T.fr} ▶`, ca: `Següent: ${T.ca} ▶`, ja: `次へ：${T.ja} ▶` }))(I.all(sig.title)) : L('Siguiente paso ▶', 'Next step ▶'), () => this.siguientePaso(), 'btn--primary')])));
      this.cardEl.hidden = false;
    }
    siguientePaso() {
      const n = (this.spec.scenes || []).length;
      this.cardEl.hidden = true;
      if (this.scene >= n - 1) { this.setMode('guia', true); return; }
      this.go(this.scene + 1, false);
      this.play();
    }
    /** Modo libre: «⏭ paso» avanza la simulación un poco (stepSecs) y queda en pausa. */
    advance(secs = this.spec.stepSecs || 0.5) {
      if (this.mode !== 'libre') this.setMode('libre');
      this.boot();
      const dt = 1 / 30, v = this.speed;
      this.speed = 1;
      this.playing = true;
      this.inFrame = true;
      try {
        let ts = 1000;
        this.lastTs = 0;
        this.step(ts);
        for (let t = dt; t <= secs + 1e-9; t += dt) this.step(ts += dt * 1000);
      } finally { this.inFrame = false; this.speed = v; }
      this.pause();
      this.lastTs = 0;
      this.dirty = true;
      this.paint();
    }
    /** Subtítulo del recorrido guiado: en las diapositivas (sin panel de narración) la nota va sobre el lienzo. */
    syncCaption() {
      if (!this.capEl) return;
      const on = this.mode === 'guia' && this.notas && this.compact && this.scene >= 0;
      this.capEl.hidden = !on;
      this.root.classList.toggle('is-guided', this.mode === 'guia');
      if (!on) return;
      const sc = this.spec.scenes[this.scene], n = this.spec.scenes.length;
      this.capTitle.innerHTML = this.titleOverride ? I.html(this.titleOverride) : `${this.scene + 1}/${n} · ${I.html(sc.title)}`;
      this.capBody.innerHTML = this.narrBody.innerHTML;
    }
    reset() {
      this.timers.length = 0;
      this.tweens.length = 0;
      this.t = 0;
      this.S = {};
      this.safe('init', () => this.spec.init && this.spec.init(this.S, this.api));
      this.safe('layout', () => this.spec.layout && this.spec.layout(this.S, this.api));
      this.scene = -1;
      this.go(0, true);
      this.dirty = true;
      this.kick();
    }
    fullscreen() {
      if (document.fullscreenElement) document.exitFullscreen();
      else if (this.root.requestFullscreen) this.root.requestFullscreen().catch(() => {});
    }
    setSuspended(v) {
      this.suspended = !!v;
      if (!v) { this.boot(); this.resize(); this.kick(); }
    }
    // Foto fija para imprimir (PDF de las presentaciones): lo que ve quien deja correr la animación desde el
    // principio hasta llevar secs segundos en la escena i (muchas escenas se apoyan en el estado de las anteriores).
    // Parte de cero como reset(), avanza en pasos fijos de 1/30 s sin reloj real ni cuadros intermedios y se detiene
    // antes de pasar a la escena i + 1. Queda en pausa y sin cuadros pendientes: la misma llamada da la misma imagen.
    still(i = 0, secs = 0) {
      this.suspended = true;
      this.started = true;   // que el IntersectionObserver no la ponga a reproducir después
      if (this.raf) { cancelAnimationFrame(this.raf); this.raf = 0; }
      this.dpr = Math.min(window.devicePixelRatio || 1, 2);   // el exportador imprime a 2×
      this.stilled = true;
      const modo = this.mode, vel = this.speed;
      this.mode = 'corrido';                    // la foto recorre las escenas como «de corrido», a 1×
      this.speed = 1;
      this.boot();
      this.timers.length = 0;
      this.tweens.length = 0;
      this.t = 0;
      this.S = {};
      this.safe('init', () => this.spec.init && this.spec.init(this.S, this.api));
      this.resize(true);
      this.scene = -1;
      this.go(0, false);
      const scenes = this.spec.scenes || [], dt = 1 / 30;
      i = clamp(i, 0, Math.max(0, scenes.length - 1));
      this.playing = true;
      this.inFrame = true;
      this.fast = true;
      try {
        let ts = 1000;
        this.lastTs = 0;
        this.step(ts);
        for (let n = 0; n < 30 * 900; n++) {
          const sc = scenes[this.scene] || {};
          if (this.scene < i && !sc.dur) { this.go(this.scene + 1, false); continue; }   // escena sin fin automático
          if (this.scene >= i && (this.sceneT + dt > secs + 1e-9 || (sc.dur && this.sceneT + dt >= sc.dur))) break;
          this.step(ts += dt * 1000);
        }
      } finally { this.inFrame = false; this.fast = false; }
      this.mode = modo;
      this.speed = vel;
      this.cardEl.hidden = true;
      this.capEl.hidden = true;
      this.pause();
      this.lastTs = 0;
      this.paint();
    }

    kick() {
      // Dentro de un cuadro (tick, timers, tweens) no se pide otro rAF: el propio cuadro lo agenda al final.
      // Sin esto, un api.set() llamado en cada tick duplicaría las peticiones cuadro a cuadro.
      if (this.inFrame) { this.needFrame = true; return; }
      if (!this.raf && this.visible && !this.suspended) this.raf = requestAnimationFrame(this.frame);
    }

    frame(ts) {
      this.raf = 0;
      this.inFrame = true;
      this.needFrame = false;
      try { this.step(ts); } finally { this.inFrame = false; }
      const busy = this.playing || this.needFrame || this.tweens.some(tw => tw.ui);
      if (busy && this.visible && !this.suspended) this.raf = requestAnimationFrame(this.frame);
      else this.lastTs = 0;
    }

    step(ts) {
      const dt = this.lastTs ? Math.min(0.05, (ts - this.lastTs) / 1000) : 0;
      this.lastTs = ts;
      const sdt = dt * this.speed;
      if (this.playing) {
        this.t += sdt;
        this.sceneT += sdt;
        for (let k = 0; k < this.timers.length; k++) {
          const tm = this.timers[k];
          tm.t -= sdt;
          if (tm.t <= 0) { this.timers.splice(k--, 1); this.safe('timer', tm.fn); }
        }
        this.safe('tick', () => this.spec.tick && this.spec.tick(this.S, sdt, this.api));
        const sc = (this.spec.scenes || [])[this.scene];
        if (sc && sc.dur && this.sceneT >= sc.dur) {
          if (this.mode === 'corrido') this.go(this.scene + 1, false);
          else if (this.mode === 'guia' && this.playing) this.finPaso();
          // libre: la escena no cambia sola
        }
      }
      const hadTweens = this.tweens.length > 0;
      this.runTweens(sdt);
      if (this.playing || this.dirty || hadTweens) this.paint();
      this.dirty = false;
      this.needFrame = false;
    }

    runTweens(dt) {
      for (let k = 0; k < this.tweens.length; k++) {
        const tw = this.tweens[k];
        if (!tw.ui && !this.playing) continue;
        tw.t += dt;
        const p = clamp(tw.t / tw.dur, 0, 1);
        if (tw.t < 0) continue;
        const e = tw.ease(p);
        for (const key in tw.to) tw.obj[key] = tw.from[key] + (tw.to[key] - tw.from[key]) * e;
        if (p >= 1) { this.tweens.splice(k--, 1); if (tw.done) this.safe('tween', tw.done); }
      }
    }

    paint() {
      if (!this.booted || !this.ctx || !this.w || this.fast) return;   // fast: Stage.still avanza sin dibujar
      const g = this.ctx;
      g.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
      g.clearRect(0, 0, this.w, this.h);
      this.safe('draw', () => this.spec.draw(this.S, g, this.api));
    }

    resize(force) {
      const cw = this.viz.clientWidth;
      if (!cw) return;
      const w = Math.round(cw);
      const narrow = w < 560;
      const aspect = +this.host.dataset.aspect || (narrow && this.spec.aspectNarrow) || this.spec.aspect || 16 / 9;
      let hh = Math.round(w / aspect);
      if (document.fullscreenElement === this.root) hh = Math.min(hh, Math.round(window.innerHeight * 0.72));
      if (!force && w === this.w && hh === this.h) return;
      this.w = w; this.h = hh; this.narrow = narrow;
      this.canvas.width = Math.round(w * this.dpr);
      this.canvas.height = Math.round(hh * this.dpr);
      this.canvas.style.height = hh + 'px';
      this.ctx = this.canvas.getContext('2d');
      if (!this.booted) return;   // solo se reserva el alto del lienzo
      this.safe('layout', () => this.spec.layout && this.spec.layout(this.S, this.api));
      this.paint();
    }

    observe() {
      const pre = new IntersectionObserver(entries => {
        if (entries.some(e => e.isIntersecting)) { pre.disconnect(); this.boot(); }
      }, { rootMargin: '400px 0px' });
      pre.observe(this.root);
      const io = new IntersectionObserver(entries => {
        for (const e of entries) {
          this.visible = e.isIntersecting;
          if (!this.visible) continue;
          this.boot();
          this.resize();
          if (!this.started && !this.suspended) {
            this.started = true;
            if (!Hub.util.reducedMotion() && this.spec.autoplay !== false) this.play();
          }
          this.kick();
        }
      }, { threshold: 0.12 });
      io.observe(this.root);
      new ResizeObserver(() => this.resize()).observe(this.viz);
      Hub.on('theme', () => { this.dirty = true; this.paint(); });
      Hub.on('lang', () => this.relabel());
    }

    pointer(type, e) {
      if (!this.spec.pointer) return;
      const r = this.canvas.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width) * this.w;
      const y = ((e.clientY - r.top) / r.height) * this.h;
      const res = this.safe('pointer', () => this.spec.pointer(this.S, { type, x, y, e }, this.api));
      if (type === 'down' && res) {
        try { this.canvas.setPointerCapture(e.pointerId); } catch (err) { /* nada */ }
        e.preventDefault();
      }
      this.dirty = true;
      this.kick();
    }

    safe(where, fn) {
      try { return fn(); } catch (err) {
        if (!this.errors) this.errors = {};
        if (!this.errors[where]) { this.errors[where] = true; console.error(`[Stage ${this.spec.id}] error en ${where}:`, err); }
        return undefined;
      }
    }
  }

  function makeApi(st) {
    return {
      get w() { return st.w; },
      get h() { return st.h; },
      get narrow() { return st.narrow; },
      get c() { return Hub.colors(st.root); },
      get p() { return st.params; },
      get t() { return st.t; },
      get scene() { return st.scene; },
      get sceneT() { return st.sceneT; },
      get playing() { return st.playing; },
      get compact() { return st.compact; },
      get reduced() { return Hub.util.reducedMotion(); },
      get still() { return st.stilled; },   // foto de Stage.still: nada que dependa del reloj real (mediciones del navegador)
      D: Hub.draw,
      U: Hub.util,
      /** Reemplaza el texto explicativo (HTML). Llamar solo cuando cambia algo relevante. */
      narrate(html) {
        st.narrFromScene = false;
        if (I.isPair(html)) html = I.html(html, 'div');
        if (html === st.lastNarr) return;
        st.lastNarr = html;
        st.narrBody.innerHTML = html;
        if (Hub.math && /\\\(|\$\$/.test(html)) Hub.math.render(st.narrBody, true);
        st.syncCaption();
      },
      /** Título de la nota (panel y subtítulo) cuando lo que se ve no es la escena —p. ej. una simulación que eligió
       *  el estudiante con un control o «Simular:»—. title(null) vuelve al de la escena; cambiar de escena también. */
      title(x) {
        st.titleOverride = x || null;
        const sc = (st.spec.scenes || [])[st.scene];
        st.narrTitle.innerHTML = x ? I.html(x) : sc ? `${st.scene + 1}. ${I.html(sc.title)}` : '';
        st.syncCaption();
      },
      /** Métricas en vivo: [{k:'Exactitud', v:'0.84', tone:'ok'|'err'|'warn'|'c1'|'c2'}] */
      metrics(list) {
        const el = st.metricsEl;
        el.hidden = !list || !list.length;
        if (!list) return;
        if (el.children.length !== list.length) {
          el.replaceChildren(...list.map(() => h('div', { class: 'stage__metric' }, h('dt'), h('dd'))));
        }
        list.forEach((m, i) => {
          const box = el.children[i];
          box.className = 'stage__metric' + (m.tone ? ' tone-' + m.tone : '');
          const kid = I.isPair(m.k) ? m.k.es + '|' + m.k.en : m.k;
          if (box.firstChild.dataset.k !== kid) {
            box.firstChild.dataset.k = kid;
            // Las letras griegas y lo que va entre `acentos graves` no se pasan a mayúsculas
            // (η, α, γ se confundirían con H, A, Y; E[h] o s(x) cambiarían de significado).
            const fmt = k => (/[\u0370-\u03FF`]/.test(k) ? Hub.util.escape(k).split('`').map((seg, j) => (j % 2 ? `<span class="nocap">${seg}</span>`
              : seg.replace(/[\u0370-\u03FF]+/g, x => `<span class="nocap">${x}</span>`))).join('') : Hub.util.escape(k));
            box.firstChild.innerHTML = I.isPair(m.k) ? I.html({ es: fmt(m.k.es), en: fmt(m.k.en) }) : fmt(m.k);
          }
          const v = String(m.v);
          if (box.lastChild.textContent !== v) {
            box.lastChild.textContent = v;
            if (m.flash) { box.classList.remove('is-flash'); void box.offsetWidth; box.classList.add('is-flash'); }
          }
        });
      },
      /** Cambia un parámetro (y su control). silent = no dispara spec.control */
      set(id, v, silent) {
        st.params[id] = v;
        if (st.ctlSetters[id]) st.ctlSetters[id](v);
        if (!silent) { st.safe('control', () => st.spec.control && st.spec.control(st.S, id, v, st.api)); }
        st.dirty = true; st.kick();
      },
      /**
       * Interpola propiedades numéricas de obj hacia `to` en `dur` segundos.
       * o = {ease:'inOut'|..., delay, ui: true (avanza aunque esté en pausa), done: fn}
       */
      tween(obj, to, dur = 0.6, o = {}) {
        if (Hub.util.reducedMotion() || dur <= 0) {
          Object.assign(obj, to);
          if (o.done) st.safe('tween', o.done);
          st.dirty = true; st.kick();
          return;
        }
        st.tweens = st.tweens.filter(tw => !(tw.obj === obj && Object.keys(to).some(k => k in tw.to)));
        const from = {};
        for (const k in to) from[k] = obj[k] == null ? to[k] : obj[k];
        st.tweens.push({ obj, from, to, dur, t: -(o.delay || 0), ease: Hub.util.ease[o.ease || 'inOut'], ui: o.ui !== false, done: o.done });
        st.dirty = true; st.kick();
      },
      /** Ejecuta fn después de `sec` segundos de simulación (se detiene en pausa). */
      after(sec, fn) { st.timers.push({ t: sec, fn }); },
      clearTimers() { st.timers.length = 0; },
      clearTweens() { st.tweens.length = 0; },
      redraw() { st.dirty = true; st.kick(); },
      play() { st.play(); },
      pause() { st.pause(); },
      go(i) { st.go(i, false); },
      next() { st.go(st.scene + 1, false); },
      /** Reinicia la escena actual como si el usuario la hubiera elegido (p. ej. tras cambiar un control). */
      restart() { st.go(st.scene, true); },
      /** Tooltip sobre el canvas (coordenadas CSS). tip(null) lo oculta. */
      tip(x, y, html) {
        if (x == null) { st.tipEl.classList.remove('is-on'); return; }
        st.tipEl.innerHTML = I.html(html);
        st.tipEl.style.left = (x / st.w) * 100 + '%';
        st.tipEl.style.top = (y / st.h) * 100 + '%';
        st.tipEl.classList.add('is-on');
      },
      badge(text) { st.badgeEl.hidden = !text; if (text) st.badgeEl.innerHTML = I.isPair(text) ? I.html(text) : Hub.util.escape(text); },
      /** Textos multilingües: L(es, en, {fr, ca, ja}?) para el DOM (narración, métricas, tip); t(es, en, {…}?) para dibujar en el lienzo. */
      L: I.L,
      t: I.t,
      tr: I.tr,
      get lang() { return I.lang; },
      cursor(c) { st.canvas.style.cursor = c || ''; },
    };
  }

  Hub.Stage = Stage;
})();
