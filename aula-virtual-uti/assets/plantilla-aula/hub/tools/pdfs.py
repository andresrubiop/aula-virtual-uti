#!/usr/bin/env python3
"""Regenera los PDF de cada unidad en materiales/unidad-N/, en español y en inglés.

    python3 hub/tools/pdfs.py            → todas las unidades
    python3 hub/tools/pdfs.py 3 5        → solo las unidades 3 y 5
    PDF_LANGS=en python3 hub/tools/pdfs.py 2      → solo ese idioma
    PDF_DOCS=manual python3 hub/tools/pdfs.py     → solo esos documentos (manual, presentacion, practica)

Archivos: M1_manual.pdf (español) y M1_manual.en.pdf (inglés); P1_presentacion(.en).pdf, una diapositiva 16:9 por
página; <ID>_practica(.en).pdf, con el identificador de la práctica de la unidad (course.json → units[].lab).
Requiere hub/dist/index.html actualizado (python3 hub/build.py), Node ≥ 22 y Chrome/Chromium.
Son además las fuentes de los videos (videos/guiones/): si el aula cambia, se regeneran.
"""
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
COURSE = json.loads((ROOT / 'hub' / 'src' / 'course.json').read_text(encoding='utf-8'))
CHECK = ['node', str(ROOT / 'hub' / 'tools' / 'check.mjs')]


def main() -> int:
    nums = [int(a) for a in sys.argv[1:]] or [u['n'] for u in COURSE['units']]
    langs = os.environ.get('PDF_LANGS', 'es en').split()
    docs = os.environ.get('PDF_DOCS', 'manual presentacion practica').split()
    fallos = 0
    for u in COURSE['units']:
        if u['n'] not in nums:
            continue
        n, uid = u['n'], u['id']
        carpeta = ROOT / 'hub' / 'src' / 'content' / uid
        sub_prac = next((s for s in ('practica', 'laboratorio', 'actividad') if list(carpeta.glob(f'*-{s}.html'))), None)
        for lang in langs:
            sfx = '' if lang == 'es' else f'.{lang}'
            titulo = u['title'].get(lang) or u['title']['es']
            out = f'materiales/unidad-{n}'
            trabajos = []
            if 'manual' in docs and list(carpeta.glob('*-manual.html')):
                trabajos.append((f'#/{uid}/manual', f'{out}/M{n}_manual{sfx}.pdf', ['--titulo', f'M{n} · {titulo}']))
            if 'presentacion' in docs and list(carpeta.glob('*-presentacion.html')):
                trabajos.append((f'#/{uid}/presentacion', f'{out}/P{n}_presentacion{sfx}.pdf', ['--deck']))
            if 'practica' in docs and sub_prac:
                lab = u.get('lab') or f'PR{n}'
                trabajos.append((f'#/{uid}/{sub_prac}', f'{out}/{lab}_practica{sfx}.pdf', ['--titulo', f'{lab} · {titulo}']))
            for ruta, pdf, extra in trabajos:
                r = subprocess.run([*CHECK, '--routes', ruta, '--lang', lang, '--pdf', pdf, *extra], cwd=ROOT)
                fallos += r.returncode != 0
    return 1 if fallos else 0


if __name__ == '__main__':
    sys.exit(main())
