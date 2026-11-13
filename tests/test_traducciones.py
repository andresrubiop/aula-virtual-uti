import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'aula-virtual-uti/assets/plantilla-aula/canvas/traducir_paquete.py'
from fixture import aula_demo
PKG = next((aula_demo()/'canvas/salida').glob('*.imscc'))
VERIFY = ROOT/'aula-virtual-uti/assets/plantilla-aula/canvas/verificar_paquete.py'

class Translations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pkg = self.root/'curso.imscc'
        self.pkg.write_bytes(PKG.read_bytes())
        self.tr = self.root/'translations.json'
    def run_cli(self, *args):
        return subprocess.run([sys.executable,str(SCRIPT),str(self.pkg),'--traducciones',str(self.tr),*args],text=True,capture_output=True)
    def inventory(self):
        self.assertEqual(self.run_cli('--inventario').returncode,0)
        return json.loads(self.tr.read_text())
    def fill(self):
        data=self.inventory()
        # Sintético: valida integración, no calidad de traducción.
        for group, entries in data.items():
            for value in entries.values():
                value['title']='English test title'
                if group != 'modules':value['html']='<p>English technical fixture</p>'+value['source_html']
        self.tr.write_text(json.dumps(data))
        return data
    def test_missing_translation_rejected(self):
        self.inventory()
        self.assertNotEqual(self.run_cli().returncode,0)
        self.assertFalse(self.pkg.with_name('curso-bilingue.imscc').exists())
    def test_integration_preserves_resources_and_es(self):
        self.fill()
        original=self.pkg.read_bytes()
        r=self.run_cli()
        self.assertEqual(r.returncode,0,r.stderr)
        output=self.pkg.with_name('curso-bilingue.imscc')
        with zipfile.ZipFile(output) as z, zipfile.ZipFile(self.pkg) as base:
            self.assertEqual(set(z.namelist()),set(base.namelist()))
            for name in z.namelist():
                if name.startswith('web_resources/'):
                    self.assertEqual(z.read(name),base.read(name))
            t=z.read('wiki_content/aula-interactiva.html').decode()
            self.assertIn('lang="es"',t)
            self.assertIn('lang="en"',t)
        self.assertEqual(original,self.pkg.read_bytes())
        r=subprocess.run([sys.executable,str(VERIFY),str(output)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout)
    def test_stale_hash_rejected_and_inventory_preserves_translation(self):
        data=self.fill()
        key=next(iter(data['pages']))
        data['pages'][key]['source_sha256']='old'
        self.tr.write_text(json.dumps(data))
        self.assertNotEqual(self.run_cli().returncode,0)
        newer=self.inventory()
        self.assertEqual(newer['pages'][key]['title'],'English test title')
        self.assertEqual(newer['pages'][key]['source_sha256'],'old')
        self.assertIn('current_source',newer['pages'][key])
    def test_reference_change_rejected(self):
        data=self.fill()
        key=next(iter(data['pages']))
        data['pages'][key]['html'] += '<a href="$WIKI_REFERENCE$/pages/wrong">Bad reference</a>'
        self.tr.write_text(json.dumps(data))
        self.assertNotEqual(self.run_cli().returncode,0)

if __name__=='__main__':unittest.main()
