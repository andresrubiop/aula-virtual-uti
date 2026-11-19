"""Mejora 11: glosario ES/EN (control/glosario.py) y estado visible de los videos en el panel, con aulas ficticias."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixture import aula_demo


class Glosario(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots', 'autonomo'))
        self.manual = self.aula / 'hub/src/content/u1/50-manual.html'
        self.recursos = self.aula / 'hub/src/content/95-recursos.html'

    def run_tool(self, *args, code=0):
        r = subprocess.run([sys.executable, 'control/glosario.py', *args, '--json'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, code, r.stdout[-1500:] + r.stderr)
        return json.loads(r.stdout)

    def agregar(self, archivo, fragmento):
        t = archivo.read_text(encoding='utf-8')
        archivo.write_text(t.replace('</article>', fragmento + '</article>', 1), encoding='utf-8')

    def test_plantilla_coherente(self):
        d = self.run_tool()
        self.assertEqual(d['terminos'], 2)
        self.assertEqual(d['errores'], [])
        self.assertEqual(d['avisos'], [])
        self.assertGreater(d['usos']['repaso espaciado'], 0)
        self.assertIn('## Uso de cada término', (self.aula / 'control/GLOSARIO.md').read_text(encoding='utf-8'))

    def test_traduccion_distinta_se_informa(self):
        self.agregar(self.manual, '<p><span lang="es">El repaso espaciado mejora el recuerdo.</span>'
                                  '<span lang="en">Distributed practice improves recall.</span></p>')
        d = self.run_tool()
        self.assertEqual(len(d['avisos']), 1)
        self.assertEqual(d['avisos'][0]['termino'], 'repaso espaciado')
        self.assertIn('50-manual.html', d['avisos'][0]['donde'])

    def test_variante_aceptada_y_plural(self):
        t = self.recursos.read_text(encoding='utf-8').replace('<em>spaced review</em>', '<em>spaced review / spaced repetition</em>')
        self.recursos.write_text(t, encoding='utf-8')
        self.agregar(self.manual, '<p><span lang="es">Los repasos espaciados ayudan.</span><span lang="en">Spaced repetitions help.</span></p>')
        self.assertEqual(self.run_tool()['avisos'], [])

    def test_dos_traducciones_en_el_glosario_es_error(self):
        t = self.recursos.read_text(encoding='utf-8').replace(
            '</dl>', '<div class="gloss__item"><dt>repaso espaciado · <em>spaced practice</em></dt><dd>x</dd></div></dl>', 1)
        self.recursos.write_text(t, encoding='utf-8')
        d = self.run_tool(code=1)
        self.assertTrue(any('repaso espaciado' in e for e in d['errores']))

    def test_subtitulos_y_propuestas(self):
        sub = self.aula / 'videos/subtitulos'; sub.mkdir(parents=True)
        (sub / 'V1.1.json').write_text(json.dumps([[3, 5, 'Distributed practice works.']]), encoding='utf-8')
        (sub / 'V1.1.es.txt').write_text('1|El repaso espaciado funciona.\n', encoding='utf-8')
        self.agregar(self.manual, '<p><span lang="es">Elige el <strong>intervalo de repaso</strong> según la fecha.</span>'
                                  '<span lang="en">Choose the <strong>review interval</strong> by date.</span></p>'
                                  '<p><span lang="es"><strong>Entrega:</strong> un plan.</span><span lang="en"><strong>Submission:</strong> a plan.</span></p>')
        d = self.run_tool('proponer')
        self.assertTrue(any(a['donde'].startswith('videos/subtitulos/V1.1') for a in d['avisos']))
        es = [c['es'] for c in d['propuestos']]
        self.assertIn('intervalo de repaso', es)
        self.assertNotIn('Entrega', es)                     # una negrita con dos puntos es un rótulo


class VideosEnPanel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots', 'autonomo'))

    def videos(self):
        r = subprocess.run([sys.executable, 'control/panel.py', '--json'], cwd=self.aula, capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        return {x['video']: x for x in json.loads(r.stdout)['comprobaciones']['videos']['lista']}

    def test_estado_de_cada_video(self):
        g = self.aula / 'videos/guiones'; g.mkdir(parents=True, exist_ok=True)
        for v in ('V1.1', 'V1.2', 'V2.1'):
            (g / f'{v}.md').write_text(f'# {v} · Título | Title\n', encoding='utf-8')
        u = self.aula / 'videos/unidad-1'; u.mkdir(parents=True, exist_ok=True)
        (u / 'V1.1.en.mp4').write_bytes(b'mp4'); (u / 'V1.1.en.es.vtt').write_text('WEBVTT\n', encoding='utf-8')
        (u / 'V1.2.en.mp4').write_bytes(b'mp4')
        (self.aula / 'videos/estado.json').write_text(json.dumps({'2.en': {'nb': 'x', 'V2.1': 'id'}}), encoding='utf-8')
        v = self.videos()
        self.assertEqual(v['V1.1']['estado'], 'inglés: en el aula · subtítulos en español')
        self.assertIn('faltan subtítulos en español', v['V1.2']['estado'])
        self.assertEqual(v['V2.1']['estado'], 'inglés: en NotebookLM')
        html = (self.aula / 'PANEL.html').read_text(encoding='utf-8') if (self.aula / 'PANEL.html').exists() else ''
        subprocess.run([sys.executable, 'control/panel.py'], cwd=self.aula, capture_output=True)
        self.assertIn('2 de 3 en el aula', (self.aula / 'PANEL.html').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
