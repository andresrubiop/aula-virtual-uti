/* Hub.draw · primitivas de dibujo en canvas para las animaciones.
   Coordenadas en píxeles CSS (el Stage ya aplica devicePixelRatio). */
(function () {
  'use strict';
  const D = (window.Hub.draw = {});
  const SANS = "Poppins, Arial, 'Helvetica Neue', 'Noto Sans CJK JP', 'Hiragino Sans', 'Yu Gothic', Meiryo, sans-serif";
  const MONO = "'JetBrains Mono', ui-monospace, Menlo, monospace";

  D.font = (size, weight = 500, mono = false) => `${weight} ${size}px ${mono ? MONO : SANS}`;

  D.rgb = function (hex) {
    let h = String(hex).trim().replace('#', '');
    if (h.length === 3) h = h.split('').map(c => c + c).join('');
    const n = parseInt(h.slice(0, 6), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  };
  D.alpha = (hex, a) => { const [r, g, b] = D.rgb(hex); return `rgba(${r},${g},${b},${a})`; };
  D.mix = function (h1, h2, t) {
    const a = D.rgb(h1), b = D.rgb(h2);
    const c = a.map((v, i) => Math.round(v + (b[i] - v) * t));
    return '#' + c.map(v => v.toString(16).padStart(2, '0')).join('');
  };

  D.clear = (g, w, h, color) => { g.save(); g.setTransform(g.getTransform()); g.fillStyle = color; g.fillRect(0, 0, w, h); g.restore(); };

  D.rrect = function (g, x, y, w, h, r = 6) {
    r = Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2);
    g.beginPath();
    g.moveTo(x + r, y);
    g.arcTo(x + w, y, x + w, y + h, r);
    g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r);
    g.arcTo(x, y, x + w, y, r);
    g.closePath();
  };

  /** Traza la forma de un marcador: circle | square | triangle | diamond | star */
  D.shape = function (g, kind, x, y, r) {
    g.beginPath();
    if (kind === 'square') { const s = r * 0.9; g.rect(x - s, y - s, 2 * s, 2 * s); }
    else if (kind === 'triangle') { g.moveTo(x, y - r * 1.15); g.lineTo(x + r * 1.05, y + r * 0.75); g.lineTo(x - r * 1.05, y + r * 0.75); g.closePath(); }
    else if (kind === 'diamond') { g.moveTo(x, y - r * 1.2); g.lineTo(x + r * 1.2, y); g.lineTo(x, y + r * 1.2); g.lineTo(x - r * 1.2, y); g.closePath(); }
    else if (kind === 'star') {
      for (let i = 0; i < 10; i++) {
        const a = -Math.PI / 2 + (i * Math.PI) / 5, rr = i % 2 ? r * 0.5 : r * 1.25;
        i ? g.lineTo(x + rr * Math.cos(a), y + rr * Math.sin(a)) : g.moveTo(x + rr * Math.cos(a), y + rr * Math.sin(a));
      }
      g.closePath();
    } else g.arc(x, y, r, 0, Math.PI * 2);
  };

  /** Marcador con relleno/borde: D.dot(g, x, y, 5, {fill, stroke, lw, shape, alpha}) */
  D.dot = function (g, x, y, r, o = {}) {
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    D.shape(g, o.shape || 'circle', x, y, r);
    if (o.fill) { g.fillStyle = o.fill; g.fill(); }
    if (o.stroke) { g.strokeStyle = o.stroke; g.lineWidth = o.lw || 1.5; g.stroke(); }
    g.restore();
  };

  D.line = function (g, x1, y1, x2, y2, o = {}) {
    g.save();
    g.strokeStyle = o.color || '#000';
    g.lineWidth = o.lw || 1;
    g.lineCap = o.cap || 'round';
    if (o.dash) g.setLineDash(o.dash);
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.beginPath(); g.moveTo(x1, y1); g.lineTo(x2, y2); g.stroke();
    g.restore();
  };

  D.poly = function (g, pts, o = {}) {
    if (!pts.length) return;
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.beginPath();
    pts.forEach((p, i) => (i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])));
    if (o.close) g.closePath();
    if (o.fill) { g.fillStyle = o.fill; g.fill(); }
    if (o.color) {
      g.strokeStyle = o.color; g.lineWidth = o.lw || 1.5; g.lineJoin = 'round'; g.lineCap = 'round';
      if (o.dash) g.setLineDash(o.dash);
      g.stroke();
    }
    g.restore();
  };

  function head(g, x, y, ang, size, color) {
    g.save();
    g.translate(x, y); g.rotate(ang);
    g.beginPath(); g.moveTo(0, 0); g.lineTo(-size, -size * 0.55); g.lineTo(-size, size * 0.55); g.closePath();
    g.fillStyle = color; g.fill();
    g.restore();
  }

  D.arrow = function (g, x1, y1, x2, y2, o = {}) {
    const size = o.head || 8, color = o.color || '#000';
    const ang = Math.atan2(y2 - y1, x2 - x1);
    const ex = x2 - Math.cos(ang) * size * 0.8, ey = y2 - Math.sin(ang) * size * 0.8;
    D.line(g, x1, y1, ex, ey, o);
    g.save(); if (o.alpha != null) g.globalAlpha *= o.alpha; head(g, x2, y2, ang, size, color); g.restore();
  };

  /** Flecha curva (Bézier cuadrática) con punta. */
  D.curveArrow = function (g, x1, y1, cx, cy, x2, y2, o = {}) {
    const size = o.head || 8, color = o.color || '#000';
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.strokeStyle = color; g.lineWidth = o.lw || 1.5; g.lineCap = 'round';
    if (o.dash) g.setLineDash(o.dash);
    g.beginPath(); g.moveTo(x1, y1); g.quadraticCurveTo(cx, cy, x2, y2); g.stroke();
    g.setLineDash([]);
    head(g, x2, y2, Math.atan2(y2 - cy, x2 - cx), size, color);
    g.restore();
  };

  /** Punto en una Bézier cuadrática (para partículas que viajan por curvas). */
  D.qpoint = (x1, y1, cx, cy, x2, y2, t) => {
    const u = 1 - t;
    return [u * u * x1 + 2 * u * t * cx + t * t * x2, u * u * y1 + 2 * u * t * cy + t * t * y2];
  };

  D.text = function (g, str, x, y, o = {}) {
    g.save();
    g.font = D.font(o.size || 12, o.weight || 500, o.mono);
    g.fillStyle = o.color || '#000';
    g.textAlign = o.align || 'left';
    g.textBaseline = o.base || 'alphabetic';
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.fillText(str, x, y, o.maxWidth);
    g.restore();
  };

  /** Etiqueta con fondo tipo píldora. Devuelve {w, h}. */
  D.label = function (g, str, x, y, o = {}) {
    const size = o.size || 11, pad = o.pad == null ? 6 : o.pad;
    g.save();
    g.font = D.font(size, o.weight || 600, o.mono);
    const w = g.measureText(str).width + pad * 2, h = size + pad * 1.2;
    let bx = x;
    if (o.align === 'center') bx = x - w / 2; else if (o.align === 'right') bx = x - w;
    const by = y - h / 2;
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    D.rrect(g, bx, by, w, h, o.radius == null ? h / 2 : o.radius);
    g.fillStyle = o.bg || '#fff'; g.fill();
    if (o.border) { g.strokeStyle = o.border; g.lineWidth = 1; g.stroke(); }
    g.fillStyle = o.color || '#000'; g.textAlign = 'left'; g.textBaseline = 'middle';
    g.fillText(str, bx + pad, y + 0.5);
    g.restore();
    return { w, h, x: bx, y: by };
  };

  /**
   * Ejes con rejilla. box = {x, y, w, h}; sx/sy = escalas de Hub.util.scale.
   * o = {c: colores, xt, yt (marcas), fx, fy (formato), xlabel, ylabel, grid: true}
   */
  D.axes = function (g, box, sx, sy, o = {}) {
    const c = o.c;
    const size = o.size || 10;
    g.save();
    if (o.grid !== false) {
      g.strokeStyle = c.grid; g.lineWidth = 1;
      (o.xt || []).forEach(t => { const x = Math.round(sx(t)) + 0.5; g.beginPath(); g.moveTo(x, box.y); g.lineTo(x, box.y + box.h); g.stroke(); });
      (o.yt || []).forEach(t => { const y = Math.round(sy(t)) + 0.5; g.beginPath(); g.moveTo(box.x, y); g.lineTo(box.x + box.w, y); g.stroke(); });
    }
    g.strokeStyle = c.axis; g.lineWidth = 1;
    g.beginPath(); g.moveTo(box.x, box.y + box.h + 0.5); g.lineTo(box.x + box.w, box.y + box.h + 0.5);
    g.moveTo(box.x - 0.5, box.y); g.lineTo(box.x - 0.5, box.y + box.h); g.stroke();
    g.font = D.font(size, 500); g.fillStyle = c.text;
    g.textAlign = 'center'; g.textBaseline = 'top';
    (o.xt || []).forEach(t => g.fillText(o.fx ? o.fx(t) : String(t), sx(t), box.y + box.h + 5));
    g.textAlign = 'right'; g.textBaseline = 'middle';
    (o.yt || []).forEach(t => g.fillText(o.fy ? o.fy(t) : String(t), box.x - 6, sy(t)));
    if (o.xlabel) { g.textAlign = 'center'; g.textBaseline = 'top'; g.font = D.font(size, 600); g.fillText(o.xlabel, box.x + box.w / 2, box.y + box.h + size + 9); }
    if (o.ylabel) {
      g.save(); g.translate(box.x - (o.ylabelGap || 34), box.y + box.h / 2); g.rotate(-Math.PI / 2);
      g.textAlign = 'center'; g.textBaseline = 'bottom'; g.font = D.font(size, 600); g.fillText(o.ylabel, 0, 0); g.restore();
    }
    g.restore();
  };

  /** Candado (abierto/cerrado) para conjuntos de prueba. */
  D.lock = function (g, x, y, s, color, open = false) {
    g.save();
    g.strokeStyle = color; g.fillStyle = color; g.lineWidth = Math.max(1.5, s * 0.16);
    g.beginPath();
    const r = s * 0.36;
    if (open) g.arc(x - s * 0.34, y - s * 0.12, r, Math.PI, 0);
    else g.arc(x, y - s * 0.12, r, Math.PI, 0);
    g.stroke();
    D.rrect(g, x - s * 0.5, y - s * 0.12, s, s * 0.78, s * 0.14);
    g.fill();
    g.restore();
  };

  D.check = function (g, x, y, s, color, lw = 2.2) {
    D.poly(g, [[x - s * 0.5, y], [x - s * 0.12, y + s * 0.38], [x + s * 0.55, y - s * 0.42]], { color, lw });
  };
  D.cross = function (g, x, y, s, color, lw = 2.2) {
    D.line(g, x - s / 2, y - s / 2, x + s / 2, y + s / 2, { color, lw });
    D.line(g, x + s / 2, y - s / 2, x - s / 2, y + s / 2, { color, lw });
  };

  /**
   * Mapa de calor suavizado sobre `box`. fn(u, v) → [r, g, b(, a)] con u, v ∈ [0, 1] (v = 0 arriba).
   * Se calcula en una rejilla pequeña (o.nx × o.ny) y se escala con interpolación.
   * Caché opcional: o.store (objeto del estado) + o.version → solo recalcula cuando cambia la versión.
   */
  const heatPool = {};
  D.heat = function (g, box, fn, o = {}) {
    const nx = o.nx || 72, ny = o.ny || Math.max(8, Math.round((nx * box.h) / Math.max(1, box.w)));
    let cv;
    if (o.store && o.store.cv && o.store.v === o.version && o.store.cv.width === nx && o.store.cv.height === ny) cv = o.store.cv;
    else {
      if (o.store) { cv = o.store.cv && o.store.cv.width === nx && o.store.cv.height === ny ? o.store.cv : document.createElement('canvas'); o.store.cv = cv; o.store.v = o.version; }
      else cv = heatPool[nx + 'x' + ny] || (heatPool[nx + 'x' + ny] = document.createElement('canvas'));
      if (cv.width !== nx || cv.height !== ny) { cv.width = nx; cv.height = ny; }
      const cx = cv.getContext('2d');
      const img = cx.createImageData(nx, ny), d = img.data;
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
        const col = fn((i + 0.5) / nx, (j + 0.5) / ny), k = (j * nx + i) * 4;
        d[k] = col[0]; d[k + 1] = col[1]; d[k + 2] = col[2]; d[k + 3] = col[3] == null ? 255 : col[3];
      }
      cx.putImageData(img, 0, 0);
    }
    g.save();
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.imageSmoothingEnabled = o.smooth !== false;
    g.imageSmoothingQuality = 'high';
    g.drawImage(cv, box.x, box.y, box.w, box.h);
    g.restore();
  };
  /** Rampa divergente para probabilidades: p = 0 → c0, p = 0.5 → bg, p = 1 → c1 (intensidad máxima k). */
  D.probRamp = function (c0, c1, bg, k = 0.5) {
    const A = D.rgb(c0), B = D.rgb(c1), N = D.rgb(bg);
    return p => {
      const t = Math.min(1, Math.abs(p - 0.5) * 2) * k, C = p >= 0.5 ? B : A;
      return [N[0] + (C[0] - N[0]) * t, N[1] + (C[1] - N[1]) * t, N[2] + (C[2] - N[2]) * t];
    };
  };
  /** Rampa secuencial: t ∈ [0, 1] de bg hacia col (intensidad máxima k). */
  D.seqRamp = function (col, bg, k = 0.6) {
    const B = D.rgb(col), N = D.rgb(bg);
    return t => { t = Math.min(1, Math.max(0, t)) * k; return [N[0] + (B[0] - N[0]) * t, N[1] + (B[1] - N[1]) * t, N[2] + (B[2] - N[2]) * t]; };
  };
  /** Segmentos de contorno (Hub.ml.contour) llevados a píxeles con tx(i), ty(j). */
  D.segs = function (g, segs, tx, ty, o = {}) {
    if (!segs.length) return;
    g.save();
    g.strokeStyle = o.color || '#000'; g.lineWidth = o.lw || 1; g.lineCap = 'round';
    if (o.dash) g.setLineDash(o.dash);
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    g.beginPath();
    for (const s of segs) { g.moveTo(tx(s[0]), ty(s[1])); g.lineTo(tx(s[2]), ty(s[3])); }
    g.stroke();
    g.restore();
  };

  /** Texto multilínea con ajuste por ancho. Devuelve la altura usada. */
  D.wrap = function (g, str, x, y, maxW, o = {}) {
    const size = o.size || 12, lh = o.lh || size * 1.4;
    g.save();
    g.font = D.font(size, o.weight || 400, o.mono);
    g.fillStyle = o.color || '#000'; g.textAlign = o.align || 'left'; g.textBaseline = 'top';
    if (o.alpha != null) g.globalAlpha *= o.alpha;
    const words = [];
    for (const w of String(str).split(/\s+/)) {          // una palabra más ancha que la línea se parte por caracteres
      if (g.measureText(w).width <= maxW) { words.push(w); continue; }
      let chunk = '';
      for (const ch of w) { if (g.measureText(chunk + ch).width > maxW && chunk) { words.push(chunk); chunk = ch; } else chunk += ch; }
      if (chunk) words.push(chunk);
    }
    let line = '', yy = y;
    for (const w of words) {
      const test = line ? line + ' ' + w : w;
      if (g.measureText(test).width > maxW && line) { g.fillText(line, x, yy); line = w; yy += lh; }
      else line = test;
    }
    if (line) g.fillText(line, x, yy);
    g.restore();
    return yy - y + lh;
  };
})();
