#!/usr/bin/env python3
"""Versiones del aula que funcionan sin la estructura de carpetas del proyecto (autonomo/).

hub/dist/index.html depende de dos carpetas hermanas: ../../videos/ (videos.js, MP4, pósters) y ../../materiales/
(los PDF). Copiado solo, o subido a Canvas, el aula funciona (animaciones, presentaciones, cuestionarios, dos idiomas) pero
pierde los videos y los botones de PDF. Este script genera, a partir de hub/dist (corre antes python3 hub/build.py):

  autonomo/<CLAVE>-aula.html        UN SOLO ARCHIVO, sin dependencias: los botones «Descargar en PDF» abren la
  autonomo/<CLAVE>-aula-profesor.html impresión de esa página («Guardar como PDF»; la presentación sale en 16:9);
                                    los videos quedan como pósters (en Canvas se suben aparte). Es el que va a Canvas.
  autonomo/paquete/                 carpeta portátil: index.html + videos/ + materiales/ con rutas propias; se copia
                                    o comprime entera y funciona completa en cualquier equipo, sin conexión.

Uso:  python3 hub/tools/autonomo.py [--sin-paquete]
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / 'hub' / 'dist'
OUT = ROOT / 'autonomo'
CFG_RE = re.compile(r'window\.HUB_CONFIG = (\{.*?\});')


def with_config(html: str, **over) -> str:
    m = CFG_RE.search(html)
    if not m:
        sys.exit('No encuentro window.HUB_CONFIG en hub/dist: ¿corriste python3 hub/build.py?')
    cfg = json.loads(m.group(1))
    cfg.update(over)
    return html[:m.start()] + 'window.HUB_CONFIG = ' + json.dumps(cfg, ensure_ascii=False) + ';' + html[m.end():]


def main() -> int:
    OUT.mkdir(exist_ok=True)
    clave = json.loads((ROOT / 'hub' / 'src' / 'course.json').read_text()).get('archivo', 'aula')
    for src, dst in (('index.html', f'{clave}.html'), ('profesor.html', f'{clave}-profesor.html')):
        html = with_config((DIST / src).read_text(), videos_base='', materiales_base='imprimir')
        (OUT / dst).write_text(html)
        print(f'  → autonomo/{dst} ({(OUT / dst).stat().st_size / 1e6:.1f} MB, un solo archivo)')
    if '--sin-paquete' in sys.argv:
        return 0
    pk = OUT / 'paquete'
    if pk.exists():
        shutil.rmtree(pk)
    pk.mkdir()
    (pk / 'index.html').write_text(with_config((DIST / 'index.html').read_text(), videos_base='videos/', materiales_base='materiales/'))
    if (ROOT / 'materiales').exists():
        shutil.copytree(ROOT / 'materiales', pk / 'materiales')
    (pk / 'videos').mkdir()
    if (ROOT / 'videos' / 'videos.js').exists():
        shutil.copy2(ROOT / 'videos' / 'videos.js', pk / 'videos' / 'videos.js')
    for d in sorted((ROOT / 'videos').glob('unidad-*')):
        shutil.copytree(d, pk / 'videos' / d.name)
    size = sum(f.stat().st_size for f in pk.rglob('*') if f.is_file()) / 1e6
    print(f'  → autonomo/paquete/ (index.html + materiales/ + videos/, {size:.0f} MB; edición de estudiantes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
