"""canvas/canvas_api.py contra un Canvas ficticio en memoria (sin red, sin cuentas, sin datos reales)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixture import aula_demo
import fake_canvas


class CanvasApi(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('shots'))
        self.curso = fake_canvas.Curso()
        self.curso.sembrar_desde_plantilla(self.aula / 'canvas/plantilla/plantilla-uti.imscc')
        self.inicio_original = next(p for p in self.curso.pages.values() if p['front_page'])['body']
        self.srv, self.url = fake_canvas.iniciar(self.curso)
        self.addCleanup(self.srv.shutdown)
        self.env = {**os.environ, 'CANVAS_TOKEN': fake_canvas.TOKEN, 'HOME': self.tmp.name}
        self.run_api('configurar', '--curso', self.url)

    def run_api(self, *args, code=0, env=None):
        r = subprocess.run([sys.executable, 'canvas/canvas_api.py', *args], cwd=self.aula, capture_output=True, text=True, env=env or self.env)
        if code is not None:
            self.assertEqual(r.returncode, code, r.stdout[-3000:] + r.stderr[-3000:])
        return r

    def test_sin_token_no_hace_nada(self):
        env = {k: v for k, v in self.env.items() if k != 'CANVAS_TOKEN'}
        r = self.run_api('plan', code=None, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('token', r.stderr.lower())
        self.assertEqual(self.curso.log, [])

    def test_token_pegado_en_el_chat_se_guarda_sin_mostrarlo(self):
        r = subprocess.run([sys.executable, 'canvas/canvas_api.py', 'token', '--stdin'], cwd=self.aula, input=fake_canvas.TOKEN + '\n',
                           capture_output=True, text=True, encoding='utf-8', env={k: v for k, v in self.env.items() if k != 'CANVAS_TOKEN'})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn(fake_canvas.TOKEN, r.stdout + r.stderr)
        self.assertIn('Revócalo', r.stdout)
        guardado = Path(self.tmp.name) / '.config/aula-uti/canvas-token'
        self.assertEqual(guardado.read_text(encoding='utf-8').strip(), fake_canvas.TOKEN)
        if os.name != 'nt':
            self.assertEqual(oct(guardado.stat().st_mode & 0o777), '0o600')
        self.assertFalse([p for p in self.aula.rglob('*') if p.is_file() and fake_canvas.TOKEN.encode() in p.read_bytes()])
        # con el token guardado (sin variable de entorno) la herramienta funciona
        self.run_api('comprobar', env={k: v for k, v in self.env.items() if k != 'CANVAS_TOKEN'})
        r = subprocess.run([sys.executable, 'canvas/canvas_api.py', 'token', '--stdin'], cwd=self.aula, input='no es un token',
                           capture_output=True, text=True, encoding='utf-8', env=self.env)
        self.assertNotEqual(r.returncode, 0)

    def test_token_rechazado(self):
        r = self.run_api('comprobar', code=None, env={**self.env, 'CANVAS_TOKEN': 'x' * 30})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('401', r.stderr)

    def test_comprobar_y_plan_son_solo_lectura(self):
        r = self.run_api('comprobar')
        inv = json.loads((self.aula / 'canvas/api/inventario.json').read_text())
        self.assertEqual(inv['inscripciones_por_tipo'], {'StudentEnrollment': 3, 'TeacherEnrollment': 1})
        self.assertNotIn(fake_canvas.TOKEN, r.stdout + (self.aula / 'canvas/api/inventario.json').read_text())
        self.run_api('plan', '--paquete', str(self.paquete()))
        plan = json.loads((self.aula / 'canvas/api/plan.json').read_text())
        self.assertIn('presentacion', plan['paginas_a_actualizar'])
        self.assertTrue(plan['paginas_a_crear'])
        self.assertTrue(plan['paginas_a_despublicar'])
        self.assertTrue(plan['inicio'].startswith('anteponer el aula'))
        self.assertEqual(self.curso.log, [])

    def paquete(self):
        return next((self.aula / 'canvas/salida').glob('*-aula-canvas.imscc'))

    def test_aplicar_actualiza_sin_duplicar_ni_publicar(self):
        r = self.run_api('aplicar', '--paquete', str(self.paquete()), '--permitir-pendientes', code=None)
        self.assertIn('Aplicado', r.stdout, r.stdout[-2000:] + r.stderr[-2000:])
        c = self.curso
        n_pag, n_tar, n_mod = len(c.pages), len(c.assignments), len(c.modules)
        # Inicio: el aula al comienzo y el contenido institucional intacto debajo
        inicio = next(p for p in c.pages.values() if p['front_page'])
        self.assertTrue(inicio['body'].startswith('<!--aula-inicio--><div id="aula-interactiva-inicio"'))
        self.assertTrue(inicio['body'].endswith(self.inicio_original))
        self.assertRegex(inicio['body'], r'<iframe[^>]*src="/courses/1/files/\d+/download"')
        # Ninguna tarea publicada, aunque los módulos se publicaron
        self.assertFalse([a['name'] for a in c.assignments.values() if a['published']])
        # Sin referencias del paquete por resolver ni enlaces al curso de la plantilla
        for p in c.pages.values():
            self.assertNotRegex(p['body'], r'\$(IMS-CC-FILEBASE|WIKI_REFERENCE|CANVAS_[A-Z_]+)\$', p['url'])
            self.assertNotRegex(p['body'], r'/courses/(?!1/)\d+/', p['url'])
        # Las páginas genéricas antiguas quedan sin publicar y fuera de los módulos
        plan = json.loads((self.aula / 'canvas/api/plan.json').read_text())
        en_mod = {it.get('page_url') for m in c.modules.values() for it in m['items']}
        for u in plan['paginas_a_despublicar']:
            self.assertFalse(c.pages[u]['published'], u)
            self.assertNotIn(u, en_mod)
        # Respaldo del curso antes de cambiar, privado
        respaldos = list((self.aula / 'canvas/api/privado').glob('respaldo-*.json'))
        self.assertEqual(len(respaldos), 1)
        self.assertEqual(oct(respaldos[0].stat().st_mode & 0o777), '0o600')
        ver = json.loads((self.aula / 'canvas/api/verificacion.json').read_text())
        self.assertTrue(ver['aula_en_inicio'])
        self.assertFalse([p for p in ver['problemas'] if 'inexistente' in p or 'sin resolver' in p], ver['problemas'])
        # Segunda ejecución: actualiza, no duplica, y el aula no se repite en Inicio
        subidas = sum(1 for x in c.log if x[0] == 'UPLOAD')
        self.assertTrue(subidas)
        self.run_api('aplicar', '--paquete', str(self.paquete()), '--permitir-pendientes', code=None)
        self.assertEqual((len(c.pages), len(c.assignments), len(c.modules)), (n_pag, n_tar, n_mod))
        inicio = next(p for p in c.pages.values() if p['front_page'])
        self.assertEqual(inicio['body'].count('aula-interactiva-inicio'), 1)
        self.assertEqual(sum(1 for x in c.log if x[0] == 'UPLOAD'), subidas)   # nada se vuelve a subir
        self.assertNotIn(fake_canvas.TOKEN, (self.aula / 'canvas/api/operaciones.jsonl').read_text())

    def test_marcas_pendientes_bloquean_aplicar(self):
        r = self.run_api('aplicar', '--paquete', str(self.paquete()), code=None)
        plan = json.loads((self.aula / 'canvas/api/plan.json').read_text())
        if plan['marcas_pendientes_visibles']:
            self.assertNotEqual(r.returncode, 0)
            self.assertFalse([x for x in self.curso.log if x[0] != 'GET'])

    def test_inicio_solo(self):
        self.run_api('inicio', '--paquete', str(self.paquete()))
        self.assertEqual(self.curso.log, [])
        # Sin archivo del aula en el curso no se puede resolver el enlace: se sube primero con aplicar
        r = self.run_api('inicio', '--paquete', str(self.paquete()), '--aplicar', code=None)
        if r.returncode == 0:
            inicio = next(p for p in self.curso.pages.values() if p['front_page'])
            self.assertTrue(inicio['body'].endswith(self.inicio_original))


if __name__ == '__main__':
    unittest.main()
