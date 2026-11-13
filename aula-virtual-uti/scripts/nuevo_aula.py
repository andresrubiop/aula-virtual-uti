#!/usr/bin/env python3
"""Crea la carpeta de trabajo de un aula virtual UTI a partir de la plantilla de la skill.

    python3 nuevo_aula.py DESTINO --nombre "Fundamentos de Programación" [--clave uti-fp-b26] [--periodo B26]

Deja en DESTINO el proyecto completo (motor del aula, identidad UTI, generador de Canvas, carpetas para los
insumos del docente) y lo compila una vez para comprobar que el equipo tiene lo necesario. No sobrescribe una
carpeta que ya tiene un proyecto.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

PLANTILLA = Path(__file__).resolve().parent.parent / 'assets' / 'plantilla-aula'
INSUMOS = {
    'fuentes/silabo': 'El sílabo vigente del proyecto formativo (PDF del SGA).',
    'fuentes/silabos-anteriores': 'Sílabos de períodos anteriores (sirven de referencia; manda el vigente).',
    'fuentes/presentaciones': 'Presentaciones que ya usas en clase (PPTX, PDF, Google Slides exportado).',
    'fuentes/guias-practicas': 'Guías de prácticas o de laboratorio (PDF, DOCX). Si vienen dentro del sílabo, no hace falta.',
    'fuentes/lecturas': 'Lecturas, capítulos, artículos y apuntes que quieres que el aula use.',
    'fuentes/otros': 'Cualquier otro material: bancos de preguntas, casos, datos, imágenes propias.',
    'fuentes/privado': 'Lo que NO debe salir de tu equipo: listas de estudiantes, notas, datos personales. El agente no lo usa.',
}


def slug(s: str) -> str:
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('destino')
    ap.add_argument('--nombre', required=True, help='nombre del proyecto formativo, como está en el sílabo')
    ap.add_argument('--nombre-en', default='', help='nombre en inglés (si no, lo propone el agente después)')
    ap.add_argument('--clave', default='', help='clave corta y única (por omisión: uti-<siglas>-<periodo>)')
    ap.add_argument('--periodo', default='', help='período académico, p. ej. B26')
    ap.add_argument('--sin-compilar', action='store_true')
    a = ap.parse_args()

    dst = Path(a.destino).expanduser().resolve()
    if (dst / 'hub' / 'build.py').exists():
        sys.exit(f'{dst} ya tiene un aula. Para continuar, abre esa carpeta y lee ESTADO.md.')
    if dst.exists() and (not dst.is_dir() or any(dst.iterdir())):
        sys.exit(f'{dst} no está vacía. Elige una carpeta nueva o vacía para conservar tus archivos.')
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PLANTILLA, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', 'dist', 'shots'))
    ejemplo = PLANTILLA.parent.parent / 'references' / 'silabo-ejemplo.json'
    if ejemplo.exists():
        shutil.copy2(ejemplo, dst / 'canvas' / 'silabo.ejemplo.json')
    for carpeta in ('canvas/exportado', 'canvas/fuentes'):
        (dst / carpeta).mkdir(parents=True, exist_ok=True)
    if (dst / 'gitignore.txt').exists():
        (dst / 'gitignore.txt').rename(dst / '.gitignore')
    for carpeta, que in INSUMOS.items():
        (dst / carpeta).mkdir(parents=True, exist_ok=True)
        (dst / carpeta / 'LEEME.txt').write_text(que + '\n', encoding='utf-8')

    siglas = ''.join(w[0] for w in slug(a.nombre).split('-') if len(w) > 2)[:6] or 'aula'
    clave = slug(a.clave) or '-'.join(x for x in ('uti', siglas, slug(a.periodo)) if x)
    cj = dst / 'hub' / 'src' / 'course.json'
    course = json.loads(cj.read_text(encoding='utf-8'))
    course.update(key=clave, archivo=f'{siglas.upper()}-aula', term=a.periodo or course['term'])
    course['title'] = {'es': a.nombre, 'en': a.nombre_en or a.nombre}
    cj.write_text(json.dumps(course, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for f in ('ESTADO.md', 'PLANIFICACION.md', 'README.md', 'AGENTS.md'):
        p = dst / f
        if p.exists():
            p.write_text(p.read_text(encoding='utf-8').replace('{{NOMBRE}}', a.nombre).replace('{{CLAVE}}', clave)
                         .replace('{{PERIODO}}', a.periodo or '[COMPLETAR]'), encoding='utf-8')

    print(f'Aula creada en {dst}')
    print(f'  clave: {clave} · archivo para Canvas: {course["archivo"]}.html')
    print('  Carpetas para tus documentos:')
    for carpeta, que in INSUMOS.items():
        print(f'    {carpeta:28s} {que}')
    if not a.sin_compilar:
        r = subprocess.run([sys.executable, str(dst / 'hub' / 'build.py')], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode:
            print('  La primera compilación falló: revisa el mensaje anterior.')
            return 1
        print(f'  Ábrela con doble clic: {dst / "hub" / "dist" / "index.html"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
