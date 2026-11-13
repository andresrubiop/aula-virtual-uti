/* Portada: ilustración viva del curso (opcional).
   Por omisión la portada no lleva animación. Si el curso quiere una (como el planificador de CPU del aula de
   Sistemas Operativos), aquí se define Hub.hero.init() y en content/00-inicio.html se agrega
   <div class="hero-viz" data-hero><canvas></canvas><div class="hero-viz__cap">…</div></div>.
   Regla: debe ser una simulación real del tema central del curso (Hub.rng con semilla, Hub.draw, colores de
   Hub.colors), pausarse cuando no se ve (IntersectionObserver) y respetar prefers-reduced-motion. */
(function () {
  'use strict';
  window.Hub.hero = { init() { /* sin portada animada */ } };
})();
