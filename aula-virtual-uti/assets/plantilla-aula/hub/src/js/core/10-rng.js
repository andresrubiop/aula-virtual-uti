/* Generador pseudoaleatorio con semilla (mulberry32): las animaciones son reproducibles.
   const r = Hub.rng(2026); r.next(); r.normal(0, 1); r.int(1, 6); r.shuffle(arr) */
(function () {
  'use strict';
  window.Hub.rng = function (seed = 2026) {
    let a = seed >>> 0;
    let spare = null;
    const next = () => {
      a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const r = {
      next,
      float: (lo = 0, hi = 1) => lo + (hi - lo) * next(),
      int: (lo, hi) => Math.floor(lo + (hi - lo + 1) * next()),
      bool: (p = 0.5) => next() < p,
      pick: arr => arr[Math.floor(next() * arr.length)],
      normal(mu = 0, sd = 1) {
        if (spare !== null) { const s = spare; spare = null; return mu + sd * s; }
        let u = 0, v = 0;
        while (u === 0) u = next();
        while (v === 0) v = next();
        const m = Math.sqrt(-2 * Math.log(u));
        spare = m * Math.sin(2 * Math.PI * v);
        return mu + sd * m * Math.cos(2 * Math.PI * v);
      },
      shuffle(arr) {
        for (let i = arr.length - 1; i > 0; i--) {
          const j = Math.floor(next() * (i + 1));
          [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
      },
      seed: () => a,
    };
    return r;
  };
})();
