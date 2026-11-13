/* Ink · anotar las diapositivas a mano alzada (Wacom, iPad, ratón) y exportar un PDF anotado.
 *
 * Se monta sobre cada presentación (componente Deck) y pone el botón de lápiz flotando sobre la diapositiva
 * (esquina superior derecha), también en pantalla completa.
 * Con la anotación activa:
 *   - se dibuja sobre la diapositiva con pluma (sensible a la presión), marcador o borrador;
 *   - se pueden intercalar HOJAS DE NOTAS en blanco después de cualquier diapositiva;
 *   - todo se guarda solo en este navegador (Hub.store) y se exporta a PDF con un clic.
 *
 * El PDF anotado se construye sobre el PDF oficial de la presentación (materiales/unidad-N/P#_presentacion.pdf):
 * la tinta se añade como anotación /Ink vectorial y las hojas de notas como páginas nuevas (ver Hub.pdf).
 *
 * Atajos (con el foco en cualquier parte de la presentación): D anotar · P pluma · M marcador · B borrador ·
 * Z deshacer · Y rehacer · 1…5 color · H hoja de notas · Esc salir de la hoja o de la anotación.
 *
 * Robustez con tabletas: cada trazo pertenece a UN puntero (un dedo o la palma no lo cortan); termina con su
 * pointerup/pointercancel, con lostpointercapture o con un pointerup en cualquier parte de la página (el lápiz que
 * se levanta fuera de la diapositiva); un pointerdown nuevo del lápiz o del ratón cierra un trazo que quedó abierto;
 * cambiar de diapositiva lo cierra. Así la anotación nunca queda «trabada». Después de usar el lápiz, el dedo no
 * dibuja (palma); se reactiva al apagar y encender la anotación.
 */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { h, $, $$, clamp } = Hub.util;

  const EW = 1600, EH = 900;      // espacio virtual de una diapositiva 16:9 (el mismo que usa Hub.pdf)
  const CAB = 81;                 // alto de la cabecera de una hoja de notas, en ese espacio
  const ALFA = 0.32;              // opacidad del marcador (idéntica en pantalla y en el PDF)
  // Colores de identidad-uti/tokens.css (morado UTI, tinta, naranja UTI, azul petróleo, verde)
  const COLORES = [['#3C235F', { es: 'morado', en: 'purple' }], ['#1B1722', { es: 'tinta', en: 'ink' }], ['#EA600A', { es: 'naranja', en: 'orange' }], ['#1F6F8B', { es: 'azul', en: 'blue' }], ['#3A7D44', { es: 'verde', en: 'green' }]];
  const GROSOR = [3.6, 6.4, 11];  // diámetro de la pluma, en unidades de diapositiva
  const MARCADOR = 26;
  const K = 0.5522847498;         // aproximación de un cuarto de circunferencia con una cúbica

  const ICO = {
    pluma: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 19.5l4.2-1.1 9.6-9.6a2.2 2.2 0 0 0-3.1-3.1L5.6 15.3 4.5 19.5z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/></svg>',
    marcador: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 14.5l6-6 3.5 3.5-6 6H8.5v-3.5z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M4.5 20.5h15" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/></svg>',
    borrador: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9.5 18.5l-4-4a1.6 1.6 0 0 1 0-2.3l6.4-6.4a1.6 1.6 0 0 1 2.3 0l4 4a1.6 1.6 0 0 1 0 2.3l-6.4 6.4z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M8.5 18.5h11" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>',
    deshacer: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 14l-4-4 4-4M5.4 10H14a4.6 4.6 0 0 1 0 9.2h-3.2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    rehacer: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 14l4-4-4-4M18.6 10H10a4.6 4.6 0 0 0 0 9.2h3.2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    limpiar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 7.5h12M9.5 7.5V5.2h5v2.3M8 7.5l.9 12h6.2l.9-12" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    hoja: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h12v17H6z" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"/><path d="M12 9v6M9 12h6" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>',
    pdf: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11M7 10l5 5 5-5M5 20h14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    mas: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 12h.01M12 12h.01M18 12h.01" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/></svg>',
    cerrar: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/></svg>',
  };

  // ======================================================================
  // Geometría: un trazo con presión se convierte en el contorno de la mancha
  // de tinta. Los mismos comandos se dibujan en SVG (pantalla) y en PDF.
  // ======================================================================

  /** Arco de un cuarto de vuelta de A = c+a hasta B = c+b, con b = a girado. */
  function cuarto(cmds, cx, cy, ax, ay, bx, by) {
    cmds.push(['C', cx + ax + K * bx, cy + ay + K * by, cx + bx + K * ax, cy + by + K * ay, cx + bx, cy + by]);
  }
  /** Media circunferencia (punta redonda) desde (fx, fy) alrededor de (cx, cy). */
  function tapa(cmds, cx, cy, fx, fy) {
    const ux = fx - cx, uy = fy - cy;
    cuarto(cmds, cx, cy, ux, uy, uy, -ux);
    cuarto(cmds, cx, cy, uy, -ux, -ux, -uy);
  }
  function circulo(cx, cy, r) {
    const cmds = [['M', cx + r, cy]];
    cuarto(cmds, cx, cy, r, 0, 0, -r);
    cuarto(cmds, cx, cy, 0, -r, -r, 0);
    cuarto(cmds, cx, cy, -r, 0, 0, r);
    cuarto(cmds, cx, cy, 0, r, r, 0);
    cmds.push(['Z']);
    return cmds;
  }
  /** Curva suave (cuadráticas por los puntos medios) por una polilínea; el punto actual ya es el primero. */
  function suave(cmds, pts, inv) {
    const n = pts.length / 2;
    const px = i => pts[2 * (inv ? n - 1 - i : i)];
    const py = i => pts[2 * (inv ? n - 1 - i : i) + 1];
    for (let i = 1; i < n - 1; i++) cmds.push(['Q', px(i), py(i), (px(i) + px(i + 1)) / 2, (py(i) + py(i + 1)) / 2]);
    if (n > 1) cmds.push(['L', px(n - 1), py(n - 1)]);
  }

  /** Contorno de un trazo. p = [x, y, radio, x, y, radio, …] en unidades de diapositiva. */
  function comandos(p) {
    const n = p.length / 3;
    if (!n) return [];
    let largo = 0;
    for (let i = 3; i < p.length; i += 3) largo += Math.hypot(p[i] - p[i - 3], p[i + 1] - p[i - 2]);
    if (n === 1 || largo < 0.4) return circulo(p[0], p[1], p[2]);
    const L = [], R = [];
    for (let i = 0; i < n; i++) {
      const a = 3 * Math.max(0, i - 1), b = 3 * Math.min(n - 1, i + 1);
      let dx = p[b] - p[a], dy = p[b + 1] - p[a + 1];
      const d = Math.hypot(dx, dy) || 1;
      const nx = (-dy / d) * p[3 * i + 2], ny = (dx / d) * p[3 * i + 2];
      L.push(p[3 * i] + nx, p[3 * i + 1] + ny);
      R.push(p[3 * i] - nx, p[3 * i + 1] - ny);
    }
    const cmds = [['M', L[0], L[1]]];
    suave(cmds, L, false);
    tapa(cmds, p[3 * n - 3], p[3 * n - 2], L[2 * n - 2], L[2 * n - 1]);
    suave(cmds, R, true);
    tapa(cmds, p[0], p[1], R[0], R[1]);
    cmds.push(['Z']);
    return cmds;
  }

  const r1 = x => Math.round(x * 10) / 10;
  function svgD(cmds) {
    return cmds.map(c => (c[0] === 'Z' ? 'Z' : c[0] + c.slice(1).map(r1).join(' '))).join('');
  }
  /** Los mismos comandos como operadores de camino de PDF (misma orientación: Y hacia abajo). */
  function pdfOps(cmds) {
    let out = '', cx = 0, cy = 0;
    const n = x => String(Math.round(x * 100) / 100);
    for (const c of cmds) {
      if (c[0] === 'M') { out += `${n(c[1])} ${n(c[2])} m\n`; cx = c[1]; cy = c[2]; }
      else if (c[0] === 'L') { out += `${n(c[1])} ${n(c[2])} l\n`; cx = c[1]; cy = c[2]; }
      else if (c[0] === 'Q') {
        out += `${n(cx + (2 / 3) * (c[1] - cx))} ${n(cy + (2 / 3) * (c[2] - cy))} ` +
          `${n(c[3] + (2 / 3) * (c[1] - c[3]))} ${n(c[4] + (2 / 3) * (c[2] - c[4]))} ${n(c[3])} ${n(c[4])} c\n`;
        cx = c[3]; cy = c[4];
      } else if (c[0] === 'C') {
        out += `${n(c[1])} ${n(c[2])} ${n(c[3])} ${n(c[4])} ${n(c[5])} ${n(c[6])} c\n`;
        cx = c[5]; cy = c[6];
      } else if (c[0] === 'Z') out += 'h\n';
    }
    return out;
  }

  const rgb = hex => [1, 3, 5].map(i => Math.round((parseInt(hex.slice(i, i + 2), 16) / 255) * 1000) / 1000);
  const svgEl = (tag, attrs) => {
    const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    return el;
  };
  /** Distancia del punto (x, y) al trazo (para el borrador). */
  function cerca(tr, x, y, rad) {
    const p = tr.p;
    for (let i = 0; i < p.length; i += 3) {
      const lim = rad + p[i + 2];
      if (i + 5 >= p.length) { if (Math.hypot(x - p[i], y - p[i + 1]) <= lim) return true; break; }
      const ax = p[i], ay = p[i + 1], bx = p[i + 3], by = p[i + 4];
      const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
      const t = l2 ? clamp(((x - ax) * dx + (y - ay) * dy) / l2, 0, 1) : 0;
      if (Math.hypot(x - (ax + t * dx), y - (ay + t * dy)) <= lim) return true;
    }
    return false;
  }

  // ======================================================================
  // Componente
  // ======================================================================

  class Tinta {
    constructor(el) {
      this.el = el;
      this.deck = el._deck;
      this.id = el.dataset.deck || 'P';
      this.clave = 'ink:' + this.id;
      this.titulo = el.dataset.title || this.id;
      this.datos = this.leer();
      this.activo = false;
      this.herr = 'pluma';
      this.color = COLORES[0][0];
      this.grosor = 1;
      this.pila = [];
      this.rehacerPila = [];
      this.hoja = null;              // {s, k} si hay una hoja de notas abierta
      this.capas = new Map();        // índice de diapositiva → <svg>
      this.pluma = false;            // ¿se ha usado un lápiz? (para descartar la palma)
      this.archivo = null;           // PDF de origen elegido a mano en esta sesión
      this.construye();
      this.pinta();
    }

    // ---- datos ---------------------------------------------------------
    leer() {
      const d = Hub.store.get(this.clave, null);
      const ok = d && typeof d === 'object' && d.slides;
      return ok ? { v: 1, deck: this.id, slides: d.slides || {}, notas: d.notas || {} }
        : { v: 1, deck: this.id, slides: {}, notas: {} };
    }
    guarda() {
      for (const [k, v] of Object.entries(this.datos.slides)) if (!v.length) delete this.datos.slides[k];
      clearTimeout(this._t);
      this._t = setTimeout(() => Hub.store.set(this.clave, this.datos), 400);
      this.actualiza();
    }
    trazosDe(ref) {
      const s = String(ref.s);
      if (ref.k == null) return (this.datos.slides[s] = this.datos.slides[s] || []);
      const notas = (this.datos.notas[s] = this.datos.notas[s] || []);
      while (notas.length <= ref.k) notas.push([]);
      return notas[ref.k];
    }
    notasDe(s) { return this.datos.notas[String(s)] || []; }
    /** Guarda el estado anterior para poder deshacer. */
    marca(ref) {
      this.pila.push(ref.k === 'notas'
        ? { tipo: 'notas', s: ref.s, antes: this.notasDe(ref.s).map(a => a.slice()) }
        : { tipo: 'trazos', ref, antes: this.trazosDe(ref).slice() });
      if (this.pila.length > 60) this.pila.shift();
      this.rehacerPila.length = 0;
    }
    aplica(e) {
      const inverso = e.tipo === 'notas'
        ? { tipo: 'notas', s: e.s, antes: this.notasDe(e.s).map(a => a.slice()) }
        : { tipo: 'trazos', ref: e.ref, antes: this.trazosDe(e.ref).slice() };
      if (e.tipo === 'notas') this.datos.notas[String(e.s)] = e.antes.map(a => a.slice());
      else {
        const t = this.trazosDe(e.ref);
        t.length = 0;
        e.antes.forEach(x => t.push(x));
      }
      this.guarda();
      this.pinta();
      return inverso;
    }
    deshacer() {
      const e = this.pila.pop();
      if (!e) return;
      if (this.hoja && e.tipo === 'notas' && e.s === this.hoja.s && e.antes.length <= this.hoja.k) this.cierraHoja();
      this.rehacerPila.push(this.aplica(e));
    }
    rehacer() {
      const e = this.rehacerPila.pop();
      if (e) this.pila.push(this.aplica(e));
    }

    // ---- interfaz ------------------------------------------------------
    construye() {
      const I = Hub.i18n, L = I.L;
      // Lápiz flotante sobre la diapositiva: siempre a mano con la tableta, también en pantalla completa
      this.btnAnotar = h('button', { type: 'button', class: 'ink-float', 'aria-pressed': 'false', html: ICO.pluma });
      I.bind(this.btnAnotar, 'title', L('Anotar a mano (D)', 'Draw by hand (D)'));
      I.bind(this.btnAnotar, 'aria-label', L('Anotar a mano', 'Draw by hand'));
      this.btnAnotar.addEventListener('pointerdown', e => e.stopPropagation());   // ni trazo ni deslizamiento
      this.btnAnotar.addEventListener('click', () => this.alterna());
      this.deck.vp.append(this.btnAnotar);

      const b = (icono, etiqueta, fn, clase) => {
        const x = h('button', { type: 'button', class: 'tbtn ' + (clase || ''), html: icono });
        I.bind(x, 'title', etiqueta);
        I.bind(x, 'aria-label', etiqueta);
        x.addEventListener('click', fn);
        return x;
      };
      this.bHerr = {};
      const herr = (id, icono, etiqueta) => {
        const x = b(icono, etiqueta, () => this.usaHerr(id));
        this.bHerr[id] = x;
        return x;
      };
      this.bColor = COLORES.map(([c, nombre], i) => {
        const x = h('button', { type: 'button', class: 'ink-color', style: { '--c': c } });
        const C = I.all(nombre);
        I.bind(x, 'title', L(`Color ${C.es} (${i + 1})`, `Colour ${C.en} (${i + 1})`, { fr: `Couleur ${C.fr} (${i + 1})`, ca: `Color ${C.ca} (${i + 1})`, ja: `色：${C.ja}（${i + 1}）` }));
        x.addEventListener('click', () => { this.color = c; this.herr = this.herr === 'borrador' ? 'pluma' : this.herr; this.actualiza(); });
        return x;
      });
      this.bGrosor = GROSOR.map((g, i) => {
        const x = h('button', { type: 'button', class: 'ink-w' }, h('span', { style: { width: 2 + i * 4 + 'px', height: 2 + i * 4 + 'px' } }));
        I.bind(x, 'title', [L('Trazo fino', 'Thin stroke'), L('Trazo medio', 'Medium stroke'), L('Trazo grueso', 'Thick stroke')][i]);
        x.addEventListener('click', () => { this.grosor = i; this.actualiza(); });
        return x;
      });
      this.bDeshacer = b(ICO.deshacer, L('Deshacer (Z)', 'Undo (Z)'), () => this.deshacer());
      this.bRehacer = b(ICO.rehacer, L('Rehacer (Y)', 'Redo (Y)'), () => this.rehacer());
      this.bHoja = b(ICO.hoja, L('Hoja de notas en blanco después de esta diapositiva (H)', 'Blank notes page after this slide (H)'), () => this.nuevaHoja());
      this.bNotas = I.bind(h('button', { type: 'button', class: 'ink-notas' }), 'title', L('Abrir las hojas de notas de esta diapositiva', 'Open the notes pages of this slide'));
      this.bNotas.addEventListener('click', () => { const n = this.notasDe(this.deck.i); if (n.length) this.abreHoja(this.deck.i, 0); });
      this.bLimpiar = b(ICO.limpiar, L('Borrar la tinta de esta página', 'Clear the ink of this page'), () => this.limpia());
      this.bPdf = h('button', { type: 'button', class: 'btn btn--sm ink-pdf', html: ICO.pdf + I.html(L('PDF anotado', 'Annotated PDF')) });
      this.bPdf.addEventListener('click', () => { if (this.bPdf.getAttribute('aria-disabled') !== 'true') this.exporta(); });
      this.bMas = b(ICO.mas, L('Más opciones', 'More options'), () => { this.menu.hidden = !this.menu.hidden; });

      this.estado = h('span', { class: 'ink-estado', role: 'status' });
      this.barra = h('div', { class: 'ink-bar', hidden: true },
        h('div', { class: 'ink-grupo' }, herr('pluma', ICO.pluma, L('Pluma (P)', 'Pen (P)')), herr('marcador', ICO.marcador, L('Marcador (M)', 'Highlighter (M)')), herr('borrador', ICO.borrador, L('Borrador (B)', 'Eraser (B)'))),
        h('div', { class: 'ink-grupo ink-grupo--colores' }, this.bColor),
        h('div', { class: 'ink-grupo' }, this.bGrosor),
        h('div', { class: 'ink-grupo' }, this.bDeshacer, this.bRehacer, this.bLimpiar),
        h('div', { class: 'ink-grupo' }, this.bHoja, this.bNotas),
        this.estado, this.bPdf, this.bMas);

      this.menu = h('div', { class: 'ink-menu', hidden: true },
        h('p', { class: 'ink-menu__t', html: I.html(L('Anotaciones de ', 'Annotations of ')) + `<strong>${this.id}</strong>` }),
        h('p', { class: 'muted', html: I.html(L('Se guardan en este navegador. Descarga una copia si vas a cambiar de equipo.', 'They are saved in this browser. Download a copy if you are going to change computers.')) }),
        h('div', { class: 'ink-menu__acc' },
          h('button', { type: 'button', class: 'btn btn--sm', onclick: () => this.descargaJSON(), html: I.html(L('Descargar anotaciones (.json)', 'Download annotations (.json)')) }),
          h('button', { type: 'button', class: 'btn btn--sm', onclick: () => this.entrada.click(), html: I.html(L('Cargar anotaciones', 'Load annotations')) }),
          h('button', { type: 'button', class: 'btn btn--sm', onclick: () => this.borraTodo(), html: I.html(L('Borrar todo', 'Clear everything')) })),
        h('p', { class: 'ink-menu__pdf muted', html: I.html(L('El PDF anotado se arma sobre el PDF oficial de la presentación: la tinta queda como anotación vectorial y cada hoja de notas, como una página nueva.',
          'The annotated PDF is built on top of the official PDF of the presentation: the ink becomes a vector annotation and every notes page, a new page.')) }),
        h('div', { class: 'ink-menu__origen', hidden: true }));
      this.entrada = h('input', { type: 'file', accept: 'application/json,.json', hidden: true, onchange: e => this.cargaJSON(e.target.files[0]) });
      this.entradaPdf = h('input', { type: 'file', accept: 'application/pdf,.pdf', hidden: true, onchange: e => this.eligePdf(e.target.files[0]) });
      this.el.append(this.barra, this.menu, this.entrada, this.entradaPdf);

      // Hoja de notas: una sola capa reutilizable sobre la diapositiva activa.
      this.hojaEl = h('div', { class: 'ink-hoja', hidden: true });
      this.hojaTit = h('span', { class: 'ink-hoja__t' });
      this.hojaNav = h('span', { class: 'ink-hoja__nav' });
      this.hojaEl.append(h('div', { class: 'ink-hoja__cab' }, this.hojaTit, this.hojaNav));
      this.hojaSvg = this.creaCapa(true);
      this.hojaEl.append(this.hojaSvg);
      this.deck.vp.append(this.hojaEl);

      // En todo el deck (también con el foco en la barra de herramientas), antes que la navegación del Deck
      this.el.addEventListener('keydown', e => this.tecla(e), true);
      Hub.on('lang', () => this.actualiza());
      Hub.on('deck:slide', ({ deck }) => { if (deck === this.deck) { this.termina(); this.cierraHoja(); this.pinta(); } });
      // red de seguridad: el lápiz o el ratón se levantan fuera de la capa (sin captura) → el trazo termina igual
      const fin = e => { if ((this.dibujo && e.pointerId === this.dibujo.id) || (this.borrando && e.pointerId === this.borrando.id)) this.termina(); };
      addEventListener('pointerup', fin, true);
      addEventListener('pointercancel', fin, true);
      document.addEventListener('click', e => {
        if (!this.menu.hidden && !this.menu.contains(e.target) && e.target !== this.bMas && !this.bMas.contains(e.target)) this.menu.hidden = true;
      });
      this.actualiza();
    }

    creaCapa(hoja) {
      const svg = svgEl('svg', { class: 'ink-capa', viewBox: `0 0 ${EW} ${EH}`, 'aria-hidden': 'true' });
      if (hoja) {
        const pid = 'rejilla-' + this.id;
        const defs = svgEl('defs', {});
        const pat = svgEl('pattern', { id: pid, x: 0, y: CAB, width: 80, height: 80, patternUnits: 'userSpaceOnUse' });
        pat.append(svgEl('path', { d: 'M0 0H80M0 0V80', fill: 'none', stroke: '#E9E3F1', 'stroke-width': 1.2 }));
        defs.append(pat);
        svg.append(defs, svgEl('rect', { x: 0, y: CAB, width: EW, height: EH - CAB, fill: `url(#${pid})` }));
      }
      svg.append(svgEl('g', { class: 'ink-hl' }), svgEl('g', { class: 'ink-pen' }));
      svg.addEventListener('pointerdown', e => this.abajo(e, svg));
      svg.addEventListener('pointermove', e => this.mueve(e));
      svg.addEventListener('pointerup', e => this.arriba(e));
      svg.addEventListener('pointercancel', e => this.arriba(e));
      svg.addEventListener('lostpointercapture', e => this.arriba(e));
      svg.addEventListener('contextmenu', e => { if (this.activo) e.preventDefault(); });
      return svg;
    }
    capaDe(i) {
      if (this.capas.has(i)) return this.capas.get(i);
      const svg = this.creaCapa(false);
      this.deck.slides[i].append(svg);
      this.capas.set(i, svg);
      return svg;
    }

    alterna(v) {
      this.activo = v == null ? !this.activo : v;
      this.termina();
      this.pluma = false;          // al volver a entrar, el dedo puede dibujar hasta que se use el lápiz
      if (this.activo) this.deck.slides.forEach((s, i) => this.capaDe(i));   // superficie de dibujo en todas
      else this.cierraHoja();
      this.el.classList.toggle('is-inking', this.activo);
      this.barra.hidden = !this.activo;
      this.btnAnotar.setAttribute('aria-pressed', String(this.activo));
      if (!this.activo) this.menu.hidden = true;
      this.actualiza();
      if (this.activo) this.deck.vp.focus({ preventScroll: true });
    }
    usaHerr(id) { this.herr = id; this.actualiza(); }

    actualiza() {
      for (const [id, btn] of Object.entries(this.bHerr)) btn.classList.toggle('is-on', this.herr === id);
      this.bColor.forEach((x, i) => x.classList.toggle('is-on', COLORES[i][0] === this.color));
      this.bGrosor.forEach((x, i) => x.classList.toggle('is-on', i === this.grosor));
      // aria-disabled, no disabled: un botón enfocado que se deshabilita suelta el foco al <body> y el teclado dejaría de
      // llegar a la presentación (las flechas, Esc, D…). Sus acciones ya no hacen nada cuando no corresponde.
      const inactivo = (b, v) => b.setAttribute('aria-disabled', String(!!v));
      inactivo(this.bDeshacer, !this.pila.length);
      inactivo(this.bRehacer, !this.rehacerPila.length);
      const n = this.notasDe(this.deck.i).length;
      const t = Hub.i18n.t;
      this.bNotas.textContent = n ? t(`${n} hoja${n > 1 ? 's' : ''}`, `${n} page${n > 1 ? 's' : ''}`,
        { fr: `${n} page${n > 1 ? 's' : ''}`, ca: `${n} full${n > 1 ? 's' : ''}`, ja: `${n} ページ` }) : t('sin hojas', 'no pages');
      inactivo(this.bNotas, !n);
      this.bNotas.classList.toggle('is-on', !!this.hoja);
      const total = this.cuenta();
      this.estado.textContent = total.trazos
        ? t(`${total.trazos} trazo${total.trazos > 1 ? 's' : ''} · ${total.hojas} hoja${total.hojas === 1 ? '' : 's'}`, `${total.trazos} stroke${total.trazos > 1 ? 's' : ''} · ${total.hojas} page${total.hojas === 1 ? '' : 's'}`,
          { fr: `${total.trazos} trait${total.trazos > 1 ? 's' : ''} · ${total.hojas} page${total.hojas > 1 ? 's' : ''}`,
            ca: `${total.trazos} traç${total.trazos > 1 ? 'os' : ''} · ${total.hojas} full${total.hojas === 1 ? '' : 's'}`,
            ja: `${total.trazos} 本の線 · ${total.hojas} ページ` })
        : t('sin anotaciones', 'no annotations');
      inactivo(this.bPdf, (!total.trazos && !total.hojas) || this.exportando);
    }
    cuenta() {
      let trazos = 0, hojas = 0;
      for (const t of Object.values(this.datos.slides)) trazos += t.length;
      for (const ns of Object.values(this.datos.notas)) { hojas += ns.length; ns.forEach(t => { trazos += t.length; }); }
      return { trazos, hojas };
    }

    // ---- dibujo --------------------------------------------------------
    pinta() {
      this.deck.slides.forEach((s, i) => {
        const t = this.datos.slides[String(i)] || [];
        if (!t.length && !this.capas.has(i)) return;
        this.repinta(this.capaDe(i), t);
      });
      if (this.hoja) this.repinta(this.hojaSvg, this.trazosDe(this.hoja));
      this.actualiza();
    }
    repinta(svg, trazos) {
      const hl = $('.ink-hl', svg), pen = $('.ink-pen', svg);
      hl.replaceChildren();
      pen.replaceChildren();
      trazos.forEach(tr => (tr.h ? hl : pen).append(svgEl('path', { d: svgD(comandos(tr.p)), fill: tr.c })));
    }

    destino() { return this.hoja ? { s: this.hoja.s, k: this.hoja.k } : { s: this.deck.i, k: null }; }

    abajo(ev, svg) {
      if (!this.activo) return;
      if (ev.pointerType === 'pen') this.pluma = true;
      if (ev.pointerType === 'touch' && this.pluma) {             // descarta la palma de la mano
        this.estado.textContent = Hub.i18n.t('Dedo ignorado mientras usas el lápiz (apaga y enciende la anotación para dibujar con el dedo)',
          'Finger ignored while you use the pen (turn annotation off and on to draw with your finger)');
        return;
      }
      if (this.dibujo || this.borrando) {
        if (ev.pointerType === 'touch') return;                    // otro dedo mientras se dibuja
        this.termina();                                            // un trazo que quedó abierto no bloquea el nuevo
      }
      if (ev.button > 0 && ev.button !== 5) return;
      ev.preventDefault();
      ev.stopPropagation();
      const borra = this.herr === 'borrador' || ev.button === 5 || (ev.buttons & 32) > 0;
      const ref = this.destino();
      const captura = () => { try { svg.setPointerCapture(ev.pointerId); } catch (e) { /* sin captura: termina por la red de seguridad */ } };
      if (borra) {
        this.borrando = { ref, svg, tocado: false, id: ev.pointerId };
        captura();
        this.borra(ev, svg);
        return;
      }
      this.marca(ref);
      const tr = { h: this.herr === 'marcador' ? 1 : 0, c: this.color, p: [] };
      this.dibujo = { ref, svg, tr, id: ev.pointerId, path: svgEl('path', { d: '', fill: tr.c }), pres: null, raf: 0 };
      $(tr.h ? '.ink-hl' : '.ink-pen', svg).append(this.dibujo.path);
      this.trazosDe(ref).push(tr);
      captura();
      this.punto(ev, svg);
      this.dibuja();
    }
    mueve(ev) {
      if (this.borrando) { if (ev.pointerId === this.borrando.id) this.borra(ev, this.borrando.svg); return; }
      const d = this.dibujo;
      if (!d || ev.pointerId !== d.id) return;
      ev.preventDefault();
      const lista = ev.getCoalescedEvents ? ev.getCoalescedEvents() : [ev];
      (lista.length ? lista : [ev]).forEach(e => this.punto(e, d.svg));
      // el contorno se recalcula una vez por cuadro, no por punto: un lápiz a 240 Hz no satura la página
      if (!d.raf) d.raf = requestAnimationFrame(() => { d.raf = 0; this.dibuja(d); });
    }
    dibuja(d = this.dibujo) { if (d && d.tr.p.length) d.path.setAttribute('d', svgD(comandos(d.tr.p))); }
    arriba(ev) {
      const d = this.dibujo, b = this.borrando;
      if ((d && ev.pointerId === d.id) || (b && ev.pointerId === b.id)) this.termina();
    }
    /** Cierra el trazo o el borrado en curso (si lo hay), pase lo que pase con el puntero. */
    termina() {
      if (this.borrando) {
        const b = this.borrando;
        this.borrando = null;
        try { b.svg.releasePointerCapture(b.id); } catch (e) { /* ya se soltó */ }
        this.guarda();
      }
      if (!this.dibujo) return;
      const d = this.dibujo;
      this.dibujo = null;
      if (d.raf) cancelAnimationFrame(d.raf);
      try { d.svg.releasePointerCapture(d.id); } catch (e) { /* el puntero ya se soltó */ }
      if (!d.tr.p.length) {
        const t = this.trazosDe(d.ref), k = t.lastIndexOf(d.tr);
        if (k >= 0) t.splice(k, 1);
        d.path.remove();
        this.pila.pop();
      } else this.dibuja(d);
      this.guarda();
    }
    punto(ev, svg) {
      const r = svg.getBoundingClientRect();
      if (!r.width) return;
      const x = ((ev.clientX - r.left) / r.width) * EW;
      const y = ((ev.clientY - r.top) / r.height) * EH;
      const d = this.dibujo;
      const p = d.tr.p;
      const n = p.length;
      if (n && Math.hypot(x - p[n - 3], y - p[n - 2]) < 1.4) return;
      let rad;
      if (d.tr.h) rad = MARCADOR / 2;
      else {
        let pr = ev.pointerType === 'pen' && ev.pressure > 0 ? ev.pressure : 0.5;
        d.pres = d.pres == null ? pr : d.pres + (pr - d.pres) * 0.35;
        rad = (GROSOR[this.grosor] / 2) * (ev.pointerType === 'pen' ? 0.45 + 0.85 * d.pres : 1);
      }
      p.push(r1(x), r1(y), Math.round(rad * 100) / 100);
    }
    borra(ev, svg) {
      const r = svg.getBoundingClientRect();
      if (!r.width) return;
      const x = ((ev.clientX - r.left) / r.width) * EW;
      const y = ((ev.clientY - r.top) / r.height) * EH;
      const trazos = this.trazosDe(this.borrando.ref);
      const quedan = trazos.filter(tr => !cerca(tr, x, y, 7));
      if (quedan.length === trazos.length) return;
      if (!this.borrando.tocado) { this.marca(this.borrando.ref); this.borrando.tocado = true; }
      trazos.length = 0;
      quedan.forEach(t => trazos.push(t));
      this.repinta(svg, trazos);
      this.actualiza();
    }
    limpia() {
      const ref = this.destino();
      const t = this.trazosDe(ref);
      if (!t.length) return;
      this.marca(ref);
      t.length = 0;
      this.repinta(this.hoja ? this.hojaSvg : this.capaDe(ref.s), t);
      this.guarda();
    }

    // ---- hojas de notas ------------------------------------------------
    nuevaHoja() {
      const s = this.hoja ? this.hoja.s : this.deck.i;
      const notas = this.datos.notas[String(s)] || [];
      this.marca({ s, k: 'notas' });
      this.datos.notas[String(s)] = notas.concat([[]]);
      this.guarda();
      this.abreHoja(s, this.datos.notas[String(s)].length - 1);
      if (!this.activo) this.alterna(true);
    }
    abreHoja(s, k) {
      const notas = this.notasDe(s);
      if (!notas.length) return;
      k = clamp(k, 0, notas.length - 1);
      this.hoja = { s, k };
      this.hojaEl.hidden = false;
      this.hojaTit.textContent = Hub.i18n.t(`Notas · después de la diapositiva ${s + 1} de ${this.deck.slides.length}` +
        (notas.length > 1 ? ` · hoja ${k + 1} de ${notas.length}` : ''), `Notes · after slide ${s + 1} of ${this.deck.slides.length}` +
        (notas.length > 1 ? ` · page ${k + 1} of ${notas.length}` : ''));
      this.hojaNav.replaceChildren(
        h('button', { type: 'button', class: 'tbtn', title: Hub.i18n.t('Hoja anterior (←)', 'Previous page (←)'), 'aria-label': Hub.i18n.t('Hoja anterior', 'Previous page'), html: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>', onclick: () => this.mueveHoja(-1) }),
        h('button', { type: 'button', class: 'tbtn', title: Hub.i18n.t('Hoja siguiente (→)', 'Next page (→)'), 'aria-label': Hub.i18n.t('Hoja siguiente', 'Next page'), html: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>', onclick: () => this.mueveHoja(1) }),
        h('button', { type: 'button', class: 'tbtn', title: Hub.i18n.t('Volver a la diapositiva (Esc)', 'Back to the slide (Esc)'), 'aria-label': Hub.i18n.t('Volver a la diapositiva', 'Back to the slide'), html: ICO.cerrar, onclick: () => this.cierraHoja() }));
      this.repinta(this.hojaSvg, this.trazosDe(this.hoja));
      this.actualiza();
    }
    mueveHoja(d) {
      if (!this.hoja) return;
      const notas = this.notasDe(this.hoja.s);
      const k = this.hoja.k + d;
      if (k < 0) { this.cierraHoja(); return; }
      if (k >= notas.length) { this.cierraHoja(); this.deck.next(); return; }
      this.abreHoja(this.hoja.s, k);
    }
    cierraHoja() {
      if (!this.hoja) return;
      this.hoja = null;
      this.hojaEl.hidden = true;
      this.actualiza();
    }

    tecla(e) {
      if (e.target.closest('input, select, textarea, .stage')) return;
      const k = e.key;
      if (e.target.closest('button') && (k === ' ' || k === 'Enter')) return;   // Espacio/Intro: del botón
      if (this.hoja) {
        if (k === 'ArrowRight' || k === 'PageDown' || k === ' ') { e.preventDefault(); e.stopPropagation(); this.mueveHoja(1); return; }
        if (k === 'ArrowLeft' || k === 'PageUp') { e.preventDefault(); e.stopPropagation(); this.mueveHoja(-1); return; }
        if (k === 'Escape') { e.stopPropagation(); this.cierraHoja(); return; }
      } else if (k === 'Escape' && this.activo) { e.stopPropagation(); this.alterna(false); return; }
      if (e.ctrlKey || e.metaKey) {
        if (k === 'z' || k === 'Z') { e.preventDefault(); e.stopPropagation(); if (e.shiftKey) this.rehacer(); else this.deshacer(); }
        return;
      }
      if (k === 'd' || k === 'D') { e.stopPropagation(); this.alterna(); return; }
      if (k === 'h' || k === 'H') { e.stopPropagation(); this.nuevaHoja(); return; }
      if (!this.activo) return;
      if (k === 'p' || k === 'P') { e.stopPropagation(); this.usaHerr('pluma'); }
      else if (k === 'm' || k === 'M') { e.stopPropagation(); this.usaHerr('marcador'); }
      else if (k === 'b' || k === 'B') { e.stopPropagation(); this.usaHerr('borrador'); }
      else if (k === 'z' || k === 'Z') { e.stopPropagation(); this.deshacer(); }
      else if (k === 'y' || k === 'Y') { e.stopPropagation(); this.rehacer(); }
      else if (k >= '1' && k <= '5' && COLORES[+k - 1]) { e.stopPropagation(); this.color = COLORES[+k - 1][0]; this.actualiza(); }
    }

    // ---- exportación ---------------------------------------------------
    /** Tinta de una página como operadores de PDF. */
    ops(trazos) {
      let out = '';
      for (const tr of trazos) {
        const c = rgb(tr.c).join(' ');
        const camino = pdfOps(comandos(tr.p));
        out += tr.h ? `q /GM gs ${c} rg\n${camino}f\nQ\n` : `q /GN gs ${c} rg\n${camino}f\nQ\n`;
      }
      return out;
    }
    lineas(trazos) {
      return trazos.map(tr => {
        const l = [];
        for (let i = 0; i < tr.p.length; i += 3) l.push(r1(tr.p[i]), r1(tr.p[i + 1]));
        return l;
      });
    }
    urlPdf() {
      const sub = this.el.closest('.sub') || document;
      const a = sub.querySelector('[data-material$="_presentacion.pdf"]') || document.querySelector(`[data-material$="/${this.id}_presentacion.pdf"]`);
      return a ? a.href : null;
    }
    async origenPdf() {
      if (this.archivo) return this.archivo;
      const url = this.urlPdf();
      if (url) {
        try {
          const r = await fetch(url);
          if (r.ok) return new Uint8Array(await r.arrayBuffer());
        } catch (e) { /* file:// no permite leer archivos vecinos */ }
      }
      return null;
    }
    eligePdf(f) {
      if (!f) return;
      const lector = new FileReader();
      lector.onload = () => { this.archivo = new Uint8Array(lector.result); this.exporta(); };
      lector.readAsArrayBuffer(f);
    }
    async exporta() {
      this.exportando = true;
      this.actualiza();
      this.estado.textContent = Hub.i18n.t('Generando el PDF…', 'Building the PDF…');
      try {
        const origen = await this.origenPdf();
        if (!origen) {
          this.menu.hidden = false;
          const caja = $('.ink-menu__origen', this.menu);
          caja.hidden = false;
          caja.replaceChildren(
            h('p', { html: Hub.i18n.html(Hub.i18n.L('Este navegador no puede leer el PDF de la presentación desde el disco (se abrió con <code>file://</code>).',
              'This browser cannot read the PDF of the presentation from the disk (it was opened with <code>file://</code>).')) }),
            h('button', { type: 'button', class: 'btn btn--sm', onclick: () => this.entradaPdf.click(), html: Hub.i18n.html(Hub.i18n.L('Elegir ', 'Choose ')) + `${this.id}_presentacion.pdf` }),
            h('p', { class: 'muted', html: Hub.i18n.html(Hub.i18n.L('Está en ', 'It is in ')) + `<code>materiales/unidad-${this.id.replace(/\D/g, '')}/${this.id}_presentacion.pdf</code>.` }));
          this.exportando = false;
          this.actualiza();
          this.estado.textContent = Hub.i18n.t('Falta el PDF de origen', 'The source PDF is missing');
          return;
        }
        const paginas = Hub.pdf.contar(origen);
        const capas = [], hojas = [];
        this.deck.slides.forEach((s, i) => {
          const t = this.datos.slides[String(i)] || [];
          if (t.length) capas.push({ pagina: i, ops: this.ops(t), inkList: this.lineas(t), color: rgb(t[0].c) });
          const ns = this.notasDe(i);
          ns.forEach((notas, k) => {
            hojas.push({
              tras: i,
              ops: this.ops(notas),
              etiqueta: Hub.i18n.t(`${this.id} · notas después de la diapositiva ${i + 1}`, `${this.id} · notes after slide ${i + 1}`,
                { fr: `${this.id} · notes après la diapositive ${i + 1}`, ca: `${this.id} · notes després de la diapositiva ${i + 1}`, ja: `${this.id} · スライド ${i + 1} の後のメモ` }) + (ns.length > 1 ? ` (${k + 1}/${ns.length})` : ''),
            });
          });
        });
        const salida = Hub.pdf.anotar(origen, {
          capas, hojas, espacio: [EW, EH], alfaMarcador: ALFA, rejillaDesde: CAB,
          titulo: Hub.i18n.t(`Anotaciones de clase · ${this.id}`, `Class annotations · ${this.id}`,
            { fr: `Annotations du cours · ${this.id}`, ca: `Anotacions de classe · ${this.id}`, ja: `授業の書き込み · ${this.id}` }),
        });
        const hoy = new Date();
        const fecha = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}-${String(hoy.getDate()).padStart(2, '0')}`;
        this.descarga(new Blob([salida], { type: 'application/pdf' }), `${this.id}_presentacion_anotado_${fecha}.pdf`);
        const aviso = paginas !== this.deck.slides.length
          ? Hub.i18n.t(` · ojo: el PDF tiene ${paginas} páginas y la presentación ${this.deck.slides.length} diapositivas`, ` · warning: the PDF has ${paginas} pages and the presentation ${this.deck.slides.length} slides`,
            { fr: ` · attention : le PDF a ${paginas} pages et la présentation ${this.deck.slides.length} diapositives`,
              ca: ` · compte: el PDF té ${paginas} pàgines i la presentació ${this.deck.slides.length} diapositives`,
              ja: ` · 注意：PDF は ${paginas} ページ、スライドは ${this.deck.slides.length} 枚です` })
          : '';
        this.estado.textContent = Hub.i18n.t(`PDF listo (+${hojas.length} hoja${hojas.length === 1 ? '' : 's'})`, `PDF ready (+${hojas.length} page${hojas.length === 1 ? '' : 's'})`,
          { fr: `PDF prêt (+${hojas.length} page${hojas.length > 1 ? 's' : ''})`, ca: `PDF llest (+${hojas.length} full${hojas.length === 1 ? '' : 's'})`, ja: `PDF 完成（+${hojas.length} ページ）` }) + aviso;
      } catch (err) {
        this.estado.textContent = Hub.i18n.t('No se pudo generar: ', 'Could not build it: ') + (err && err.message ? err.message : err);
      }
      const msg = this.estado.textContent;      // «PDF listo…» o el error: que actualiza() no lo tape
      this.exportando = false;
      this.actualiza();
      this.estado.textContent = msg;
    }
    descarga(blob, nombre) {
      const a = h('a', { href: URL.createObjectURL(blob), download: nombre });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 5000);
    }
    descargaJSON() {
      const d = { ...this.datos, titulo: this.titulo, fecha: new Date().toISOString() };
      this.descarga(new Blob([JSON.stringify(d)], { type: 'application/json' }), `anotaciones_${this.id}.json`);
    }
    cargaJSON(f) {
      if (!f) return;
      const lector = new FileReader();
      lector.onload = () => {
        try {
          const d = JSON.parse(lector.result);
          if (!d || typeof d !== 'object' || !d.slides) throw new Error('formato desconocido');
          this.datos = { v: 1, deck: this.id, slides: d.slides || {}, notas: d.notas || {} };
          this.pila.length = this.rehacerPila.length = 0;
          this.cierraHoja();
          this.capas.forEach(svg => svg.remove());
          this.capas.clear();
          this.guarda();
          this.pinta();
          this.estado.textContent = Hub.i18n.t('Anotaciones cargadas', 'Annotations loaded');
        } catch (e) { this.estado.textContent = Hub.i18n.t('Archivo no válido', 'Invalid file'); }
      };
      lector.readAsText(f);
      this.entrada.value = '';
    }
    borraTodo() {
      const n = this.cuenta();
      if (!n.trazos && !n.hojas) return;
      if (!window.confirm(Hub.i18n.t(`¿Borrar las anotaciones de ${this.id}? Se perderán ${n.trazos} trazos y ${n.hojas} hojas de notas.`,
        `Delete the annotations of ${this.id}? ${n.trazos} strokes and ${n.hojas} notes pages will be lost.`,
        { fr: `Effacer les annotations de ${this.id} ? ${n.trazos} traits et ${n.hojas} pages de notes seront perdus.`,
          ca: `Vols esborrar les anotacions de ${this.id}? Es perdran ${n.trazos} traços i ${n.hojas} fulls de notes.`,
          ja: `${this.id} の書き込みを削除しますか？ ${n.trazos} 本の線と ${n.hojas} ページのメモが失われます。` }))) return;
      this.datos = { v: 1, deck: this.id, slides: {}, notas: {} };
      this.pila.length = this.rehacerPila.length = 0;
      this.cierraHoja();
      this.capas.forEach(svg => svg.remove());
      this.capas.clear();
      this.guarda();
      this.pinta();
      this.menu.hidden = true;
    }
  }

  Hub.ink = {
    instancias: [],
    mountAll(root = document) {
      $$('.deck[data-mounted]:not([data-ink])', root).forEach(el => {
        if (!el._deck) return;
        el.setAttribute('data-ink', '');
        el._ink = new Tinta(el);
        Hub.ink.instancias.push(el._ink);
      });
    },
  };
})();
