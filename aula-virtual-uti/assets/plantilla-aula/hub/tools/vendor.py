#!/usr/bin/env python3
"""Descarga UNA vez una biblioteca opcional y la deja lista para incrustar en el aula (sin CDN en ejecución).

    python3 hub/tools/vendor.py three          → hub/vendor/opcional/three.js  (window.THREE; three.js, MIT)

Después: agrega "vendor": ["three"] a hub/src/course.json y compila (python3 hub/build.py).
Necesita internet solo en este paso (registro público de npm). El aula compilada funciona sin conexión.
"""
import io
import json
import pathlib
import sys
import tarfile
import urllib.request

OUT = pathlib.Path(__file__).resolve().parents[1] / 'vendor' / 'opcional'
LIBS = {
    # nombre: (paquete npm, versión fija, archivo dentro del paquete, global que deja)
    'three': ('three', '0.170.0', 'package/build/three.cjs', 'THREE'),
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in LIBS:
        print(__doc__)
        print('Disponibles:', ', '.join(LIBS))
        return 1
    name = sys.argv[1]
    pkg, ver, inner, glob = LIBS[name]
    meta = json.load(urllib.request.urlopen(f'https://registry.npmjs.org/{pkg}/{ver}', timeout=60))
    data = urllib.request.urlopen(meta['dist']['tarball'], timeout=180).read()
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        code = tar.extractfile(inner).read().decode('utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    # el paquete es CommonJS: se envuelve para que deje un global y no toque nada más
    wrapped = (f'/*! {pkg} {ver} · licencia en https://www.npmjs.com/package/{pkg} */\n'
               f'(function () {{ var module = {{ exports: {{}} }}, exports = module.exports;\n{code}\n'
               f'window.{glob} = module.exports; }})();\n')
    (OUT / f'{name}.js').write_text(wrapped, encoding='utf-8')
    print(f'  → hub/vendor/opcional/{name}.js ({len(wrapped) / 1e6:.2f} MB) · global window.{glob}')
    print(f'  Ahora: "vendor": ["{name}"] en hub/src/course.json y python3 hub/build.py')
    return 0


if __name__ == '__main__':
    sys.exit(main())
