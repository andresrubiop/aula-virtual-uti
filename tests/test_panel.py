"""Panel local de avance con aulas ficticias: se deriva de ESTADO.md, no lo modifica ni crea otro registro."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fixture import aula_demo

SKILL = Path(__file__).resolve().parents[1] / 'aula-virtual-uti'
PLANTILLA = SKILL / 'assets/plantilla-aula'
PANEL = PLANTILLA / 'control/panel.py'
ESTADO = PLANTILLA / 'control/estado.py'


def huellas(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


class Panel(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.estado = (PLANTILLA / 'ESTADO.md').read_text(encoding='utf-8')
        self.write('ESTADO.md', self.estado)
        self.write('hub/src/course.json', {'title': {'es': 'Curso Ficticio', 'en': 'Mock Course'}, 'term': 'B26', 'units': []})
        self.write('fuentes/LEEME.md', 'Carpeta de insumos ficticia.')

    def write(self, name, value):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value, encoding='utf-8')
        return p

    def panel(self, root=None, code=0):
        r = subprocess.run([sys.executable, PANEL, '--aula', root or self.root, '--json'], capture_output=True, text=True)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        html = (Path(root or self.root) / 'PANEL.html').read_text(encoding='utf-8')
        return (json.loads(r.stdout) if code == 0 else None), html

    def edit_estado(self, old, new):
        text = (self.root / 'ESTADO.md').read_text(encoding='utf-8')
        self.assertIn(old, text)
        self.write('ESTADO.md', text.replace(old, new, 1))

    def acceso(self, datos, rel):
        return next(a for g in datos['accesos'] for a in g['accesos'] if a['ruta'] == rel)

    def test_plantilla_genera_panel_sin_modificar_nada_mas(self):
        antes = huellas(self.root)
        datos, html = self.panel()
        despues = huellas(self.root)
        self.assertEqual(set(despues) - set(antes), {'PANEL.html'})
        self.assertEqual({k: v for k, v in despues.items() if k != 'PANEL.html'}, antes)
        self.assertEqual(len(datos['fases']), 10)
        self.assertEqual(datos['titulo'], 'Curso Ficticio')
        self.assertEqual(datos['estado_sha256'], hashlib.sha256(self.estado.encode('utf-8')).hexdigest())
        self.assertIn('Panel de avance del aula', html)
        self.assertIn('0 de 10 fases', html)
        self.assertNotIn('http://', html.replace('http://www.w3.org', ''))
        self.assertNotIn('https://', html)
        self.assertNotIn('<script', html)

    def test_lo_que_espera_al_docente(self):
        self.edit_estado('(ninguna todavía)', '- ¿Se mantiene la práctica 2 del sílabo anterior?\n- ¿Videos en inglés?')
        self.edit_estado('| 3 · Planificación (`PLANIFICACION.md`) aprobada por el docente | ⬜ | |',
                         '| 3 · Planificación (`PLANIFICACION.md`) aprobada por el docente | ⛔ | Falta confirmar el orden de U2 y U3 |')
        self.edit_estado('[ninguno confirmado todavía]', 'Esperando la guía de laboratorio actualizada.')
        datos, html = self.panel()
        tipos = [n['tipo'] for n in datos['necesita']]
        self.assertEqual(tipos, ['pregunta', 'pregunta', 'bloqueo', 'fase'])
        self.assertIn('Falta confirmar el orden de U2 y U3', html)
        self.assertIn('Esperando la guía de laboratorio actualizada.', html)
        self.assertEqual(next(f for f in datos['fases'] if f['fase'] == 3)['icono'], '⛔')

    def test_marcadores_de_plantilla_no_son_pendientes(self):
        datos, html = self.panel()
        self.assertEqual(datos['necesita'], [])
        self.assertIn('Nada registrado por ahora', html)
        self.assertEqual(datos['unidades']['filas'], [], 'la fila de ejemplo vacía no se presenta como unidad')

    def test_texto_de_estado_se_escapa(self):
        self.edit_estado('(ninguna todavía)', '- <script>alert(1)</script> ¿y <img src=x onerror=alert(2)>?')
        self.edit_estado('| U1 (ejemplo de la plantilla: reemplazar) | — |',
                         '| U1 <b onclick="x()">Hilos</b> | ✅ Lista |')
        _, html = self.panel()
        self.assertNotIn('<script>alert', html)
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('<b onclick', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_unidades_con_iconos_y_formato_minimo(self):
        self.edit_estado('| U1 (ejemplo de la plantilla: reemplazar) | — | — | — | — | — | — | — | — | — | — |',
                         '| U1 Procesos | ✅ | ✅ | ✅ | 🟡 | ⬜ | ✅ | ⬜ | ✅ | ⬜ | ⏭ |\n'
                         '| U2 `hilos` | 🟡 | — | — | — | — | — | — | — | — | — |')
        datos, html = self.panel()
        self.assertEqual([f[0] for f in datos['unidades']['filas']], ['U1 Procesos', 'U2 `hilos`'])
        self.assertIn('<td class="ok">✅</td>', html)
        self.assertIn('<code>hilos</code>', html)

    def test_accesos_existentes_y_compilacion_anterior(self):
        dist = self.write('hub/dist/index.html', '<!doctype html><title>aula</title>')
        old = time.time() - 600
        os.utime(dist, (old, old))
        self.write('hub/src/content/u1/30-presentacion.html', '<section>nuevo</section>')
        self.write('materiales/unidad-1/M1_manual.pdf', '%PDF-1.4 ficticio')
        datos, html = self.panel()
        aula = self.acceso(datos, 'hub/dist/index.html')
        self.assertTrue(aula['existe'])
        self.assertTrue(any('hub/src/content/u1/30-presentacion.html' in a for a in aula['avisos']))
        self.assertFalse(self.acceso(datos, 'hub/dist/profesor.html')['existe'])
        self.assertIn('href="hub/dist/index.html"', html)
        self.assertIn('href="materiales/unidad-1/M1_manual.pdf"', html)
        self.assertIn('Aún no existe <code>hub/dist/profesor.html</code>', html)
        self.assertTrue(self.acceso(datos, 'materiales/unidad-1/M1_manual.pdf')['avisos'] == [])

    def test_no_enlaza_privados_ni_enlaces_simbolicos(self):
        self.write('materiales/privado/notas.pdf', '%PDF-1.4 privado')
        self.write('materiales/unidad-1/vacio.pdf', '')
        externo = self.write('fuera.pdf', '%PDF-1.4 externo')
        (self.root / 'materiales/unidad-1/enlace.pdf').symlink_to(externo)
        datos, html = self.panel()
        rutas = [a['ruta'] for g in datos['accesos'] for a in g['accesos']]
        self.assertFalse([r for r in rutas if 'privado' in r or r.endswith(('enlace.pdf', 'vacio.pdf'))])
        self.assertNotIn('privado/notas.pdf', html)

    def test_evidencia_vigente_y_luego_cambiada(self):
        self.write('hub/dist/index.html', '<!doctype html><title>aula</title>')
        self.write('control/compilacion.txt', 'Compilación ficticia del escenario de prueba.')
        r = subprocess.run([sys.executable, ESTADO, '--aula', self.root, 'registrar', 'compilacion', '--fase', '0',
                            '--entregable', 'hub/dist/index.html', '--fuente', 'hub/src/course.json',
                            '--prueba', 'control/compilacion.txt', '--resultado', 'pasado'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        datos, _ = self.panel()
        self.assertIn('vigente (compilacion)', self.acceso(datos, 'hub/dist/index.html')['comprobacion'])
        self.write('hub/src/course.json', {'title': {'es': 'Curso Ficticio cambiado'}, 'units': []})
        datos, _ = self.panel()
        self.assertTrue(self.acceso(datos, 'hub/dist/index.html')['comprobacion'].startswith('Cambió'))
        self.assertTrue(datos['comprobaciones']['impacto']['afectados'])

    def test_estado_dañado_o_ausente(self):
        self.edit_estado('"version": 1', '"version": 9')
        datos, html = self.panel()
        self.assertTrue(datos['aviso_registro'])
        self.assertIn('No se pudo comprobar', html)
        (self.root / 'ESTADO.md').unlink()
        _, html = self.panel(code=2)
        self.assertIn('Panel no generado', html)
        self.assertNotIn('Panel de avance del aula', html)

    def test_panel_no_es_evidencia(self):
        self.panel()
        r = subprocess.run([sys.executable, ESTADO, '--aula', self.root, 'registrar', 'x', '--fase', '0',
                            '--entregable', 'PANEL.html', '--fuente', 'hub/src/course.json', '--resultado', 'no_ejecutado'],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('informe derivado', r.stderr)

    def test_aula_completa_con_entrega_y_ficha(self):
        aula = self.root / 'aula'
        shutil.copytree(aula_demo(), aula, ignore=shutil.ignore_patterns('__pycache__'))
        r = subprocess.run([sys.executable, 'control/panel.py', '--json'], cwd=aula, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        datos = json.loads(r.stdout)
        rutas = [a['ruta'] for g in datos['accesos'] for a in g['accesos'] if a['existe']]
        self.assertIn('hub/dist/index.html', rutas)
        self.assertTrue(any(x.startswith('autonomo/') and x.endswith('.html') for x in rutas))
        self.assertTrue(any(x.startswith('canvas/salida/') and x.endswith('.imscc') for x in rutas))
        self.assertTrue(datos['comprobaciones']['ficha'].get('no_iniciada'))
        self.write('aula/fuentes/silabo/vigente.pdf', '%PDF-1.4 ficticio')
        self.write('aula/fuentes/_texto/silabo/vigente.pdf.txt', 'Curso Prueba\fsin más datos')
        r = subprocess.run([sys.executable, 'control/ficha_silabo.py', 'iniciar', '--documento', 'fuentes/silabo/vigente.pdf'],
                           cwd=aula, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, 'control/panel.py', '--json'], cwd=aula, capture_output=True, text=True)
        datos = json.loads(r.stdout)
        ficha = datos['comprobaciones']['ficha']
        self.assertGreater(ficha['campos'], 0)
        self.assertFalse(ficha['revisada'])
        self.assertTrue(any(n['tipo'] == 'revision' for n in datos['necesita']))

    def test_aula_anterior_con_aula(self):
        """Un aula creada antes de la mejora no tiene control/panel.py: se usa el de la skill con --aula."""
        self.assertFalse((self.root / 'control/panel.py').exists())
        datos, _ = self.panel()
        self.assertEqual(datos['comprobaciones']['estado'].get('resultado'), 'sin_incidencias')


if __name__ == '__main__':
    unittest.main()
