#!/usr/bin/env python3
"""El aula vive en un repositorio privado de GitHub del docente (obligatorio): historial, copia fuera del equipo y relevo.

    python3 control/repositorio.py                       # estado: Git, remoto en GitHub, privacidad, cambios sin guardar o sin subir
    python3 control/repositorio.py iniciar --crear NOMBRE   # crea el repositorio PRIVADO en la cuenta del docente (gh) y sube el aula
    python3 control/repositorio.py iniciar --remoto URL     # o usa un repositorio vacío que el docente ya creó en github.com
    python3 control/repositorio.py guardar -m "Unidad 2 lista para revisión"   # commit + push al cerrar cada hito o sesión
    python3 control/repositorio.py --json …

Antes de cada commit revisa lo que se va a subir y se detiene si encuentra: fuentes/privado/, canvas/api/privado/,
respaldos/, archivos .env, llaves, el token de Canvas guardado en el equipo o algo con forma de token, o archivos
de más de 50 MB (GitHub rechaza los de 100 MB). Lo generado (hub/dist, autonomo, canvas/salida, videos MP4) ya está
en .gitignore y se regenera. El docente crea su cuenta de GitHub e inicia sesión él mismo (`gh auth login` o la web):
el asistente nunca pide ni escribe contraseñas.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
PROHIBIDO = re.compile(r'(^|/)(fuentes/privado|canvas/api/privado|respaldos)/|(^|/)\.env(\.|$)|(^|/)(id_rsa|id_ed25519)[^/]*$|\.(pem|key|p12)$|canvas-token', re.I)
TOKEN = re.compile(rb'\b\d{2,6}~[A-Za-z0-9]{40,}\b|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}')
MAX_MB = 50


def git(*args, check=False, root=ROOT):
    r = subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if check and r.returncode:
        raise SystemExit(f'git {" ".join(args[:2])} falló: {(r.stderr or r.stdout).strip()[:400]}')
    return r


def estado(root=ROOT):
    root = Path(root)
    res = {'git': shutil.which('git') is not None, 'repo': False, 'remoto': None, 'github': False, 'visibilidad': None,
           'cambios': 0, 'sin_subir': None, 'ultimo': None, 'errores': [], 'avisos': []}
    if not res['git']:
        res['errores'].append('Git no está instalado: instálalo (https://git-scm.com/downloads; en Linux «sudo apt install git», '
                              'en macOS «xcode-select --install», en Windows «winget install Git.Git»).')
        return res
    res['repo'] = git('rev-parse', '--is-inside-work-tree', root=root).stdout.strip() == 'true' and \
        Path(git('rev-parse', '--show-toplevel', root=root).stdout.strip()).resolve() == root.resolve()
    if not res['repo']:
        res['errores'].append('El aula no es un repositorio Git: python3 control/repositorio.py iniciar --crear <nombre>.')
        return res
    res['remoto'] = git('config', '--get', 'remote.origin.url', root=root).stdout.strip() or None
    res['github'] = bool(res['remoto'] and 'github.com' in res['remoto'])
    if not res['github']:
        res['errores'].append('El aula no está conectada a GitHub (remoto «origin»). Pide al docente su cuenta de GitHub, que inicie sesión '
                              '(gh auth login) y ejecuta: python3 control/repositorio.py iniciar --crear <nombre>.')
    res['cambios'] = len([l for l in git('status', '--porcelain', root=root).stdout.splitlines() if l.strip()])
    ultimo = git('log', '-1', '--format=%cI', root=root)
    res['ultimo'] = ultimo.stdout.strip() or None
    if res['github']:
        rama = git('rev-parse', '--abbrev-ref', 'HEAD', root=root).stdout.strip()
        r = git('rev-list', '--count', f'origin/{rama}..HEAD', root=root)
        res['sin_subir'] = int(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip().isdigit() else None
        if shutil.which('gh') and not os.environ.get('AULA_SIN_RED'):
            v = subprocess.run(['gh', 'repo', 'view', res['remoto'], '--json', 'visibility', '-q', '.visibility'],
                               capture_output=True, text=True, encoding='utf-8')
            res['visibilidad'] = (v.stdout.strip().lower() or None) if v.returncode == 0 else None
        if res['visibilidad'] == 'public':
            res['avisos'].append('El repositorio es PÚBLICO: el aula contiene los documentos del docente. Hazlo privado en GitHub '
                                 '(Settings → General → Danger Zone → Change visibility) salvo decisión expresa del docente.')
    if res['cambios']:
        res['avisos'].append(f'{res["cambios"]} archivo(s) con cambios sin guardar: python3 control/repositorio.py guardar -m "…".')
    if res['sin_subir']:
        res['avisos'].append(f'{res["sin_subir"]} commit(s) sin subir a GitHub: python3 control/repositorio.py guardar.')
    if res['github'] and res['sin_subir'] is None and res['ultimo']:
        res['avisos'].append('No se pudo comparar con GitHub (¿la rama aún no se subió?): python3 control/repositorio.py guardar.')
    return res


def revisar_preparados():
    """Lo que está preparado para el commit no debe contener privados, credenciales ni archivos enormes."""
    problemas = []
    token_local = None
    tf = Path.home() / '.config' / 'aula-uti' / 'canvas-token'
    if tf.exists():
        token_local = tf.read_text(encoding='utf-8').strip().encode() or None
    for rel in git('diff', '--cached', '--name-only', '-z').stdout.split('\0'):
        if not rel:
            continue
        if PROHIBIDO.search(rel):
            problemas.append(f'{rel}: privado o credencial; no se sube')
            continue
        p = ROOT / rel
        if not p.is_file():
            continue
        tam = p.stat().st_size
        if tam > MAX_MB * 1024 * 1024:
            problemas.append(f'{rel}: {tam / 1e6:.0f} MB (más de {MAX_MB} MB); agrégalo a .gitignore o súbelo aparte')
            continue
        datos = p.read_bytes() if tam < 20 * 1024 * 1024 else b''
        if (token_local and token_local in datos) or TOKEN.search(datos):
            problemas.append(f'{rel}: contiene algo con forma de token o clave; quítalo antes de guardar')
    return problemas


def identidad():
    nombre, correo = git('config', 'user.name').stdout.strip(), git('config', 'user.email').stdout.strip()
    if not nombre or not correo:
        sys.exit('Falta la identidad de Git del docente. Que la indique él (aparece en el historial de su repositorio):\n'
                 '  git config --global user.name "Nombre Apellido"\n  git config --global user.email "correo@…"')


def iniciar(crear=None, remoto=None):
    if not shutil.which('git'):
        sys.exit(estado()['errores'][0])
    identidad()
    if not (ROOT / '.git').exists():
        git('init', '-b', 'main', check=True)
    if not git('rev-parse', '--verify', 'HEAD').stdout.strip():
        git('add', '-A', check=True)
        prob = revisar_preparados()
        if prob:
            git('reset', '-q')
            sys.exit('No se creó el primer commit:\n  - ' + '\n  - '.join(prob))
        git('commit', '-q', '-m', 'Aula creada con la skill aula-virtual-uti', check=True)
    actual = git('config', '--get', 'remote.origin.url').stdout.strip()
    if crear:
        if actual:
            sys.exit(f'El aula ya tiene remoto: {actual}')
        if not shutil.which('gh'):
            sys.exit('Para crear el repositorio desde aquí hace falta GitHub CLI (gh): https://cli.github.com · o crea tú un repositorio '
                     'PRIVADO y vacío en github.com y usa --remoto <URL>.')
        if subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode:
            sys.exit('El docente debe iniciar sesión en GitHub él mismo: gh auth login (elige GitHub.com y el navegador).')
        r = subprocess.run(['gh', 'repo', 'create', crear, '--private', '--source', str(ROOT), '--remote', 'origin', '--push',
                            '--description', 'Aula virtual UTI (skill aula-virtual-uti)'], capture_output=True, text=True, encoding='utf-8')
        if r.returncode:
            sys.exit('gh repo create falló: ' + (r.stderr or r.stdout).strip()[:400])
    elif remoto:
        if actual and actual != remoto:
            sys.exit(f'El aula ya tiene otro remoto: {actual}')
        if not actual:
            git('remote', 'add', 'origin', remoto, check=True)
        r = git('push', '-u', 'origin', 'HEAD')
        if r.returncode:
            sys.exit('No se pudo subir (¿repositorio vacío y sesión iniciada?): ' + (r.stderr or r.stdout).strip()[:400])
    return estado()


def guardar(mensaje, subir=True):
    est = estado()
    if not est['repo']:
        sys.exit(est['errores'][0])
    identidad()
    git('add', '-A', check=True)
    prob = revisar_preparados()
    if prob:
        git('reset', '-q')
        sys.exit('No se guardó nada; revisa:\n  - ' + '\n  - '.join(prob) + '\nAgrega lo privado a .gitignore o quítalo del aula.')
    hecho = False
    if git('diff', '--cached', '--quiet').returncode:
        git('commit', '-q', '-m', mensaje or 'Avance del aula', check=True)
        hecho = True
    subido = False
    if subir and est['github']:
        r = git('push', '-u', 'origin', 'HEAD')
        if r.returncode:
            sys.exit('Commit guardado en el equipo, pero no se pudo subir a GitHub: ' + (r.stderr or r.stdout).strip()[:400])
        subido = True
    return {'commit': hecho, 'subido': subido, 'estado': estado()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('orden', nargs='?', default='estado', choices=['estado', 'iniciar', 'guardar'])
    ap.add_argument('--crear', help='nombre del repositorio privado a crear con gh')
    ap.add_argument('--remoto', help='URL de un repositorio vacío ya creado en GitHub')
    ap.add_argument('-m', '--mensaje', default='')
    ap.add_argument('--sin-subir', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if a.orden == 'iniciar':
        r = iniciar(a.crear, a.remoto)
    elif a.orden == 'guardar':
        r = guardar(a.mensaje, not a.sin_subir)
    else:
        r = estado()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        e = r.get('estado', r)
        print(f'GitHub: {e["remoto"] or "sin conectar"}' + (f' ({e["visibilidad"]})' if e.get('visibilidad') else '')
              + (f' · último commit {e["ultimo"][:16]}' if e.get('ultimo') else ''))
        if 'commit' in r:
            print(('Guardado' if r['commit'] else 'Sin cambios nuevos') + (' y subido a GitHub.' if r['subido'] else '.'))
        for x in e['errores']:
            print('  ✗', x)
        for x in e['avisos']:
            print('  ·', x)
    e = r.get('estado', r)
    return 1 if e['errores'] else 0


if __name__ == '__main__':
    sys.exit(main())
