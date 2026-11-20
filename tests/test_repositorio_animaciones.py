"""Mejora 14: el aula vive en GitHub (obligatorio) y cada temática tiene su animación (obligatorio). Sin red ni cuentas."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixture import aula_demo

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://github.com/ejemplo/aula-ficticia.git'


class Repositorio(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots'))
        self.bare = Path(self.tmp.name) / 'remoto.git'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(self.bare)], check=True)
        self.git('remote', 'remove', 'origin')
        # El «GitHub» de la prueba es un repositorio local: la URL de github.com se redirige a él
        self.git('config', f'url.{self.bare.as_uri()}.insteadOf', URL)
        self.git('config', 'user.name', 'Docente Ficticio'); self.git('config', 'user.email', 'docente@example.org')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.aula), *args], capture_output=True, text=True)

    def tool(self, *args, code=0):
        r = subprocess.run([sys.executable, 'control/repositorio.py', *args, '--json'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, code, r.stdout[-1500:] + r.stderr[-1500:])
        return json.loads(r.stdout) if r.stdout.strip().startswith('{') else r

    def test_sin_github_no_se_genera_canvas(self):
        e = self.tool(code=1)
        self.assertFalse(e['github'])
        self.assertTrue(any('GitHub' in x for x in e['errores']))
        r = subprocess.run([sys.executable, 'canvas/generar_canvas.py'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(r.returncode, 0); self.assertIn('repositorio de GitHub', r.stderr)
        r = subprocess.run([sys.executable, 'canvas/generar_canvas.py', '--borrador'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])

    def test_iniciar_y_guardar_suben_al_repositorio(self):
        e = self.tool('iniciar', '--remoto', URL)
        self.assertTrue(e['github']); self.assertEqual(e['sin_subir'], 0)
        self.assertIn('Aula creada', subprocess.run(['git', '-C', str(self.bare), 'log', '--oneline'], capture_output=True, text=True).stdout)
        (self.aula / 'hub/src/content/u1/nota.html').write_text('<p>cambio</p>', encoding='utf-8')
        r = self.tool('guardar', '-m', 'Unidad 1 revisada')
        self.assertTrue(r['commit']); self.assertTrue(r['subido']); self.assertEqual(r['estado']['cambios'], 0)
        self.assertIn('Unidad 1 revisada', subprocess.run(['git', '-C', str(self.bare), 'log', '--oneline'], capture_output=True, text=True).stdout)
        # lo privado y lo generado no se suben
        subidos = subprocess.run(['git', '-C', str(self.bare), 'ls-tree', '-r', '--name-only', 'main'], capture_output=True, text=True).stdout
        self.assertNotIn('fuentes/privado/', subidos); self.assertNotIn('hub/dist/', subidos); self.assertNotIn('canvas/salida/', subidos)
        self.assertIn('ESTADO.md', subidos)

    def test_guardar_detiene_tokens_y_credenciales(self):
        self.tool('iniciar', '--remoto', URL)
        malo = self.aula / 'control/notas.md'
        malo.write_text('token: 12345~' + 'a' * 64 + '\n', encoding='utf-8')
        r = self.tool('guardar', '-m', 'con token', code=1)
        self.assertIn('forma de token', r.stderr)
        malo.unlink()
        (self.aula / 'control/canvas-token').write_text('x\n', encoding='utf-8')
        r = self.tool('guardar', '-m', 'con archivo de token', code=1)
        self.assertIn('credencial', r.stderr)
        self.assertEqual(self.git('diff', '--cached', '--name-only').stdout.strip(), '')       # nada quedó preparado

    def test_entorno_exige_git(self):
        d = json.loads(subprocess.run([sys.executable, str(ROOT / 'aula-virtual-uti/scripts/entorno.py'), '--json'], capture_output=True, text=True, encoding='utf-8').stdout)
        tipos = {x['que']: x['tipo'] for x in d}
        self.assertEqual(tipos['Git'], 'imprescindible')
        self.assertEqual(tipos['Cuenta de GitHub (gh)'], 'obligatorio')

    def test_panel_muestra_github(self):
        subprocess.run([sys.executable, 'control/panel.py'], cwd=self.aula, capture_output=True)
        self.assertIn('Obligatorio: el aula debe estar en tu repositorio privado de GitHub', (self.aula / 'PANEL.html').read_text(encoding='utf-8'))


class Animaciones(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots'))
        self.course = self.aula / 'hub/src/course.json'

    def pendientes(self):
        r = subprocess.run([sys.executable, '-c', 'import sys; sys.path.insert(0, "control"); import calidad, json; print(json.dumps(calidad.animaciones_pendientes()))'],
                           cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        return json.loads(r.stdout)

    def generar(self, *extra):
        return subprocess.run([sys.executable, 'canvas/generar_canvas.py', *extra], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')

    def test_plantilla_cumple(self):
        self.assertEqual(self.pendientes(), [])
        self.assertEqual(self.generar().returncode, 0)

    def test_animacion_fuera_de_la_presentacion_bloquea(self):
        p = self.aula / 'hub/src/content/u1/30-presentacion.html'
        p.write_text(re.sub(r'data-anim="A1\.1"', 'data-anim-retirada="A1.1"', p.read_text(encoding='utf-8')), encoding='utf-8')
        pend = self.pendientes()
        self.assertEqual(len(pend), 1); self.assertIn('en la presentación', pend[0])
        r = self.generar()
        self.assertNotEqual(r.returncode, 0); self.assertIn('Faltan animaciones obligatorias', r.stderr)
        self.assertEqual(self.generar('--borrador').returncode, 0)

    def test_cada_tematica_necesita_la_suya(self):
        d = json.loads(self.course.read_text(encoding='utf-8'))
        d['units'][0]['sessions'] = [1, 2]
        self.course.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        pend = self.pendientes()
        self.assertEqual(len(pend), 1); self.assertIn('Sesión 2', pend[0])
        r = subprocess.run([sys.executable, 'control/calidad.py', '--json'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        filas = json.loads(r.stdout)['unidades'][0]['comprobaciones']
        self.assertTrue(any(f['area'] == 'Animaciones' and f['estado'] == 'falta' and 'Sesión 2' in f['que'] for f in filas))


if __name__ == '__main__':
    unittest.main()
