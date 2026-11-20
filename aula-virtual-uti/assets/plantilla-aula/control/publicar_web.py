#!/usr/bin/env python3
"""Publica una edición del aula (la del estudiante o, si el docente lo pide, la del profesor) en GitHub Pages, para Canvas.

    python3 control/publicar_web.py                          # estado: dirección publicada y si está al día
    python3 control/publicar_web.py publicar --repo NOMBRE [--edicion profesor]   # repositorio PÚBLICO aparte, Pages comprobado

Por qué: Canvas sirve los HTML subidos al curso con «Content-Security-Policy: sandbox; script-src 'none'», así que el
aula (que necesita JavaScript para el menú, las animaciones, los cuestionarios y el avance) se ve estática y no
responde. Publicada en una dirección https propia, Canvas la muestra en un marco y funciona completa.

Qué se publica: autonomo/<archivo>.html (edición del estudiante, por omisión) o autonomo/<archivo>-profesor.html
(--edicion profesor: incluye los bloques docentes —solucionarios, notas— y quedan públicos) como index.html, más
README y .nojekyll. Nunca fuentes, ESTADO, respaldos ni el repositorio privado del aula, que sigue privado. Antes de
subir se detiene si encuentra teléfonos o algo con forma de token (y bloques docentes en la edición del estudiante). Publicar es
público en internet: hazlo solo con la conformidad expresa del docente. La dirección queda en hub/src/course.json →
"publicacion" y canvas/generar_canvas.py la usa para el aula en Inicio y en la página del aula.
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
COURSE = ROOT / 'hub' / 'src' / 'course.json'
TOKEN = re.compile(rb'\b\d{2,6}~[A-Za-z0-9]{40,}\b|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}')
TELEFONO = re.compile(rb'(\+593[\s-]?\d[\d\s-]{6,}\d|\b09\d{8}\b)')


def course():
    return json.loads(COURSE.read_text(encoding='utf-8'))


def edicion(cual='estudiante'):
    return ROOT / 'autonomo' / (f'{course()["archivo"]}-profesor.html' if cual == 'profesor' else f'{course()["archivo"]}.html')


def sh(*cmd, cwd=None, check=True):
    r = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and r.returncode:
        raise SystemExit(f'{" ".join(cmd[:3])} falló: {(r.stderr or r.stdout).strip()[:400]}')
    return r


def revisar(datos, cual='estudiante'):
    problemas = []
    if cual != 'profesor' and (b'<!--docente' in datos or b'class="docente' in datos):
        problemas.append('contiene bloques de la edición docente')
    if TOKEN.search(datos):
        problemas.append('contiene algo con forma de token o clave')
    if TELEFONO.search(datos):
        problemas.append('contiene un número de teléfono (no se publica salvo pedido expreso del docente)')
    tf = Path.home() / '.config' / 'aula-uti' / 'canvas-token'
    if tf.exists() and tf.read_text(encoding='utf-8').strip().encode() in datos:
        problemas.append('contiene el token de Canvas')
    return problemas


def estado():
    pub = course().get('publicacion') or {}
    res = {'url': pub.get('url'), 'repo': pub.get('repo'), 'edicion': pub.get('edicion'), 'publicada_sha256': pub.get('sha256'), 'al_dia': None, 'responde': None}
    f = edicion(pub.get('edicion', 'estudiante'))
    if f.exists() and pub.get('sha256'):
        res['al_dia'] = hashlib.sha256(f.read_bytes()).hexdigest() == pub['sha256']
    if pub.get('url'):
        try:
            with urllib.request.urlopen(pub['url'], timeout=20) as r:
                res['responde'] = r.status == 200
        except Exception:                                   # noqa: BLE001
            res['responde'] = False
    return res


def publicar(repo, cual='estudiante'):
    f = edicion(cual)
    if not f.exists():
        sys.exit(f'Falta {f.relative_to(ROOT)}: python3 hub/build.py && python3 hub/tools/autonomo.py --sin-paquete')
    datos = f.read_bytes()
    prob = revisar(datos, cual)
    if cual == 'profesor':
        print('AVISO: se publica la edición del PROFESOR; todo lo docente que contenga (solucionarios, notas) quedará público en internet.')
    if prob:
        sys.exit(f'No se publica la edición del {cual}:\n  - ' + '\n  - '.join(prob))
    if not shutil.which('gh') or sh('gh', 'auth', 'status', check=False).returncode:
        sys.exit('Hace falta GitHub CLI con la sesión del docente iniciada (gh auth login).')
    usuario = sh('gh', 'api', 'user', '-q', '.login').stdout.strip()
    completo = repo if '/' in repo else f'{usuario}/{repo}'
    vis = sh('gh', 'repo', 'view', completo, '--json', 'visibility', '-q', '.visibility', check=False)
    if vis.returncode:
        sh('gh', 'repo', 'create', completo, '--public', '--description',
           f'Aula interactiva · {course()["title"]["es"]} · UTI')
    elif vis.stdout.strip().upper() != 'PUBLIC':
        sys.exit(f'{completo} no es público: GitHub Pages gratuito necesita un repositorio público solo con la edición del aula.')
    nombre_git = sh('git', '-C', str(ROOT), 'config', 'user.name', check=False).stdout.strip() or usuario
    correo_git = sh('git', '-C', str(ROOT), 'config', 'user.email', check=False).stdout.strip() or f'{usuario}@users.noreply.github.com'
    tmp = Path(tempfile.mkdtemp(prefix='aula-web-'))
    try:
        sh('git', 'init', '-q', '-b', 'main', str(tmp))
        url_git = f'https://github.com/{completo}.git'
        sh('git', '-C', str(tmp), 'remote', 'add', 'origin', url_git)
        if sh('git', '-C', str(tmp), 'fetch', '-q', 'origin', 'main', check=False).returncode == 0:
            sh('git', '-C', str(tmp), 'checkout', '-q', '-B', 'main', 'origin/main')
        (tmp / 'index.html').write_bytes(datos)
        (tmp / '.nojekyll').write_text('', encoding='utf-8')
        c = course()
        (tmp / 'README.md').write_text(
            f'# {c["title"]["es"]}\n\nAula interactiva del curso (edición del {"profesor" if cual == "profesor" else "estudiante"}), Universidad Tecnológica Indoamérica.\n'
            'Se publica aquí porque Canvas no ejecuta el JavaScript de los HTML subidos; el curso la muestra desde esta dirección.\n'
            'Generada con la skill aula-virtual-uti. Logos e identidad gráfica: Universidad Tecnológica Indoamérica.\n', encoding='utf-8', newline='\n')
        sh('git', '-C', str(tmp), 'add', '-A')
        if sh('git', '-C', str(tmp), 'diff', '--cached', '--quiet', check=False).returncode:
            sh('git', '-C', str(tmp), '-c', f'user.name={nombre_git}', '-c', f'user.email={correo_git}', 'commit', '-q', '-m', f'Aula interactiva (edición del {cual})')
        sh('git', '-C', str(tmp), 'push', '-q', '-u', 'origin', 'main')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    r = sh('gh', 'api', '-X', 'POST', f'repos/{completo}/pages', '-f', 'source[branch]=main', '-f', 'source[path]=/', check=False)
    if r.returncode and 'already' not in (r.stderr + r.stdout).lower() and '409' not in r.stderr:
        sys.exit('No se pudo activar GitHub Pages: ' + (r.stderr or r.stdout).strip()[:300])
    url = sh('gh', 'api', f'repos/{completo}/pages', '-q', '.html_url').stdout.strip() or f'https://{usuario}.github.io/{completo.split("/")[1]}/'
    huella = hashlib.sha256(datos).hexdigest()
    servido = None
    for _ in range(40):                                     # Pages tarda en desplegar: hasta unos 4 minutos
        try:
            with urllib.request.urlopen(url + ('' if url.endswith('/') else '/'), timeout=20) as resp:
                servido = hashlib.sha256(resp.read()).hexdigest()
            if servido == huella:
                break
        except Exception:                                   # noqa: BLE001
            pass
        time.sleep(6)
    c = course()
    c['publicacion'] = {'url': url, 'repo': completo, 'edicion': cual, 'sha256': huella, 'servida': servido == huella}
    COURSE.write_text(json.dumps(c, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return c['publicacion']


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('orden', nargs='?', default='estado', choices=['estado', 'publicar'])
    ap.add_argument('--repo', help='nombre del repositorio público (aparte del repositorio privado del aula)')
    ap.add_argument('--edicion', choices=['estudiante', 'profesor'], default='estudiante')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if a.orden == 'publicar':
        if not a.repo:
            sys.exit('Indica --repo NOMBRE (repositorio público aparte del repositorio privado del aula).')
        r = publicar(a.repo, a.edicion)
        print(json.dumps(r, ensure_ascii=False) if a.json else
              f'Publicada en {r["url"]} ' + ('(comprobada: sirve la versión actual).' if r['servida'] else '(GitHub Pages aún desplegando; vuelve a comprobar con «estado»).'))
        return 0 if r['servida'] else 1
    r = estado()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        if not r['url']:
            print('El aula no está publicada en la web. En Canvas no funcionará dentro del curso (Canvas bloquea su JavaScript): '
                  'python3 control/publicar_web.py publicar --repo <nombre>, con la conformidad del docente.')
        else:
            print(f'Publicada: {r["url"]} · responde: {r["responde"]} · al día: {r["al_dia"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
