"""Regresiones reproducibles con documentos sintéticos; no requieren red ni cuentas."""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / 'aula-virtual-uti'
spec = importlib.util.spec_from_file_location('fuentes', SKILL / 'scripts/fuentes.py')
fuentes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fuentes)


class Scripts(unittest.TestCase):
    def test_preserva_destino_existente(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'README.md').write_text('contenido del docente')
            r = subprocess.run([sys.executable, str(SKILL / 'scripts/nuevo_aula.py'), d,
                                '--nombre', 'Prueba', '--sin-compilar'], capture_output=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertEqual((root / 'README.md').read_text(), 'contenido del docente')
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_fuentes_privadas_y_enlaces_no_se_leen(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / 'fuentes'
            (src / 'privado').mkdir(parents=True)
            (src / 'lecturas').mkdir()
            (src / 'privado/dato.txt').write_text('MARCADOR_PRIVADO_NO_PUBLICAR')
            (src / 'lecturas/publico.txt').write_text('Lectura válida')
            (src / 'lecturas/enlace.txt').symlink_to('../privado/dato.txt')
            r = subprocess.run([sys.executable, str(SKILL / 'scripts/fuentes.py'), d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn('MARCADOR_PRIVADO', r.stdout)
            self.assertEqual(len(list((src / '_texto').rglob('*.txt'))), 1)
            self.assertIn('Lectura válida', (src / '_texto/lecturas/publico.txt.txt').read_text())

    def test_cache_retira_fuentes_privadas_borradas_y_fallidas(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); src = root / 'fuentes'
            (src / 'lecturas').mkdir(parents=True); (src / 'privado').mkdir()
            for name in ('mover.txt', 'borrar.txt'):
                (src / 'lecturas' / name).write_text('Texto anterior reservado')
            doc = src / 'lecturas/roto.docx'
            with zipfile.ZipFile(doc, 'w') as z: z.writestr('word/document.xml','<w:p>Texto previo</w:p>')
            def run():
                r = subprocess.run([sys.executable, str(SKILL / 'scripts/fuentes.py'), d], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            run()
            (src / 'lecturas/mover.txt').rename(src / 'privado/mover.txt')
            (src / 'lecturas/borrar.txt').unlink(); doc.write_text('archivo roto')
            run()
            self.assertEqual(list((src / '_texto').rglob('*.txt')), [])
            self.assertNotIn('Texto anterior', (src / 'INVENTARIO.md').read_text())

    def test_pptx_orden_relaciones_y_notas(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'reordenado.pptx'
            with zipfile.ZipFile(f, 'w') as z:
                z.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="urn:p" xmlns:r="urn:r"><p:sldIdLst><p:sldId r:id="r2"/><p:sldId r:id="r1"/></p:sldIdLst></p:presentation>')
                z.writestr('ppt/_rels/presentation.xml.rels', '<Relationships><Relationship Id="r1" Type="o/slide" Target="slides/slide1.xml"/><Relationship Id="r2" Type="o/slide" Target="slides/slide2.xml"/></Relationships>')
                z.writestr('ppt/slides/slide1.xml','<a:p>Primera física</a:p>')
                z.writestr('ppt/slides/slide2.xml','<a:p>Segunda física</a:p>')
                z.writestr('ppt/slides/slide3.xml','<a:p>Huérfana no visible</a:p>')
                z.writestr('ppt/slides/_rels/slide2.xml.rels','<Relationships><Relationship Id="n" Type="o/notesSlide" Target="../notesSlides/notesSlide9.xml"/></Relationships>')
                z.writestr('ppt/notesSlides/notesSlide9.xml','<a:p>Nota de la segunda</a:p>')
            text, count = fuentes.pptx(f)
            self.assertLess(text.index('Segunda física'), text.index('Primera física'))
            self.assertLess(text.index('Nota de la segunda'), text.index('Diapositiva 2'))
            self.assertNotIn('Huérfana', text); self.assertEqual(count, '2 diapositivas')

    def test_xlsx_texto_numeros_y_formula_sin_cache(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'datos.xlsx'
            with zipfile.ZipFile(f, 'w') as z:
                z.writestr('xl/sharedStrings.xml', '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>Compartido</t></si></sst>')
                z.writestr('xl/worksheets/sheet1.xml', '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row><c r="A1" t="inlineStr"><is><t>Medición</t></is></c><c r="B1"><v>42</v></c><c r="C1" t="s"><v>0</v></c><c r="D1"><f>B1*2</f></c></row></sheetData></worksheet>')
            text, info = fuentes.xlsx(f)
            for item in ('A1: Medición', 'B1: 42', 'C1: Compartido', '=B1*2 [sin resultado guardado]'):
                self.assertIn(item, text)

    def test_docx_y_notas_pptx(self):
        with tempfile.TemporaryDirectory() as d:
            doc = Path(d) / 'guia.docx'
            ppt = Path(d) / 'clase.pptx'
            with zipfile.ZipFile(doc, 'w') as z:
                z.writestr('word/document.xml', '<w:p><w:t>Guía práctica</w:t></w:p>')
            with zipfile.ZipFile(ppt, 'w') as z:
                z.writestr('ppt/presentation.xml', '<p:presentation xmlns:p="urn:p" xmlns:r="urn:r"><p:sldIdLst><p:sldId r:id="r1"/></p:sldIdLst></p:presentation>')
                z.writestr('ppt/_rels/presentation.xml.rels', '<Relationships><Relationship Id="r1" Type="o/slide" Target="slides/slide1.xml"/></Relationships>')
                z.writestr('ppt/slides/_rels/slide1.xml.rels', '<Relationships><Relationship Id="n" Type="o/notesSlide" Target="../notesSlides/notesSlide1.xml"/></Relationships>')
                z.writestr('ppt/slides/slide1.xml', '<a:p><a:t>Diapositiva uno</a:t></a:p>')
                z.writestr('ppt/notesSlides/notesSlide1.xml', '<a:p><a:t>Nota docente</a:t></a:p>')
            self.assertIn('Guía práctica', fuentes.docx(doc)[0])
            self.assertIn('Nota docente', fuentes.pptx(ppt)[0])


if __name__ == '__main__':
    unittest.main()
