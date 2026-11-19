"""Mejora 10: calidad pedagógica (control/calidad.py) y accesibilidad (hub/tools/accesibilidad.mjs), con aulas ficticias."""
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


def hay_navegador():
    if os.environ.get('CHROME') or shutil.which('node') is None:
        return bool(os.environ.get('CHROME')) and shutil.which('node') is not None
    return any(shutil.which(c) for c in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'))


class Calidad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots', 'autonomo'))
        u1 = self.aula / 'hub/src/content/u1'
        for f in u1.glob('*.html'):                 # una unidad «terminada»: sin marcas de relleno
            f.write_text(re.sub(r'\[COMPLETAR[^\]]*\]', 'texto del docente', f.read_text(encoding='utf-8')), encoding='utf-8')

    def calidad(self, code=None):
        r = subprocess.run([sys.executable, 'control/calidad.py', '--json'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        if code is not None:
            self.assertEqual(r.returncode, code, r.stdout[-2000:] + r.stderr)
        return json.loads(r.stdout), r.returncode

    def fila(self, datos, que):
        return next(f for f in datos['unidades'][0]['comprobaciones'] if f['que'].startswith(que))

    def test_unidad_de_la_plantilla_completa(self):
        datos, _ = self.calidad(code=0)
        u = datos['unidades'][0]
        self.assertEqual(u['faltan'], 0, u['comprobaciones'])
        self.assertEqual(self.fila(datos, 'Rúbrica')['estado'], 'ok')
        self.assertEqual(self.fila(datos, 'Retroalimentación')['estado'], 'ok')
        md = (self.aula / 'control/CALIDAD.md').read_text(encoding='utf-8')
        self.assertIn('**Revisión del docente**', md)
        self.assertIn('- [ ] Los ejemplos son pertinentes', md)

    def test_detecta_rubrica_incompleta_y_falta_de_desafio(self):
        p = self.aula / 'hub/src/content/u1/60-practica.html'
        t = p.read_text(encoding='utf-8').replace('Cocreativo', 'Avanzado').replace('<!--@@desafio:PR1@@-->', '')
        p.write_text(t, encoding='utf-8')
        datos, code = self.calidad()
        self.assertEqual(code, 1)
        self.assertEqual(self.fila(datos, 'Rúbrica')['estado'], 'falta')
        self.assertIn('Cocreativo', self.fila(datos, 'Rúbrica')['detalle'])
        self.assertEqual(self.fila(datos, 'Desafío')['estado'], 'falta')

    def test_detecta_pregunta_sin_retroalimentacion(self):
        p = self.aula / 'hub/src/content/u1/80-quiz.html'
        t = p.read_text(encoding='utf-8')
        m = re.search(r'(<script type="application/json">)(.*?)(</script>)', t, re.S)
        q = json.loads(m[2]); q['questions'][0]['why'] = q['questions'][0]['why'][:1]
        p.write_text(t[:m.start(2)] + json.dumps(q, ensure_ascii=False) + t[m.end(2):], encoding='utf-8')
        datos, code = self.calidad()
        self.assertEqual(code, 1)
        f = self.fila(datos, 'Retroalimentación')
        self.assertEqual(f['estado'], 'falta'); self.assertIn('[1]', f['detalle'])

    def test_resumen_sin_ra_ni_evidencia(self):
        p = self.aula / 'hub/src/content/u1/10-resumen.html'
        t = re.sub(r'\bRA\d\b', 'Resultado', p.read_text(encoding='utf-8'))
        t = re.sub(r'(?i)evidencia|evidence|producto|entrega|deliverable', 'parte', t)
        p.write_text(t, encoding='utf-8')
        datos, code = self.calidad()
        self.assertEqual(code, 1)
        self.assertEqual(self.fila(datos, 'Resultados de aprendizaje')['estado'], 'falta')
        self.assertEqual(self.fila(datos, 'Evidencia')['estado'], 'falta')


@unittest.skipUnless(hay_navegador(), 'requiere node y Chrome/Chromium')
class Accesibilidad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots', 'autonomo'))

    def revisar(self, *rutas):
        subprocess.run([sys.executable, 'hub/build.py'], cwd=self.aula, capture_output=True, check=True)
        r = subprocess.run(['node', 'hub/tools/accesibilidad.mjs', '--routes', ','.join(rutas), '--lang', 'es', '--tabs', '15'],
                           cwd=self.aula, capture_output=True, text=True, encoding='utf-8', timeout=300)
        return json.loads((self.aula / 'control/accesibilidad.json').read_text(encoding='utf-8')), r.returncode

    def test_plantilla_sin_errores_en_claro_y_oscuro(self):
        datos, code = self.revisar('#/u1/manual', '#/u1/animaciones')
        self.assertEqual(code, 0, datos['errores'])
        self.assertEqual(datos['errores'], [])
        self.assertGreater(datos['textos_contraste'], 50)
        self.assertEqual(datos['temas'], ['claro', 'oscuro'])
        self.assertIn('lector de pantalla', (self.aula / 'control/ACCESIBILIDAD.md').read_text(encoding='utf-8'))

    def test_detecta_imagen_sin_alt_contraste_y_boton_sin_nombre(self):
        p = self.aula / 'hub/src/content/u1/50-manual.html'
        t = p.read_text(encoding='utf-8')
        malo = ('<p style="color:#BBBBBB;background:#FFFFFF">Texto gris claro de prueba</p>'
                '<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" width="40" height="40">'
                '<button class="btn" style="width:40px;height:30px"></button>')
        p.write_text(t.replace('</article>', malo + '</article>', 1), encoding='utf-8')
        datos, code = self.revisar('#/u1/manual')
        self.assertEqual(code, 1)
        tipos = {e['tipo'] for e in datos['errores']}
        self.assertTrue({'imagen sin alt', 'contraste', 'control sin nombre'} <= tipos, tipos)


if __name__ == '__main__':
    unittest.main()
