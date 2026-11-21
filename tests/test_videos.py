"""Videos: por omisión un solo video en inglés con subtítulos en español (sin cuentas ni red)."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from fixture import aula_demo


class Videos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots'))

    def run_py(self, *args, code=0):
        r = subprocess.run([sys.executable, *map(str, args)], cwd=self.aula, capture_output=True, text=True)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return r.stdout

    def test_por_omision_solo_ingles(self):
        src = (self.aula / 'videos/generar_videos.py').read_text()
        self.assertIn("else 'en').split(',')", src)
        g = self.aula / 'videos/guiones/V1.1.md'
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_text('# V1.1 · Título | Title\n\n## prompt es\nEnfoque.\n\n## prompt en\nFocus.\n')
        salida = self.run_py('videos/generar_videos.py', '--lista')
        self.assertIn('es: subtítulos pendientes', salida)
        self.assertIn('en: pendiente', salida)
        m = self.aula / 'materiales/unidad-1'; m.mkdir(parents=True, exist_ok=True)
        (m / 'M1_manual.en.pdf').write_bytes(b'%PDF-1.4 ficticio')
        manual = self.run_py('videos/generar_videos.py', '--manual', 'V1.1')
        self.assertIn('inglés', manual)
        self.assertNotIn('español ════', manual)

    def test_subtitulos_en_espanol_del_video_ingles(self):
        sub = self.aula / 'videos/subtitulos'; sub.mkdir(parents=True)
        palabras = [[0.0, 0.4, ' Every'], [0.4, 0.8, ' project'], [0.8, 1.3, ' starts.'],
                    [3.0, 3.4, ' Define'], [3.4, 3.8, ' the'], [3.8, 4.4, ' problem.']]
        (self.aula / 'p.json').write_text(json.dumps(palabras))
        self.run_py('hub/tools/subtitulos.py', 'frases', 'V1.1', 'p.json')
        frases = json.loads((sub / 'V1.1.json').read_text())
        self.assertEqual(len(frases), 2)
        self.assertAlmostEqual(frases[0][0], 3.0)          # incluye la portada UTI de 3 s
        self.assertEqual(self.run_py('hub/tools/subtitulos.py', 'ver', 'V1.1').split('\n')[0], '1|Every project starts.')
        (sub / 'V1.1.es.txt').write_text('1|Todo proyecto empieza.\n2|Define el problema.\n')
        unidad = self.aula / 'videos/unidad-1'; unidad.mkdir(parents=True, exist_ok=True)
        (unidad / 'V1.1.en.mp4').write_bytes(b'mp4 ficticio')
        self.run_py('hub/tools/subtitulos.py', 'vtt', 'V1.1')
        vtt = (unidad / 'V1.1.en.es.vtt').read_text()
        self.assertTrue(vtt.startswith('WEBVTT'))
        self.assertIn('00:00:03.000 --> ', vtt)
        self.assertIn('Todo proyecto empieza.', vtt)
        self.assertTrue((unidad / 'V1.1.en.en.vtt').exists() and (unidad / 'V1.1.en.subs.js').exists())
        self.run_py('hub/tools/videos.py')
        reg = (self.aula / 'videos/videos.js').read_text()
        datos = json.loads(reg[reg.index('{', reg.index('*/')): reg.rindex('}') + 1])
        self.assertEqual(datos['V1.1']['en']['subtitulos']['es'], 'unidad-1/V1.1.en.es.vtt')
        self.assertNotIn('es', datos['V1.1'])
        lista = self.run_py('videos/generar_videos.py', '--lista') if (self.aula / 'videos/guiones/V1.1.md').exists() else ''
        if lista:
            self.assertIn('es: subtítulos listos', lista)

    def test_canvas_usa_el_video_con_subtitulos_grabados(self):
        u = self.aula / 'videos/unidad-1'; u.mkdir(parents=True, exist_ok=True)
        (u / 'V1.1.en.mp4').write_bytes(b'mp4 ficticio'); (u / 'V1.1.en.sub-es.mp4').write_bytes(b'mp4 con subtitulos')
        self.run_py('canvas/generar_canvas.py', '--borrador')
        mat = (self.aula / 'canvas/salida/pegar/materiales-del-curso.html').read_text(encoding='utf-8')
        self.assertIn('V1.1.en.sub-es.mp4', mat)
        self.assertNotIn('V1.1.en.mp4', mat)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'requiere ffmpeg')
    def test_quemar_subtitulos(self):
        u = self.aula / 'videos/unidad-1'; u.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=white:s=320x180:d=2', '-f', 'lavfi',
                        '-i', 'anullsrc=r=44100:cl=mono', '-t', '2', '-c:v', 'libx264', '-c:a', 'aac', str(u / 'V1.1.en.mp4')], check=True)
        (u / 'V1.1.en.es.vtt').write_text('WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000\nHola\n', encoding='utf-8')
        self.run_py('hub/tools/subtitulos.py', 'quemar', 'V1.1')
        out = u / 'V1.1.en.sub-es.mp4'
        self.assertTrue(out.exists() and out.stat().st_size > 1000)
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(out)], capture_output=True, text=True)
        self.assertEqual(sorted(r.stdout.split()), ['audio', 'video'])

    def test_traduccion_incompleta_rechazada(self):
        sub = self.aula / 'videos/subtitulos'; sub.mkdir(parents=True)
        (sub / 'V1.1.json').write_text(json.dumps([[3, 4, 'One.'], [5, 6, 'Two.']]))
        (sub / 'V1.1.es.txt').write_text('1|Uno.\n')
        (self.aula / 'videos/unidad-1').mkdir(parents=True, exist_ok=True)
        self.run_py('hub/tools/subtitulos.py', 'vtt', 'V1.1', code=1)

    def test_transcribir_sin_video_avisa(self):
        r = subprocess.run([sys.executable, 'hub/tools/subtitulos.py', 'transcribir', 'V9.1'], cwd=self.aula, capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('V9.1.en.mp4', r.stderr)


if __name__ == '__main__':
    unittest.main()
