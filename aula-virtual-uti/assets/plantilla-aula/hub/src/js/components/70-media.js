/* Medios externos al HTML: videos (carpeta videos/), enlaces al repositorio y PDF de materiales.
 * Videos bilingües: una entrada de videos.js puede ser {src, …} (un solo idioma) o {es: {src, …}, en: {src, …}};
 * con los dos idiomas se montan dos reproductores y el CSS muestra el del idioma activo.
 *
 * Videos:   <div class="video-poster" data-video="V1.1">…póster…</div>
 *   Se carga <videos_base>/videos.js (window.HUB_VIDEOS) y cada póster configurado se reemplaza por un
 *   reproductor. videos_base viene de hub/config.json o del parámetro ?videos=RUTA de la URL.
 *   Entrada {"embed": true}: el MP4 va dentro del propio HTML, en <script type="application/octet-stream"
 *   id="hub-video-V1.1"> (base64) al final del documento (aula para Blackboard, Blackboard/build.py). Se
 *   decodifica recién al pulsar el póster, así el aula abre y funciona mientras los videos terminan de bajar.
 * Notebooks: <a class="btn" data-colab="semana-1/E1.1_x.ipynb">…</a> · <a class="btn" data-github="…">…</a>
 *   Se activan si hub/config.json define repo_estudiantes (https://github.com/usuario/repo).
 */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { h, $$ } = Hub.util;
  const I = Hub.i18n;
  const { L } = I;
  const CFG = window.HUB_CONFIG || {};

  function videosBase() {
    try {
      const q = new URLSearchParams(location.search).get('videos');
      if (q) return q.endsWith('/') ? q : q + '/';
    } catch (e) { /* nada */ }
    const b = CFG.videos_base || 'videos/';
    return b.endsWith('/') ? b : b + '/';
  }

  function youtubeId(url) {
    const m = String(url).match(/(?:youtu\.be\/|v=|embed\/)([\w-]{6,})/);
    return m ? m[1] : null;
  }

  function markCard(poster, estado, texto) {
    const card = poster.closest('.res-card');
    const st = card && card.querySelector('.status');
    if (st) { st.className = 'status status--' + estado; st.innerHTML = I.html(texto); }
  }

  const READY = L('Disponible · generado con NotebookLM y revisado por el docente', 'Available · generated with NotebookLM and reviewed by the instructor');

  function mountVideo(poster, id, entry, base) {
    const title = I.text(poster.querySelector('.video-poster__title')) || id;
    const langs = entry.es || entry.en ? entry : { es: entry };
    const nodes = I.LANGS.filter(l => langs[l]).map(l => {
      const n = player(poster, id, title, langs[l], base, l);
      return I.LANGS.filter(x => langs[x]).length > 1 ? h('div', { lang: l }, n) : n;
    });
    // Un solo idioma: aviso en los demás (el texto del idioma del video queda vacío)
    if (nodes.length === 1 && !langs.en) nodes.push(h('p', { class: 'muted video-lang-note', html: I.html(L('', 'Video available in Spanish only.')) }));
    if (nodes.length === 1 && langs.en && !langs.es) nodes.push(h('p', { class: 'muted video-lang-note', html: I.html(L('Video disponible solo en inglés.', '',
      { fr: 'Vidéo disponible en anglais uniquement.', ca: 'Vídeo disponible només en anglès.', ja: '動画は英語版のみです。' })) }));
    const box = h('div', { class: 'video-box' }, nodes);
    poster.replaceWith(box);
    markCard(box, 'listo', READY);
  }

  const SUB_LABEL = { es: 'Español', en: 'English', fr: 'Français', ca: 'Català', ja: '日本語' };
  // Al cambiar el idioma del aula, los subtítulos cambian con él (el estudiante puede elegir otros en el reproductor)
  function syncSubs() {
    $$('video[data-subs]').forEach(v => [...v.textTracks].forEach(tr => {
      if (tr.kind === 'subtitles') tr.mode = tr.language === I.lang ? 'showing' : 'disabled';
    }));
  }

  // Los subtítulos llegan como script (V1.1.en.subs.js, de hub/tools/subtitulos.py) y no como <track src>: Chrome no
  // carga <track> si el aula se abre como archivo (file://) ni desde otro origen sin CORS (la plantilla de Classroom).
  // Se cargan cuando el video aparece en pantalla (las unidades ocultas no piden nada).
  const subsScripts = {};
  const subsLater = typeof IntersectionObserver === 'undefined' ? null : new IntersectionObserver(es => es.forEach(en => {
    if (en.isIntersecting) { subsLater.unobserve(en.target); en.target._loadSubs(); }
  }), { rootMargin: '400px' });
  function loadSubs(video, src, key) {
    video._loadSubs = () => addSubs(video, src, key);
    if (subsLater) subsLater.observe(video); else video._loadSubs();
  }
  function addSubs(video, src, key) {
    subsScripts[src] = subsScripts[src] || new Promise(ok => {
      const s = h('script', { src });
      s.onload = s.onerror = () => ok();
      document.head.append(s);
    });
    subsScripts[src].then(() => {
      const all = (window.HUB_SUBS || {})[key];
      if (!all || typeof VTTCue === 'undefined') return;
      for (const [sl, cues] of Object.entries(all)) {
        const tr = video.addTextTrack('subtitles', SUB_LABEL[sl] || sl, sl);
        cues.forEach(([a, b, t]) => tr.addCue(new VTTCue(a, b, t)));
        tr.mode = sl === I.lang ? 'showing' : 'disabled';
      }
    });
  }

  function player(poster, id, title, e, base, lang) {
    let node;
    if (e.url) {
      const yt = youtubeId(e.url);
      node = yt
        ? h('iframe', { class: 'video-frame', src: `https://www.youtube-nocookie.com/embed/${yt}`, title: `${id} · ${title}`, loading: 'lazy', allow: 'fullscreen; picture-in-picture', allowfullscreen: true })
        : h('iframe', { class: 'video-frame', src: e.url, title: `${id} · ${title}`, loading: 'lazy', allowfullscreen: true });
    } else {
      const at = f => /^https?:\/\//.test(f) ? f : base + f;   // una URL absoluta (p. ej. GitHub Releases) no lleva la carpeta de videos delante
      node = h('video', { class: 'video-frame', controls: true, preload: 'metadata', playsinline: true, 'aria-label': `${id} · ${title}`, poster: e.poster ? at(e.poster) : null });
      node.append(h('source', { src: at(e.src) }));
      // Subtítulos: una cadena (un idioma, el del video) o {es: …, en: …, fr: …} (varios). Se muestra el del idioma
      // activo del aula (si no hay, ninguno: el estudiante puede elegir otro en el menú del reproductor)
      const subs = typeof e.subtitulos === 'string' ? { [lang]: e.subtitulos } : (e.subtitulos || {});
      if (e.subtitulos_js) loadSubs(node, at(e.subtitulos_js), `${id}.${lang}`);
      else for (const [sl, src] of Object.entries(subs)) {
        node.append(h('track', { kind: 'subtitles', srclang: sl, label: SUB_LABEL[sl] || sl, src: at(src), default: sl === I.lang }));
      }
      if (Object.keys(subs).length) node.dataset.subs = '1';
      const fail = () => {
        if (!node.isConnected) return;
        const box = node.closest('.video-box');
        (box || node).replaceWith(poster);
        markCard(poster, 'produccion', L(`No se encontró ${e.src} en la carpeta de videos`, `${e.src} was not found in the videos folder`,
          { fr: `${e.src} est introuvable dans le dossier des vidéos`, ca: `No s’ha trobat ${e.src} a la carpeta de vídeos`, ja: `動画フォルダに ${e.src} が見つかりません` }));
      };
      node.querySelector('source').addEventListener('error', fail);
      node.addEventListener('error', fail);
    }
    return node;
  }

  // MP4 incrustado en base64: se convierte en un Blob una sola vez y se libera el texto
  function embeddedUrl(id) {
    const s = document.getElementById('hub-video-' + id);
    if (!s) return null;                                   // todavía no terminó de bajar esa parte del HTML
    if (!s._url) {
      const bin = atob(s.textContent.replace(/\s+/g, ''));
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      s._url = URL.createObjectURL(new Blob([bytes], { type: s.dataset.type || 'video/mp4' }));
      s.textContent = '';
    }
    return s._url;
  }

  function mountEmbedded(poster, id) {
    const title = I.text(poster.querySelector('.video-poster__title')) || id;
    const badge = poster.querySelector('.video-poster__badge');
    if (badge) badge.innerHTML = I.html(L('▶ Reproducir', '▶ Play'));
    poster.classList.add('video-poster--play');
    poster.setAttribute('role', 'button');
    poster.tabIndex = 0;
    I.bind(poster, 'aria-label', L(`Reproducir ${id} · ${title}`, `Play ${id} · ${title}`, { fr: `Lire ${id} · ${title}`, ca: `Reprodueix ${id} · ${title}`, ja: `再生：${id} · ${title}` }));
    markCard(poster, 'listo', READY);
    let started = false;
    const play = () => {
      const url = embeddedUrl(id);
      if (!url) {                                          // el aula ya funciona, pero ese video aún está llegando
        if (badge) badge.innerHTML = I.html(L('Cargando…', 'Loading…'));
        setTimeout(play, 700);
        return;
      }
      const node = h('video', { class: 'video-frame', controls: true, autoplay: true, playsinline: true, src: url, 'aria-label': `${id} · ${title}` });
      poster.replaceWith(node);
      node.focus();
    };
    const start = () => { if (!started) { started = true; play(); } };
    poster.addEventListener('click', start);
    poster.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); start(); } });
  }

  function applyVideos(base) {
    const cfg = window.HUB_VIDEOS || {};
    $$('.video-poster[data-video]').forEach(p => {
      const e = cfg[p.dataset.video];
      // entrada de un solo video ({src} o {url}) o por idioma ({es: {…}, en: {…}}, la que escribe hub/tools/videos.py)
      if (e && (e.src || e.url || e.es || e.en)) mountVideo(p, p.dataset.video, e, base);
      else if (e && e.embed) mountEmbedded(p, p.dataset.video);
    });
  }

  function applyNotebooks() {
    const repo = (CFG.repo_estudiantes || '').replace(/\/+$/, '');
    const m = repo.match(/github\.com\/([^/]+)\/([^/]+)/);
    if (!m) return;
    const [, owner, name] = m, branch = CFG.rama || 'main';
    $$('[data-colab]').forEach(a => {
      a.href = `https://colab.research.google.com/github/${owner}/${name}/blob/${branch}/${a.dataset.colab}`;
      a.innerHTML = I.html(a.dataset.label || L('Abrir en Colab', 'Open in Colab'));
      a.target = '_blank'; a.rel = 'noopener'; a.removeAttribute('aria-disabled');
    });
    $$('[data-github]').forEach(a => {
      a.href = `${repo}/blob/${branch}/${a.dataset.github}`;
      a.innerHTML = a.dataset.label ? Hub.util.escape(a.dataset.label) : I.html(L('Ver en GitHub', 'View on GitHub'));
      a.target = '_blank'; a.rel = 'noopener'; a.removeAttribute('aria-disabled');
    });
  }

  // PDF de manuales y presentaciones: <a data-material="unidad-1/M1_manual.pdf">. En otro idioma se abre
  // M1_manual.en.pdf, .fr.pdf, .ca.pdf o .ja.pdf (hub/tools/pdfs.sh los genera); francés, catalán y japonés solo
  // si la unidad está traducida (data-l10n de su vista), si no, el inglés. Se actualiza al cambiar de idioma.
  // Versión autónoma de un solo archivo (hub/tools/autonomo.py, materiales_base = "imprimir"): no hay carpeta de PDF,
  // así que el botón imprime la vista de ese material (manual, presentación o laboratorio) y el navegador la guarda
  // en PDF. La presentación se prepara como hub/tools/check.mjs --deck: una diapositiva 16:9 por página.
  async function printMaterial(m) {
    const u = /unidad-(\d+)\/[^/]*_(manual|presentacion|practica|laboratorio)/.exec(m);
    if (!u) return;
    const vista = document.querySelector(`.view[data-view="u${u[1]}"]`);
    // la práctica de la unidad puede llamarse practica, laboratorio o actividad (según los archivos de la unidad)
    const sub = u[2] === 'manual' || u[2] === 'presentacion' ? u[2]
      : ['practica', 'laboratorio', 'actividad'].find(s => vista && vista.querySelector(`.sub[data-sub="${s}"]`)) || u[2];
    const deck = u[2] === 'presentacion';
    location.hash = `#/u${u[1]}/${sub}`;
    await new Promise(r => setTimeout(r, 900));
    const theme = document.documentElement.dataset.theme, root = document.documentElement;
    Hub.theme.set('light');
    document.querySelectorAll('details').forEach(d => { d.open = true; });
    let pg = null;
    if (deck) {
      root.classList.add('print-deck');
      pg = document.createElement('style'); pg.textContent = '@page { size: 297mm 167.06mm; margin: 0; }'; document.head.append(pg);
      const view = document.querySelector(`.view[data-view="u${u[1]}"]`) || document;   // solo esta presentación
      view.querySelectorAll('.slide [data-anim]').forEach(a => { if (!a.hasAttribute('data-mounted')) Hub.anim.mount(a); });
      view.querySelectorAll('.slide').forEach(sl => { if (Hub.math) Hub.math.render(sl); });
      await document.fonts.ready;
      await new Promise(r => setTimeout(r, 1200));
      view.querySelectorAll('.slide [data-anim]').forEach(a => { if (a._stage) a._stage.still(...(a.dataset.print || '0:0').split(':').map(Number)); });
    }
    const restore = () => {
      root.classList.remove('print-deck'); if (pg) pg.remove();
      if (theme) Hub.theme.set(theme);
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.print();
  }

  function applyMateriales() {
    if (CFG.materiales_base === 'imprimir') {
      $$('[data-material]').forEach(a => {
        a.href = '#'; a.removeAttribute('target');
        a.title = I.t('Se abre la impresión: elige «Guardar como PDF»', 'Opens printing: choose "Save as PDF"',
          { fr: 'Ouvre l’impression : choisissez « Enregistrer au format PDF »', ca: 'S’obre la impressió: tria «Desa com a PDF»', ja: '印刷が開きます：「PDF に保存」を選んでください' });
        if (!a.dataset.printBound) { a.dataset.printBound = '1'; a.addEventListener('click', ev => { ev.preventDefault(); printMaterial(a.dataset.material); }); }
      });
      return;
    }
    let base = CFG.materiales_base || 'materiales/';
    if (!base.endsWith('/')) base += '/';
    const l = I.lang;
    $$('[data-material]').forEach(a => {
      const m = a.dataset.material;
      const sfx = l === 'es' ? '' : '.en';
      a.href = base + m.replace(/\.pdf$/, sfx + '.pdf');
      a.target = '_blank'; a.rel = 'noopener';
    });
  }

  // Un PDF incrustado (data URI, como el informe de ejemplo del TD0) se abre en una pestaña nueva como blob: los
  // navegadores no abren un data: arriba. Se decodifica en el mismo clic, para que no lo frene el bloqueador de ventanas.
  function openData(a, ev) {
    const m = /^data:([^;,]+);base64,(.*)$/.exec(a.getAttribute('href') || '');
    if (!m) return;
    ev.preventDefault();
    const bin = atob(m[2]), u8 = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    window.open(URL.createObjectURL(new Blob([u8], { type: m[1] })), '_blank');
  }

  Hub.media = {
    init() {
      // La plantilla y el ejemplo del informe van incrustados una vez (pestaña Tarea de la U1); las demás unidades los copian
      $$('a[data-igual]').forEach(a => { const src = document.getElementById(a.dataset.igual); if (src) a.href = src.getAttribute('href'); });
      $$('a[data-abrir]').forEach(a => a.addEventListener('click', ev => openData(a, ev)));
      applyNotebooks();
      applyMateriales();
      Hub.on('lang', applyMateriales);
      Hub.on('lang', syncSubs);
      if (!$$('.video-poster[data-video]').length) return;
      if (CFG.videos_base === '') return;   // versión autónoma de un solo archivo: sin carpeta de videos, quedan los pósters
      const base = videosBase();
      const s = document.createElement('script');
      s.src = base + 'videos.js';
      s.onload = () => applyVideos(base);
      s.onerror = () => { /* sin carpeta de videos: se mantienen los pósters */ };
      document.head.append(s);
    },
    base: videosBase,
  };
})();
