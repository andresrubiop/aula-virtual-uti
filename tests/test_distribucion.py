"""Mejora 12: versión identificable, guía de una sola fuente y actualización de aulas existentes."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'aula-virtual-uti'
ACTUALIZAR = SKILL / 'scripts' / 'actualizar_aula.py'


def version():
    return re.search(r'^\s*version:\s*"?([\w.\-]+)"?', (SKILL / 'SKILL.md').read_text(encoding='utf-8').split('\n---', 1)[0], re.M)[1]


class Distribucion(unittest.TestCase):
    def test_version_coherente(self):
        v = version()
        self.assertRegex(v, r'^\d+\.\d+\.\d+$')
        primera = re.search(r'^## (\S+)', (SKILL / 'CAMBIOS.md').read_text(encoding='utf-8'), re.M)[1]
        self.assertEqual(primera, v, 'la primera entrada de CAMBIOS.md debe ser la versión de SKILL.md')
        r = subprocess.run([sys.executable, str(SKILL / 'scripts/entorno.py')], capture_output=True, text=True, encoding='utf-8')
        self.assertIn(f'aula-virtual-uti {v}', r.stdout.splitlines()[0])
        val = json.loads((ROOT / 'dist/validacion.json').read_text(encoding='utf-8'))
        self.assertEqual(val.get('version'), v, 'dist/validacion.json debe declarar la versión publicada')

    def test_guia_de_una_sola_fuente(self):
        r = subprocess.run([sys.executable, str(ROOT / 'tools/guias.py'), 'comprobar'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stdout)
        sys.path.insert(0, str(ROOT / 'tools'))
        try:
            import guias
        finally:
            sys.path.remove(str(ROOT / 'tools'))
        raiz = guias.raiz_desde_fuente('# Guía\n\nVer [panel](references/panel.md), [web](https://x.org) y [arriba](#a).\n')
        self.assertIn('(aula-virtual-uti/references/panel.md)', raiz)
        self.assertIn('(https://x.org)', raiz); self.assertIn('(#a)', raiz)
        self.assertIn('GUIA_DE_USO.pdf', raiz.splitlines()[2])


class Actualizar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        r = subprocess.run([sys.executable, str(SKILL / 'scripts/nuevo_aula.py'), str(self.aula), '--nombre', 'Curso Ficticio', '--sin-compilar'],
                           capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)

    def run_tool(self, *args, code=0):
        r = subprocess.run([sys.executable, str(ACTUALIZAR), str(self.aula), *args, '--json'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return json.loads(r.stdout) if code == 0 else r

    def huellas(self):
        return {p.relative_to(self.aula).as_posix(): p.read_bytes() for p in self.aula.rglob('*') if p.is_file()}

    def test_aula_nueva_queda_al_dia_con_su_version(self):
        self.assertEqual((self.aula / 'control/VERSION_SKILL').read_text(encoding='utf-8').strip(), version())
        self.assertIn(f'`aula-virtual-uti` {version()}', (self.aula / 'ESTADO.md').read_text(encoding='utf-8'))
        d = self.run_tool()
        self.assertEqual(d['herramientas'], []); self.assertEqual(d['motor'], [])

    def test_aula_anterior_actualiza_herramientas_sin_tocar_contenido_ni_motor(self):
        panel = self.aula / 'control/panel.py'
        panel.write_text(panel.read_text(encoding='utf-8') + '\n# versión anterior\n', encoding='utf-8')
        (self.aula / 'hub/tools/accesibilidad.mjs').unlink()
        css = self.aula / 'hub/src/css/40-stage.css'
        css.write_text(css.read_text(encoding='utf-8') + '\n/* ajuste propio del aula */\n', encoding='utf-8')
        contenido = self.aula / 'hub/src/content/u1/50-manual.html'
        contenido.write_text(contenido.read_text(encoding='utf-8') + '<!-- edición del docente -->', encoding='utf-8')
        (self.aula / 'control/VERSION_SKILL').unlink()
        antes = self.huellas()
        d = self.run_tool()                                       # vista previa: nada cambia
        self.assertEqual(self.huellas(), antes)
        self.assertEqual(d['version_aula'], 'anterior a 0.12.0')
        self.assertEqual({x['archivo']: x['cambio'] for x in d['herramientas']},
                         {'control/panel.py': 'distinto', 'hub/tools/accesibilidad.mjs': 'nuevo'})
        self.assertEqual(d['motor'], [{'archivo': 'hub/src/css/40-stage.css', 'cambio': 'distinto'}])
        d = self.run_tool('--aplicar')
        self.assertTrue(d['aplicado'])
        self.assertNotIn('# versión anterior', panel.read_text(encoding='utf-8'))
        self.assertTrue((self.aula / 'hub/tools/accesibilidad.mjs').exists())
        self.assertIn('ajuste propio del aula', css.read_text(encoding='utf-8'))      # el motor no se toca sin pedirlo
        self.assertIn('edición del docente', contenido.read_text(encoding='utf-8'))
        copia = self.aula / d['copia_anterior'] / 'control/panel.py'
        self.assertIn('# versión anterior', copia.read_text(encoding='utf-8'))
        self.assertEqual((self.aula / 'control/VERSION_SKILL').read_text(encoding='utf-8').strip(), version())
        d = self.run_tool('--aplicar', '--incluir-motor')
        self.assertNotIn('ajuste propio del aula', css.read_text(encoding='utf-8'))
        self.assertIn('ajuste propio del aula', (self.aula / d['copia_anterior'] / 'hub/src/css/40-stage.css').read_text(encoding='utf-8'))

    def test_rechaza_lo_que_no_es_un_aula(self):
        otra = Path(self.tmp.name) / 'otra'; otra.mkdir()
        r = subprocess.run([sys.executable, str(ACTUALIZAR), str(otra)], capture_output=True, text=True, encoding='utf-8')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no parece un aula', r.stderr)


if __name__ == '__main__':
    unittest.main()
