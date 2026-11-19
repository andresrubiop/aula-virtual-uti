#!/usr/bin/env python3
"""Lleva las herramientas de un aula existente a la versión instalada de la skill, sin tocar su contenido.

    python3 <skill>/scripts/actualizar_aula.py <aula>                   # vista previa: qué cambiaría
    python3 <skill>/scripts/actualizar_aula.py <aula> --aplicar         # copia de lo reemplazado y actualización
    python3 <skill>/scripts/actualizar_aula.py <aula> --aplicar --incluir-motor   # también estilos y componentes

Se actualizan solo HERRAMIENTAS que el docente no edita (control/*.py, hub/build.py, hub/tools/, canvas/*.py,
videos/generar_videos.py, sus LEEME/README) y se agregan las que falten. El MOTOR del aula (hub/src/css,
hub/src/js/core y components, identidad-uti/tokens.css) puede tener ajustes propios del aula: se informa lo que
difiere y solo se reemplaza con --incluir-motor, después de revisarlo. Nunca se tocan el contenido (hub/src/content,
course.json, animaciones, prácticas, materiales, videos), fuentes/, ESTADO.md ni los respaldos.
Antes de reemplazar, guarda cada archivo anterior en respaldos/actualizacion-<fecha>/ (con la misma ruta) y
escribe control/VERSION_SKILL. Después: python3 hub/build.py, control/estado.py verificar y control/panel.py.
"""
import argparse
import filecmp
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SKILL = Path(__file__).resolve().parents[1]
PLANTILLA = SKILL / 'assets' / 'plantilla-aula'
HERRAMIENTAS = ['control/*.py', 'control/LEEME.md', 'hub/build.py', 'hub/tools/*.py', 'hub/tools/*.mjs', 'hub/tools/lib/*.mjs',
                'canvas/*.py', 'canvas/LEEME.md', 'videos/generar_videos.py', 'videos/README.md']
MOTOR = ['hub/src/css/*.css', 'hub/src/js/core/*.js', 'hub/src/js/components/*.js', 'hub/src/js/app.js', 'identidad-uti/tokens.css']


def version():
    m = re.search(r'^\s*version:\s*"?([\w.\-]+)"?\s*$', (SKILL / 'SKILL.md').read_text(encoding='utf-8').split('\n---', 1)[0], re.M)
    return m[1] if m else 'sin versión'


def plan(aula, patrones):
    out = []
    for patron in patrones:
        for src in sorted(PLANTILLA.glob(patron)):
            if not src.is_file() or '__pycache__' in src.parts:
                continue
            rel = src.relative_to(PLANTILLA).as_posix()
            dst = aula / rel
            if dst.is_symlink():
                out.append((rel, 'enlace: no se toca'))
            elif not dst.exists():
                out.append((rel, 'nuevo'))
            elif not filecmp.cmp(src, dst, shallow=False):
                out.append((rel, 'distinto'))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('aula', type=Path)
    ap.add_argument('--aplicar', action='store_true')
    ap.add_argument('--incluir-motor', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    aula = a.aula.expanduser().resolve()
    if not (aula / 'ESTADO.md').is_file() or not (aula / 'hub' / 'src').is_dir():
        sys.exit(f'{aula} no parece un aula (faltan ESTADO.md o hub/src/).')
    if aula == PLANTILLA.resolve() or SKILL.resolve() in aula.parents:
        sys.exit('Indica la carpeta del aula, no la de la skill.')
    anterior = (aula / 'control' / 'VERSION_SKILL').read_text(encoding='utf-8').strip() if (aula / 'control' / 'VERSION_SKILL').is_file() else 'anterior a 0.12.0'
    herramientas = plan(aula, HERRAMIENTAS)
    motor = plan(aula, MOTOR)
    aplicar = [(r, e) for r, e in herramientas + (motor if a.incluir_motor else []) if e in ('nuevo', 'distinto')]
    resultado = {'aula': str(aula), 'version_aula': anterior, 'version_skill': version(),
                 'herramientas': [{'archivo': r, 'cambio': e} for r, e in herramientas],
                 'motor': [{'archivo': r, 'cambio': e} for r, e in motor], 'incluir_motor': a.incluir_motor, 'aplicado': False}
    if a.aplicar and aplicar:
        marca = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        copia = aula / 'respaldos' / f'actualizacion-{marca}'
        for rel, estado in aplicar:
            dst = aula / rel
            if estado == 'distinto':
                (copia / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, copia / rel)
        for rel, _ in aplicar:
            dst = aula / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name('.' + dst.name + '.nuevo')
            shutil.copy2(PLANTILLA / rel, tmp)
            tmp.replace(dst)
        (aula / 'control').mkdir(exist_ok=True)
        (aula / 'control' / 'VERSION_SKILL').write_text(version() + '\n', encoding='utf-8', newline='\n')
        resultado.update(aplicado=True, copia_anterior=copia.relative_to(aula).as_posix() if copia.exists() else None)
    elif a.aplicar:
        (aula / 'control' / 'VERSION_SKILL').write_text(version() + '\n', encoding='utf-8', newline='\n')
        resultado['aplicado'] = True
    if a.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=1))
        return 0
    print(f'Aula: {aula}\nVersión del aula: {anterior} → skill instalada: {version()}\n')
    for titulo, filas in (('Herramientas', herramientas), ('Motor del aula (estilos y componentes)', motor)):
        print(f'{titulo}: {len(filas)} archivo(s) por actualizar' if filas else f'{titulo}: al día')
        for rel, e in filas:
            print(f'   {e:9s} {rel}')
    if motor and not a.incluir_motor:
        print('\n   El motor puede tener ajustes propios del aula: revísalo y añade --incluir-motor para actualizarlo.')
    if not a.aplicar:
        print('\nVista previa: no se cambió nada. Para aplicar: añade --aplicar.')
    else:
        print('\nActualizado.' + (f' Copia de los archivos reemplazados: {resultado["copia_anterior"]}' if resultado.get('copia_anterior') else '')
              + '\nAhora: python3 hub/build.py · python3 control/estado.py verificar · python3 control/panel.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
