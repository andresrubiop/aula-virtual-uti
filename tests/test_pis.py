"""PIS obligatorio para el proyecto formativo articulador, compartible con los que aportan (aulas ficticias, Canvas ficticio)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from fixture import aula_demo
import fake_canvas

ROOT = Path(__file__).resolve().parents[1]
EJEMPLO = ROOT / 'aula-virtual-uti/references/pis-ejemplo.json'


class Pis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = self.copia('aula')

    def copia(self, nombre):
        a = Path(self.tmp.name) / nombre
        shutil.copytree(aula_demo(), a, ignore=shutil.ignore_patterns('salida', 'shots'))
        return a

    def py(self, aula, *args, code=0, **kw):
        r = subprocess.run([sys.executable, *map(str, args)], cwd=aula, capture_output=True, text=True, encoding='utf-8', **kw)
        if code is not None:
            self.assertEqual(r.returncode, code, r.stdout[-2000:] + r.stderr[-2000:])
        return r

    def rol(self, aula, valor):
        p = aula / 'canvas/silabo.json'
        d = json.loads(p.read_text(encoding='utf-8'))
        if valor is None:
            d.pop('pis_rol', None)
        else:
            d['pis_rol'] = valor
        p.write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')

    def articulador(self, aula):
        self.rol(aula, 'articulador')
        shutil.copy2(EJEMPLO, aula / 'canvas/pis.json')
        (aula / 'fuentes/pis').mkdir(parents=True, exist_ok=True)
        (aula / 'fuentes/pis/PIS-ejemplo.pdf').write_bytes(b'%PDF-1.4 ficticio')

    def modulo_pis(self, aula):
        import re
        with zipfile.ZipFile(next((aula / 'canvas/salida').glob('*-aula-canvas.imscc'))) as z:
            mm = z.read('course_settings/module_meta.xml').decode('utf-8')
        m = re.search(r'<module identifier="\w+">\s*<title>(PIS[^<]*)</title>\s*<workflow_state>(\w+)</workflow_state>(.*?)</module>', mm, re.S)
        return m[1], m[2], re.findall(r'<title>([^<]+)</title>', m[3])

    def test_rol_obligatorio_si_hay_pis(self):
        self.rol(self.aula, None)
        r = self.py(self.aula, 'canvas/validar_silabo.py', code=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('pis_rol', r.stdout + r.stderr)
        self.rol(self.aula, 'otro')
        self.assertNotEqual(self.py(self.aula, 'canvas/validar_silabo.py', code=None).returncode, 0)

    def test_articulador_sin_documento_no_genera(self):
        self.rol(self.aula, 'articulador')
        r = self.py(self.aula, 'canvas/generar_canvas.py', code=None)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('fuentes/pis/', r.stderr)
        self.assertIn('canvas/pis.json', r.stderr)

    def test_articulador_genera_vista_y_modulo(self):
        self.articulador(self.aula)
        v = json.loads(self.py(self.aula, 'control/pis.py', '--json').stdout)
        self.assertEqual((v['rol'], v['estado']), ('articulador', 'listo'))
        self.py(self.aula, 'hub/build.py')
        html = (self.aula / 'hub/dist/index.html').read_text(encoding='utf-8')
        self.assertIn('data-view="pis"', html); self.assertIn('data-nav="pis"', html)
        self.assertIn('Momentos del PIS', html); self.assertIn('PIS stages', html)
        self.py(self.aula, 'hub/tools/autonomo.py', '--sin-paquete')
        self.py(self.aula, 'canvas/generar_canvas.py')
        titulo, estado, items = self.modulo_pis(self.aula)
        self.assertEqual(titulo, 'PIS: Aula ficticia de repaso colaborativo')
        self.assertEqual(estado, 'unpublished')
        self.assertEqual(items[:2], ['PIS: proyecto y proyectos formativos', 'PIS: Momento 1. Diagnóstico'])
        self.assertIn('PIS: rúbrica y evidencia integradora', items)
        self.assertEqual(sum('Interdisciplinario' in x for x in items), 2)        # las tareas PIS de la plantilla, sin duplicar
        self.py(self.aula, 'canvas/verificar_paquete.py')
        # Con la aprobación del docente: módulo y páginas publicados; las tareas siguen sin publicar
        self.py(self.aula, 'canvas/generar_canvas.py', '--publicar-pis')
        titulo, estado, _ = self.modulo_pis(self.aula)
        self.assertEqual(estado, 'active')
        import re
        with zipfile.ZipFile(next((self.aula / 'canvas/salida').glob('*-aula-canvas.imscc'))) as z:
            mm = z.read('course_settings/module_meta.xml').decode('utf-8')
        bloque = re.search(r'<title>PIS[^<]*</title>.*?</module>', mm, re.S)[0]
        estados = dict((ti, est) for est, ti in re.findall(r'<item identifier="\w+">\s*<content_type>\w+</content_type>\s*<workflow_state>(\w+)</workflow_state>\s*<title>([^<]+)</title>', bloque))
        self.assertEqual(estados['PIS: proyecto y proyectos formativos'], 'active')
        self.assertTrue(all(v == 'unpublished' for k, v in estados.items() if 'Interdisciplinario' in k), estados)
        self.py(self.aula, 'canvas/verificar_paquete.py')

    def test_datos_incoherentes_se_rechazan(self):
        self.articulador(self.aula)
        d = json.loads((self.aula / 'canvas/pis.json').read_text(encoding='utf-8'))
        d['en']['momentos'][0]['actividades'].pop()                               # un idioma con menos piezas
        (self.aula / 'canvas/pis.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        v = json.loads(self.py(self.aula, 'control/pis.py', '--json', code=1).stdout)
        self.assertIn('actividades: 2 en español y 1 en inglés', ' '.join(v['errores']))
        d['es']['rubrica']['niveles'] = d['es']['rubrica']['niveles'][:4]           # rúbrica sin los cinco niveles
        (self.aula / 'canvas/pis.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        v = json.loads(self.py(self.aula, 'control/pis.py', '--json', code=1).stdout)
        self.assertIn('cinco niveles', ' '.join(v['errores']))
        r = self.py(self.aula, 'hub/build.py', code=None)
        self.assertIn('sin la vista PIS', r.stderr)
        self.assertNotIn('data-view="pis"', (self.aula / 'hub/dist/index.html').read_text(encoding='utf-8'))

    def test_compartir_del_articulador_al_que_aporta(self):
        art = self.aula
        self.articulador(art)
        paquete = Path(self.py(art, 'control/pis.py', 'exportar', '--json').stdout and
                       json.loads(self.py(art, 'control/pis.py', 'exportar', '--json').stdout)['paquete'])
        paquete = art / paquete
        with zipfile.ZipFile(paquete) as z:
            self.assertEqual(sorted(z.namelist()), ['LEEME.txt', 'pis.json'])        # sin documentos salvo --con-documentos
        aporta = self.copia('aporta')
        v = json.loads(self.py(aporta, 'control/pis.py', '--json').stdout)
        self.assertEqual((v['rol'], v['estado']), ('aportante', 'pendiente'))
        self.py(aporta, 'control/pis.py', 'importar', paquete)
        v = json.loads(self.py(aporta, 'control/pis.py', '--json').stdout)
        self.assertEqual((v['estado'], v['origen']['rol']), ('listo', 'compartido'))
        self.py(aporta, 'hub/build.py')
        self.assertIn('Compartido por el proyecto formativo articulador', (aporta / 'hub/dist/index.html').read_text(encoding='utf-8'))
        r = self.py(art, 'control/pis.py', 'importar', paquete, code=None)            # el articulador no importa
        self.assertNotEqual(r.returncode, 0)

    def test_panel_muestra_el_rol(self):
        self.rol(self.aula, None)
        self.py(self.aula, 'control/panel.py')
        self.assertIn('Falta tu respuesta: ¿tu proyecto formativo es el articulador', (self.aula / 'PANEL.html').read_text(encoding='utf-8'))
        self.articulador(self.aula)
        self.py(self.aula, 'control/panel.py')
        self.assertIn('es el <strong>articulador</strong>', (self.aula / 'PANEL.html').read_text(encoding='utf-8'))


class PisEnCanvas(unittest.TestCase):
    """canvas_api --modulo PIS: solo el módulo del PIS, sin tocar el resto del curso."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.aula = Path(self.tmp.name) / 'aula'
        shutil.copytree(aula_demo(), self.aula, ignore=shutil.ignore_patterns('salida', 'shots'))
        d = json.loads((self.aula / 'canvas/silabo.json').read_text(encoding='utf-8')); d['pis_rol'] = 'articulador'
        (self.aula / 'canvas/silabo.json').write_text(json.dumps(d, ensure_ascii=False), encoding='utf-8')
        shutil.copy2(EJEMPLO, self.aula / 'canvas/pis.json')
        (self.aula / 'fuentes/pis').mkdir(parents=True, exist_ok=True); (self.aula / 'fuentes/pis/PIS.pdf').write_bytes(b'%PDF')
        for s in ('hub/build.py', 'hub/tools/autonomo.py', 'canvas/generar_canvas.py'):
            subprocess.run([sys.executable, s, *(['--sin-paquete'] if 'autonomo' in s else [])], cwd=self.aula, capture_output=True, check=True)
        self.curso = fake_canvas.Curso(); self.curso.sembrar_desde_plantilla(self.aula / 'canvas/plantilla/plantilla-uti.imscc')
        self.srv, url = fake_canvas.iniciar(self.curso); self.addCleanup(self.srv.shutdown)
        self.env = {**os.environ, 'CANVAS_TOKEN': fake_canvas.TOKEN, 'HOME': self.tmp.name}
        subprocess.run([sys.executable, 'canvas/canvas_api.py', 'configurar', '--curso', url], cwd=self.aula, env=self.env, check=True, capture_output=True)

    def test_solo_el_modulo_pis(self):
        paginas_antes = {u: dict(p) for u, p in self.curso.pages.items()}
        modulos_antes = len(self.curso.modules)
        r = subprocess.run([sys.executable, 'canvas/canvas_api.py', 'aplicar', '--modulo', 'PIS', '--permitir-pendientes'], cwd=self.aula,
                           env=self.env, capture_output=True, text=True, encoding='utf-8')
        self.assertIn('Aplicado', r.stdout, r.stdout[-2000:] + r.stderr[-2000:])
        plan = json.loads((self.aula / 'canvas/api/plan.json').read_text(encoding='utf-8'))
        self.assertEqual(plan['modulo'], 'PIS')
        self.assertEqual(len(plan['paginas_a_crear']), 4)
        self.assertEqual(plan['paginas_a_actualizar'], {})
        self.assertEqual(len(self.curso.modules), modulos_antes)                     # reutiliza el módulo «PIS» de la plantilla
        pis = next(m for m in self.curso.modules.values() if m['name'].startswith('PIS'))
        self.assertTrue(pis['name'].startswith('PIS: '))
        self.assertEqual(len(pis['items']), 6)
        for u, p in paginas_antes.items():                                           # el resto del curso no cambia
            self.assertEqual(self.curso.pages[u]['body'], p['body'], u)
        self.assertFalse([a['name'] for a in self.curso.assignments.values() if a['published']])
        nuevas = [p for u, p in self.curso.pages.items() if u not in paginas_antes]
        self.assertTrue(all(not p['published'] for p in nuevas))
        self.assertTrue(any('Rúbrica analítica del PIS' in p['body'] for p in nuevas))


if __name__ == '__main__':
    unittest.main()
