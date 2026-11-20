"""Mejora 15: Canvas no ejecuta el JavaScript de los HTML subidos; el aula se publica en la web (GitHub Pages) y Canvas
la muestra desde allí. Sin red ni cuentas: se prueba la revisión previa, el generador y la API contra el Canvas ficticio."""
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
import fake_canvas

URL = 'https://docente-ficticio.github.io/aula-ficticia/'


def revisar(aula, datos, cual):
    r = subprocess.run([sys.executable, '-c', 'import sys, json; sys.path.insert(0, "control"); import publicar_web as p; '
                        f'print(json.dumps(p.revisar(sys.stdin.buffer.read(), {cual!r})))'],
                       cwd=aula, input=datos, capture_output=True, env={**os.environ, 'HOME': str(aula)})
    return json.loads(r.stdout)


class PublicarWeb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('shots'))
        self.course = self.aula / 'hub/src/course.json'

    def publicar_ficticio(self):
        d = json.loads(self.course.read_text(encoding='utf-8'))
        d['publicacion'] = {'url': URL, 'repo': 'docente-ficticio/aula-ficticia', 'edicion': 'profesor', 'sha256': '0' * 64, 'servida': True}
        self.course.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')

    def generar(self):
        return subprocess.run([sys.executable, 'canvas/generar_canvas.py', '--borrador'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')

    def test_revision_antes_de_publicar(self):
        limpio = b'<html><body>Aula</body></html>'
        self.assertEqual(revisar(self.aula, limpio, 'estudiante'), [])
        docente = b'<p>x</p><!--docente--><p>solucionario</p><!--/docente-->'
        self.assertTrue(any('docente' in x for x in revisar(self.aula, docente, 'estudiante')))
        self.assertEqual(revisar(self.aula, docente, 'profesor'), [])      # la del profesor se publica a pedido expreso
        self.assertTrue(any('token' in x for x in revisar(self.aula, b'clave 12345~' + b'a' * 64, 'profesor')))
        self.assertTrue(any('teléfono' in x for x in revisar(self.aula, b'llama al 0991234567', 'profesor')))

    def test_sin_publicar_avisa_y_usa_el_archivo(self):
        r = self.generar()
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertIn('no está publicada en la web', r.stdout + r.stderr)
        inicio = (self.aula / 'canvas/salida/pegar/inicio-SOLO-AL-COMIENZO.html').read_text(encoding='utf-8')
        self.assertNotIn('github.io', inicio)

    def test_publicada_el_marco_y_abrir_usan_la_web(self):
        self.publicar_ficticio()
        r = self.generar()
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.assertNotIn('no está publicada en la web', r.stdout + r.stderr)
        for f in ('inicio-SOLO-AL-COMIENZO.html', 'aula-interactiva.html'):
            t = (self.aula / 'canvas/salida/pegar' / f).read_text(encoding='utf-8')
            self.assertRegex(t, r'<iframe[^>]*src="' + re.escape(URL) + '"', f)
            self.assertIn(f'href="{URL}"', t, f)

    def test_estado_sin_publicar(self):
        r = subprocess.run([sys.executable, 'control/publicar_web.py', '--json'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(json.loads(r.stdout)['url'])


class CanvasConAulaWeb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('shots'))
        c = self.aula / 'hub/src/course.json'
        d = json.loads(c.read_text(encoding='utf-8')); d['publicacion'] = {'url': URL}
        c.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        r = subprocess.run([sys.executable, 'canvas/generar_canvas.py', '--borrador'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr[-1500:])
        self.curso = fake_canvas.Curso()
        self.curso.sembrar_desde_plantilla(self.aula / 'canvas/plantilla/plantilla-uti.imscc')
        self.srv, self.url = fake_canvas.iniciar(self.curso)
        self.addCleanup(self.srv.shutdown)
        self.env = {**os.environ, 'CANVAS_TOKEN': fake_canvas.TOKEN, 'HOME': self.tmp.name}
        self.api('configurar', '--curso', self.url)

    def api(self, *args):
        return subprocess.run([sys.executable, 'canvas/canvas_api.py', *args], cwd=self.aula, capture_output=True, text=True, env=self.env)

    def test_inicio_con_aula_web_y_enlaces_tras_renombrar(self):
        c = self.curso
        # Como en un curso real: la página «Momento 2» tiene una URL larga (otro título anterior) y Inicio la enlaza
        p = c.pages.pop('momento-2'); p['url'] = 'momento-2-fase-de-diseno'; p['title'] = 'Momento 2: Fase de diseño'
        c.pages[p['url']] = p
        portada = next(x for x in c.pages.values() if x['front_page'])
        portada['body'] = portada['body'].replace('/pages/momento-2"', '/pages/momento-2-fase-de-diseno"')
        mapa = self.aula / 'canvas/api/mapa.json'
        m = json.loads(mapa.read_text(encoding='utf-8')) if mapa.exists() else {}
        m.setdefault('paginas', {})['momento-2'] = 'momento-2-fase-de-diseno'
        mapa.write_text(json.dumps(m), encoding='utf-8')
        paquete = next((self.aula / 'canvas/salida').glob('*-aula-canvas.imscc'))
        r = self.api('aplicar', '--paquete', str(paquete), '--permitir-pendientes')
        self.assertIn('Aplicado', r.stdout, r.stdout[-2000:] + r.stderr[-2000:])
        inicio = next(x for x in c.pages.values() if x['front_page'])['body']
        self.assertRegex(inicio, r'<iframe[^>]*src="' + re.escape(URL) + '"')
        self.assertNotIn('/pages/momento-2-fase-de-diseno', inicio)        # el enlace sigue a la URL nueva
        ver = json.loads((self.aula / 'canvas/api/verificacion.json').read_text())
        self.assertFalse([x for x in ver['problemas'] if 'inexistente' in x], ver['problemas'])


if __name__ == '__main__':
    unittest.main()
