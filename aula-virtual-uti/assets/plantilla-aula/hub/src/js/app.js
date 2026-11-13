/* Arranque del hub. Se ejecuta al final, cuando todo el contenido y los módulos ya existen. */
(function () {
  'use strict';
  const Hub = window.Hub;
  const toggle = document.getElementById('theme-toggle');
  if (toggle) toggle.addEventListener('click', () => Hub.theme.toggle());

  // Idioma: botones ES / EN de la cabecera
  Hub.i18n.init();
  const langBtns = document.querySelectorAll('[data-set-lang]');
  const paintLang = () => langBtns.forEach(b => b.setAttribute('aria-pressed', b.dataset.setLang === Hub.i18n.lang ? 'true' : 'false'));
  langBtns.forEach(b => b.addEventListener('click', () => Hub.i18n.set(b.dataset.setLang)));
  Hub.on('lang', paintLang);
  paintLang();

  // Logos institucionales reutilizados sin duplicar el data URI: <img data-logo="blanco|color">
  const logos = { blanco: document.querySelector('.brand__logo--dark'), color: document.querySelector('.brand__logo--light') };
  document.querySelectorAll('img[data-logo]').forEach(img => { const src = logos[img.dataset.logo]; if (src) img.src = src.src; });

  Hub.code.init(document);
  Hub.pager.init();
  Hub.progress.init();
  Hub.countdown.init();
  Hub.glossary.init();
  if (Hub.hero) Hub.hero.init();   // portada animada propia del curso (opcional: components/60-hero.js)
  Hub.media.init();

  // Montaje perezoso: fórmulas, animaciones, presentaciones y cuestionarios solo en la vista visible.
  Hub.on('route', ({ el }) => {
    Hub.math.render(el);
    Hub.deck.mountAll(el);
    Hub.ink.mountAll(el);
    Hub.quiz.mountAll(el);
    Hub.anim.mountAll(el);
  });

  if (!location.hash || !location.hash.startsWith('#/')) history.replaceState(null, '', '#/inicio');
  Hub.router.apply();
  document.documentElement.classList.add('hub-ready');
})();
