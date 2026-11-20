"""Aula ficticia reproducible desde la fuente actual, sin red ni cuentas."""
import atexit
import os
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault('AULA_SIN_RED', '1')     # sin consultas a GitHub en las pruebas

@lru_cache(maxsize=1)
def aula_demo():
    temporary = tempfile.TemporaryDirectory(prefix='uti-tests-')
    atexit.register(temporary.cleanup)
    aula = Path(temporary.name) / 'aula'
    def run(*args, cwd=None):
        r = subprocess.run([sys.executable, *map(str, args)], cwd=cwd, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stdout + r.stderr)
    run(ROOT/'aula-virtual-uti/scripts/nuevo_aula.py', aula, '--nombre', 'Curso Prueba', '--periodo', 'B26')
    subprocess.run(['git', '-C', str(aula), 'remote', 'add', 'origin', 'https://github.com/ejemplo/aula-ficticia.git'], check=True)   # GitHub obligatorio
    shutil.copy2(aula/'canvas/silabo.ejemplo.json', aula/'canvas/silabo.json')
    run('hub/tools/autonomo.py', '--sin-paquete', cwd=aula)
    run('canvas/generar_canvas.py', cwd=aula)
    return aula
