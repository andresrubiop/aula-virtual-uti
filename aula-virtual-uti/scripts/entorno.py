#!/usr/bin/env python3
"""Comprueba que el equipo del docente tiene lo necesario y explica, en lenguaje llano, qué falta y cómo instalarlo.

    python3 entorno.py            → tabla de lo imprescindible y lo opcional
    python3 entorno.py --json     → lo mismo para que lo lea el agente

Imprescindible: Python ≥ 3.10 (compila el aula y genera el paquete de Canvas).
Para verificar y exportar PDF: Node ≥ 22 y Chrome, Edge o Chromium.
Para videos: ffmpeg (portada y cierre UTI) y, solo en modo automático, la herramienta nlm de NotebookLM.
Para leer los documentos del docente: pdftotext (poppler); LibreOffice si hay .doc/.ppt antiguos.
"""
import json
import platform
import shutil
import subprocess
import sys

SO = platform.system()


def version(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:                                   # noqa: BLE001
        return ''


def instalar(pkg_apt, pkg_brew, pkg_winget, web=''):
    if SO == 'Linux':
        return f'sudo apt install {pkg_apt}' if pkg_apt else web
    if SO == 'Darwin':
        return f'brew install {pkg_brew}' if pkg_brew else web
    return (f'winget install {pkg_winget}' if pkg_winget else web)


def main() -> int:
    chrome = next((c for c in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'msedge', 'microsoft-edge') if shutil.which(c)), None)
    if not chrome and SO == 'Darwin':
        import os
        for p in ('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'):
            if os.path.exists(p):
                chrome = p
    node = version(['node', '--version']) if shutil.which('node') else ''
    node_ok = bool(node) and int(node.lstrip('v').split('.')[0]) >= 22
    filas = [
        ('Python ≥ 3.10', sys.version_info >= (3, 10), platform.python_version(), 'imprescindible', 'compilar el aula y generar el paquete de Canvas',
         instalar('python3', 'python', 'Python.Python.3.12', 'https://www.python.org/downloads/')),
        ('Node ≥ 22', node_ok, node or 'no está', 'verificación', 'comprobar el aula sin abrirla y exportar los PDF',
         instalar('nodejs  (o https://nodejs.org)', 'node', 'OpenJS.NodeJS.LTS', 'https://nodejs.org')),
        ('Chrome / Edge / Chromium', bool(chrome), chrome or 'no está', 'verificación', 'lo mismo: el aula se revisa y se imprime con el navegador',
         instalar('chromium-browser', '--cask google-chrome', 'Google.Chrome', 'https://www.google.com/chrome/')),
        ('pdftotext (poppler)', bool(shutil.which('pdftotext')), version(['pdftotext', '-v']) or 'no está', 'insumos', 'leer el sílabo y los PDF del docente',
         instalar('poppler-utils', 'poppler', 'oschwartz10612.Poppler')),
        ('LibreOffice', bool(shutil.which('soffice') or shutil.which('libreoffice')), 'sí' if shutil.which('soffice') or shutil.which('libreoffice') else 'no está',
         'opcional', 'convertir .doc y .ppt antiguos (los .docx y .pptx se leen sin él)', instalar('libreoffice', '--cask libreoffice', 'TheDocumentFoundation.LibreOffice')),
        ('ffmpeg', bool(shutil.which('ffmpeg')), version(['ffmpeg', '-version'])[:40] or 'no está', 'videos', 'poner portada y cierre UTI a los videos',
         instalar('ffmpeg', 'ffmpeg', 'Gyan.FFmpeg')),
        ('nlm (NotebookLM)', bool(shutil.which('nlm')), version(['nlm', '--version']) or 'no está', 'opcional', 'generar los videos sin entrar a la web (hay modo manual)',
         'uv tool install notebooklm-mcp-cli   (o: pipx install notebooklm-mcp-cli) y luego: nlm login'),
    ]
    if '--json' in sys.argv:
        print(json.dumps([dict(que=f[0], ok=f[1], version=f[2], tipo=f[3], para=f[4], instalar=f[5]) for f in filas], ensure_ascii=False, indent=1))
        return 0
    print(f'Equipo: {SO} {platform.release()}\n')
    for que, ok, ver, tipo, para, como in filas:
        print(f'  {"✓" if ok else "✗"} {que:26s} {ver[:44]:46s} [{tipo}]')
        if not ok:
            print(f'      Sirve para {para}.\n      Cómo instalarlo: {como}')
    falta = [f[0] for f in filas if not f[1] and f[3] == 'imprescindible']
    sin_verif = [f[0] for f in filas if not f[1] and f[3] == 'verificación']
    print()
    if falta:
        print('No se puede continuar sin: ' + ', '.join(falta))
        return 1
    if sin_verif:
        print('Se puede construir el aula, pero sin ' + ' ni '.join(sin_verif) + ' no se podrá verificar automáticamente ni exportar los PDF.')
    else:
        print('Todo lo necesario para construir, verificar y exportar está instalado.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
