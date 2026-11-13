/* A1.1 · La curva del olvido y el repaso espaciado (animación de EJEMPLO de la plantilla).
   Modelo ilustrativo R(t) = exp(-(t - último repaso) / S); cada repaso multiplica la estabilidad S por un factor.
   Es el mismo cálculo de practicas/pr1/repaso.py: la animación y la práctica dan las mismas cifras.
   Sirve de modelo para las animaciones del curso: escenas con nota que explica lo que se ve, controles que
   rehacen el cálculo, métricas en vivo, textos en español e inglés y colores solo de api.c. */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { L } = Hub.i18n;
  const D = Hub.draw;
  const DAYS = 30;
  const PLANS = [[], [1], [1, 3, 7, 14], [29]];
  const pct = (x, l) => Hub.i18n.num(x * 100, 1, l) + ' %';

  function retention(plan, s0, factor, day) {
    let s = s0, last = 0;
    for (const r of plan) { if (r > day) break; s *= factor; last = r; }
    return Math.exp(-(day - last) / s);
  }

  Hub.anim.define({
    id: 'A1.1',
    title: L('La curva del olvido y el repaso espaciado', 'The forgetting curve and spaced review'),
    subtitle: L('Cuánto recuerdas cada día según cuándo repasas. Modelo ilustrativo: <code>R = exp(−t/S)</code>; cada repaso multiplica la estabilidad <code>S</code>.',
      'How much you remember each day depending on when you review. Illustrative model: <code>R = exp(−t/S)</code>; each review multiplies the stability <code>S</code>.'),
    theory: { label: 'M1 §1', href: '#/u1/manual/m1-1' },
    practice: { label: 'PR1 · 1', href: '#/u1/practica/pr1-1' },
    aspect: 2.1, aspectNarrow: 1.1,
    controls: [
      { id: 's0', type: 'range', label: L('Estabilidad inicial (días)', 'Initial stability (days)'), min: 1, max: 6, step: 0.5, value: 2 },
      { id: 'factor', type: 'range', label: L('Efecto de cada repaso (×)', 'Effect of each review (×)'), min: 1.5, max: 3.5, step: 0.5, value: 2.5, compact: false },
    ],
    scenes: [
      { title: L('Sin repasos', 'No reviews'), dur: 6,
        text: (S, api) => L(`Estudias una vez y no vuelves al tema. Con una estabilidad de ${Hub.i18n.num(api.p.s0, 1, 'es')} días, el día 30 queda el <b>${pct(S.end, 'es')}</b>: la caída es rápida al principio y luego se frena.`,
          `You study once and never come back to the topic. With a stability of ${Hub.i18n.num(api.p.s0, 1, 'en')} days, on day 30 <b>${pct(S.end, 'en')}</b> is left: the drop is fast at first and then slows down.`) },
      { title: L('Un repaso', 'One review'), dur: 6,
        text: S => L(`Un solo repaso al día siguiente vuelve a subir el recuerdo y hace más lenta la caída, pero no alcanza: el día 30 queda el <b>${pct(S.end, 'es')}</b>.`,
          `A single review the next day brings the memory back up and slows the drop, but it is not enough: on day 30 <b>${pct(S.end, 'en')}</b> is left.`) },
      { title: L('Repaso espaciado', 'Spaced review'), dur: 8,
        text: S => L(`Cuatro repasos a intervalos crecientes (días 1, 3, 7 y 14). Cada uno llega cuando el recuerdo empieza a caer y lo deja más estable: el día 30 queda el <b>${pct(S.end, 'es')}</b>.`,
          `Four reviews at growing intervals (days 1, 3, 7 and 14). Each one arrives when the memory starts to drop and leaves it more stable: on day 30 <b>${pct(S.end, 'en')}</b> is left.`) },
      { title: L('Todo la víspera', 'Everything the night before'), dur: 7,
        text: S => L(`Un único repaso el día 29 también da un número alto el día 30 (<b>${pct(S.end, 'es')}</b>), pero mira el área bajo la curva: casi todo el mes no lo sabías, y con tan poca estabilidad se pierde enseguida.`,
          `A single review on day 29 also gives a high number on day 30 (<b>${pct(S.end, 'en')}</b>), but look at the area under the curve: for most of the month you did not know it, and with so little stability it is lost right away.`) },
    ],
    observe: [
      L('Mueve la estabilidad inicial: ¿qué plan depende más de ella?', 'Move the initial stability: which plan depends on it the most?'),
      L('Compara el promedio del mes entre «espaciado» y «todo la víspera».', 'Compare the monthly average between "spaced" and "everything the night before".'),
    ],

    init(S) { S.plan = PLANS[0]; S.t = 0; S.end = 0; S.avg = 0; },
    scene(S, i, api) {
      api.clearTweens();
      S.plan = PLANS[i];
      S.t = 0;
      this.recalc(S, api);
      api.tween(S, { t: DAYS }, 4, { ease: 'linear', ui: false });
    },
    recalc(S, api) {
      S.end = retention(S.plan, api.p.s0, api.p.factor, DAYS);
      let sum = 0;
      for (let d = 0; d <= DAYS * 4; d++) sum += retention(S.plan, api.p.s0, api.p.factor, d / 4);
      S.avg = sum / (DAYS * 4 + 1);
    },
    control(S, id, v, api) { this.recalc(S, api); api.redraw(); },

    draw(S, g, api) {
      const c = api.c, W = api.w, H = api.h;
      const fs = Math.max(10, Math.min(13, W / 60));
      g.fillStyle = c.plotBg; g.fillRect(0, 0, W, H);
      const box = { x: 46, y: 16, w: W - 66, h: H - 56 };
      const sx = d => box.x + (d / DAYS) * box.w, sy = r => box.y + (1 - r) * box.h;
      g.strokeStyle = c.grid; g.lineWidth = 1;
      for (let r = 0; r <= 1.001; r += 0.25) {
        g.beginPath(); g.moveTo(box.x, sy(r)); g.lineTo(box.x + box.w, sy(r)); g.stroke();
        D.text(g, Math.round(r * 100) + ' %', box.x - 6, sy(r) + 4, { size: fs - 2, color: c.text, align: 'right' });
      }
      for (let d = 0; d <= DAYS; d += 5) D.text(g, String(d), sx(d), box.y + box.h + 16, { size: fs - 2, color: c.text, align: 'center' });
      D.text(g, api.t('días desde que estudiaste', 'days since you studied'), box.x + box.w / 2, box.y + box.h + 34, { size: fs - 1, color: c.text, align: 'center' });
      // repasos (líneas verticales) y curva hasta el día S.t
      S.plan.forEach(r => {
        if (r > S.t) return;
        D.line(g, sx(r), box.y, sx(r), box.y + box.h, { color: c.c2, width: 1.5, dash: [4, 4] });
        D.label(g, api.t('repaso', 'review'), sx(r) + 4, box.y + 12, { size: fs - 2, bg: c.c2, color: '#FFFFFF' });
      });
      const pts = [];
      for (let d = 0; d <= S.t; d += 0.1) pts.push([sx(d), sy(retention(S.plan, api.p.s0, api.p.factor, d))]);
      if (pts.length > 1) D.poly(g, pts, { color: c.c1, width: 3 });
      const now = retention(S.plan, api.p.s0, api.p.factor, S.t);
      D.dot(g, sx(S.t), sy(now), 5, { fill: c.c1 });
      api.metrics([
        { k: L('Día', 'Day'), v: Hub.i18n.num(S.t, 0) },
        { k: L('Recuerdas ahora', 'You remember now'), v: pct(now), tone: now > 0.6 ? 'ok' : now > 0.3 ? 'warn' : 'err' },
        { k: L('El día 30', 'On day 30'), v: pct(S.end), tone: 'c1' },
        { k: L('Promedio del mes', 'Monthly average'), v: pct(S.avg), tone: 'c2' },
      ]);
    },
  });
})();
