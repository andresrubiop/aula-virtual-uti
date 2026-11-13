/* Quiz · cuestionarios formativos con retroalimentación inmediata (sin calificación).
 * Bilingüe: q, opts[i], why[i] y tag pueden ser {"es": "…", "en": "…"}.
 *
 *   <div class="quiz" data-quiz="Q1" data-check-id="s1-q1">
 *     <script type="application/json">
 *       {"questions":[{"q":"Enunciado (HTML)","opts":["A","B","C","D"],"ans":1,
 *                      "why":["por qué A","por qué B","…"],"tag":"Fuga de datos","ref":"#/s1/manual/m1-7"}]}
 *     </script>
 *   </div>
 * Las respuestas se guardan solo en este navegador. Al completar se marca data-check-id.
 */
(function () {
  'use strict';
  const Hub = window.Hub;
  const { h, $$ } = Hub.util;
  const I = Hub.i18n;
  const { L } = I;
  const KEYS = 'ABCDEFG';

  function mount(el) {
    const id = el.dataset.quiz;
    let data;
    try { data = JSON.parse(el.querySelector('script[type="application/json"]').textContent); }
    catch (e) { el.innerHTML = `<div class="pending">${I.html(L('No se pudo leer el cuestionario.', 'The quiz could not be read.'))}</div>`; console.error('[Quiz]', id, e); return; }
    const qs = data.questions || [];
    let answers = Hub.store.get('quiz:' + id, {});

    const score = h('div', { class: 'quiz__score' });
    const barFill = h('span');
    const status = h('div', { class: 'muted' });
    const reset = h('button', { type: 'button', class: 'btn btn--sm', html: I.html(L('Reiniciar cuestionario', 'Restart quiz')) });
    const summary = h('div', { class: 'quiz__summary' }, score, h('div', { class: 'quiz__bar' }, barFill), status, reset);
    const list = h('div', { class: 'quiz' });

    function update() {
      const done = Object.keys(answers).length;
      const ok = Object.entries(answers).filter(([k, v]) => qs[k] && qs[k].ans === v).length;
      score.textContent = `${ok} / ${qs.length}`;
      barFill.style.width = (done / (qs.length || 1)) * 100 + '%';
      if (done < qs.length) status.innerHTML = I.html(L(`Respondidas ${done} de ${qs.length}. Cada respuesta muestra su explicación.`,
        `${done} of ${qs.length} answered. Every answer shows its explanation.`,
        { fr: `${done} sur ${qs.length} répondues. Chaque réponse affiche son explication.`,
          ca: `${done} de ${qs.length} respostes. Cada resposta mostra la seva explicació.`,
          ja: `${qs.length} 問中 ${done} 問に回答。各回答に解説が表示されます。` }));
      else status.innerHTML = ok >= qs.length * 0.8
        ? I.html(L('<strong>¡Muy bien!</strong> Dominas los conceptos de la unidad.', '<strong>Well done!</strong> You master the concepts of the unit.'))
        : I.html(L('<strong>Revisa</strong> las explicaciones y las secciones del manual enlazadas; puedes reiniciar e intentarlo otra vez.',
          '<strong>Review</strong> the explanations and the linked manual sections; you can restart and try again.'));
      if (done === qs.length && el.dataset.checkId && Hub.progress) Hub.progress.set(el.dataset.checkId, true);
    }

    function render() {
      list.replaceChildren(...qs.map((q, qi) => {
        const chosen = answers[qi];
        const answered = chosen !== undefined;
        const opts = q.opts.map((o, oi) => {
          const cls = ['q__opt'];
          if (answered && oi === q.ans) cls.push('is-correct');
          if (answered && oi === chosen && chosen !== q.ans) cls.push('is-wrong');
          const b = h('button', { type: 'button', class: cls.join(' '), disabled: answered },
            h('span', { class: 'q__key' }, KEYS[oi]), h('span', { html: I.html(o) }));
          b.addEventListener('click', () => { answers[qi] = oi; Hub.store.set('quiz:' + id, answers); render(); update(); });
          return h('li', {}, b);
        });
        let why = null;
        if (answered) {
          const right = chosen === q.ans;
          const parts = [`<strong>${I.html(right ? L('✓ Correcto', '✓ Correct') : L('✗ No es la mejor respuesta', '✗ Not the best answer'))}</strong>`];
          if (q.why && q.why[chosen]) parts.push(I.html(q.why[chosen]));
          if (!right && q.why && q.why[q.ans]) parts.push(`<br><em>${I.html(L('Respuesta', 'Answer'))} ${KEYS[q.ans]}:</em> ${I.html(q.why[q.ans])}`);
          if (q.ref) parts.push(` <a href="${q.ref}">${I.html(L('Repasar en el manual →', 'Review in the manual →'))}</a>`);
          why = h('div', { class: 'q__why' + (right ? '' : ' is-wrong'), html: parts.join(' ') });
        }
        return h('div', { class: 'q' },
          h('div', { class: 'q__head' }, h('span', { class: 'q__n' }, String(qi + 1).padStart(2, '0')),
            h('div', { class: 'q__stem', html: I.html(q.q) }), q.tag ? h('span', { class: 'chip q__tag', html: I.html(q.tag) }) : null),
          h('ol', { class: 'q__opts' }, opts), why);
      }));
      if (Hub.math) Hub.math.render(list, true);
    }

    reset.addEventListener('click', () => { answers = {}; Hub.store.set('quiz:' + id, answers); render(); update(); });
    el.replaceChildren(summary, list);
    render();
    update();
  }

  Hub.quiz = { mountAll(root = document) { $$('.quiz[data-quiz]:not([data-mounted])', root).forEach(el => { el.setAttribute('data-mounted', ''); mount(el); }); } };
})();
