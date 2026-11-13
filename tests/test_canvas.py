import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
from fixture import aula_demo
BASE=aula_demo()
class Canvas(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula=Path(self.tmp.name)/'aula'
        shutil.copytree(BASE,self.aula,ignore=shutil.ignore_patterns('salida','shots'))
        self.data=json.loads((self.aula/'canvas/silabo.json').read_text())
    def generate(self):
        (self.aula/'canvas/silabo.json').write_text(json.dumps(self.data))
        return subprocess.run([sys.executable,'canvas/generar_canvas.py'],cwd=self.aula,capture_output=True,text=True)
    def test_same_named_guides_do_not_collide(self):
        for i in (1,2):
            p=self.aula/f'fuentes/guias-practicas/g{i}/guia.txt';p.parent.mkdir(parents=True);p.write_text(f'Guía {i}')
        g=self.data['practicas'][0];g['archivo']='fuentes/guias-practicas/g1/guia.txt'
        other=dict(g,id='PR2',archivo='fuentes/guias-practicas/g2/guia.txt')
        self.data['practicas'].append(other)
        r=self.generate();self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        import zipfile
        with zipfile.ZipFile(self.aula/'canvas/salida/CP-aula-canvas.imscc') as z:
            for i in (1,2):self.assertIn(f'web_resources/Aula y materiales/guias/PR{i}-guia.txt',z.namelist())
    def test_private_guide_rejected(self):
        p=self.aula/'fuentes/privado/secret.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text('private')
        self.data['practicas'][0]['archivo']='fuentes/privado/secret.txt'
        self.assertNotEqual(self.generate().returncode,0)
    def test_generated_export_rejected(self):
        self.assertEqual(self.generate().returncode,0)
        dest=self.aula/'canvas/exportado/previo.imscc';dest.parent.mkdir(exist_ok=True)
        shutil.copy2(self.aula/'canvas/salida/CP-aula-canvas.imscc',dest)
        r=self.generate();self.assertNotEqual(r.returncode,0)
        self.assertIn('ya contiene',r.stderr)
    def test_invalid_syllabus_blocks_generation(self):
        self.data['ra']=[]
        self.assertNotEqual(self.generate().returncode,0)
if __name__=='__main__':unittest.main()
