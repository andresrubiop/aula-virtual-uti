#!/usr/bin/env python3
"""Desbordes en los PDF de las presentaciones (una diapositiva 16:9 por página, hub/tools/pdfs.sh):
texto que invade la franja del pie, que se sale por la izquierda o la derecha, o que queda fuera de la página.

    python3 hub/tools/deck_overflow.py materiales/unidad-*/P*_presentacion*.pdf
    python3 hub/tools/deck_overflow.py --selftest     # comprueba que detecta desbordes fabricados (usa Chrome)

Código de salida 1 si encuentra alguno.
Cómo decide: el pie de cada diapositiva es la fila de texto que contiene "Fundamentos"/"Fundamentals" (o el título del
curso en francés, catalán o japonés) en el 15 %
inferior de la página; toda palabra de otra fila que baje hasta esa franja es un desborde. La portada y el cierre
(sin pie) no se revisan. Límites: no ve texto recortado por su propio bloque (una línea larga de código que se corta
dentro de su recuadro) ni solapamientos entre bloques; para eso, node hub/tools/check.mjs --slides mide en pantalla.
Requiere pdftotext (poppler-utils).
"""
import html
import os
import re
import subprocess
import sys
import tempfile

FOOT = ('Fundamentos', 'Fundamentals', 'Fondements', 'Fonaments')   # + japonés: オペレーティングシステムの基礎
FOOT_JA = 'オペレーティングシステムの基礎'


def words_by_page(pdf):
    xml = subprocess.run(['pdftotext', '-bbox', pdf, '-'], capture_output=True, text=True, check=True).stdout
    for page in re.findall(r'<page (.*?)</page>', xml, re.S):
        W, H = (float(re.search(fr'{k}="([\d.]+)"', page).group(1)) for k in ('width', 'height'))
        words = [(float(a), float(b), float(c), float(d), html.unescape(w)) for a, b, c, d, w in
                 re.findall(r'<word xMin="([-\d.]+)" yMin="([-\d.]+)" xMax="([-\d.]+)" yMax="([-\d.]+)">(.*?)</word>', page)]
        yield W, H, words


def check(pdf):
    out = []
    for n, (W, H, words) in enumerate(words_by_page(pdf), 1):
        anchors = [w for w in words if (w[4] in FOOT or w[4].startswith(FOOT_JA)) and w[1] > 0.85 * H]
        if not anchors:                                   # portada y cierre: sin pie
            continue
        fy0 = min(w[1] for w in anchors)                  # fila del pie: misma línea que el ancla
        fy1 = max(w[3] for w in anchors)
        row = lambda w: w[1] >= fy0 - 2 and w[3] <= fy1 + 2
        low = [w[4] for w in words if not row(w) and w[3] > fy0 - 3]
        right = [w[4] for w in words if w[2] > W - 22]
        left = [w[4] for w in words if w[0] < 8]
        off = [w[4] for w in words if w[1] < 0 or w[3] > H]
        problems = [(low, 'invade el pie'), (right, 'se sale por la derecha'), (left, 'se sale por la izquierda'), (off, 'queda fuera de la página')]
        msg = ' · '.join(f'{what} «{" ".join(ws)[:70]}»' for ws, what in problems if ws)
        if msg:
            out.append(f'{pdf} · diapositiva {n}: {msg}')
    return out


def selftest():
    """Fabrica desbordes en una presentación (abajo a la izquierda, a la derecha) y exige que se detecten, y que la
    misma presentación sin tocar salga limpia."""
    here = os.path.dirname(os.path.abspath(__file__))
    inject = ("(() => { const s = document.querySelectorAll('main > .view:not([hidden]) .deck .slide')[1];"
              " const ul = document.createElement('ul'); for (let i = 0; i < 40; i++) { const li = document.createElement('li');"
              " li.textContent = 'relleno ' + i; ul.append(li); } s.append(ul);"
              " const p = document.createElement('p'); p.style.whiteSpace = 'nowrap';"
              " p.textContent = 'desborde '.repeat(60); s.querySelector('h2').after(p); })()")
    with tempfile.TemporaryDirectory() as d:
        bad, good = os.path.join(d, 'bad.pdf'), os.path.join(d, 'good.pdf')
        for pdf, extra in ((bad, ['--eval', inject]), (good, [])):
            subprocess.run(['node', os.path.join(here, 'check.mjs'), '--routes', '#/u1/presentacion', '--lang', 'es',
                            '--deck', '--pdf', pdf, *extra], capture_output=True, check=False)
        found_bad, found_good = check(bad), check(good)
    ok_bad = any('diapositiva 2:' in f and 'invade el pie' in f and 'derecha' in f for f in found_bad)
    print(('✓' if ok_bad else '✗') + ' detecta los desbordes fabricados en la diapositiva 2' + ('' if ok_bad else f': {found_bad}'))
    print(('✓' if not found_good else '✗') + ' la misma presentación sin tocar sale limpia' + ('' if not found_good else f': {found_good}'))
    return 0 if ok_bad and not found_good else 1


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        sys.exit(selftest())
    found = [line for pdf in sys.argv[1:] for line in check(pdf)]
    print('\n'.join(found) if found else f'Sin desbordes en {len(sys.argv) - 1} PDF.')
    sys.exit(1 if found else 0)
