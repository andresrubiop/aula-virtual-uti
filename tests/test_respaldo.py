"""Respaldos por hitos con aulas ficticias: versiones recuperables sin tocar los documentos originales."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'aula-virtual-uti'
PLANTILLA = SKILL / 'assets/plantilla-aula'
RESPALDO = PLANTILLA / 'control/respaldo.py'
ESTADO = PLANTILLA / 'control/estado.py'
PANEL = PLANTILLA / 'control/panel.py'


def huellas(root, sin=('respaldos/',)):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts
            and not p.relative_to(root).as_posix().startswith(sin)}


class Respaldo(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'aula'
        self.write('ESTADO.md', (PLANTILLA / 'ESTADO.md').read_text(encoding='utf-8'))
        self.write('PLANIFICACION.md', '# Planificación ficticia\n')
        self.write('hub/src/course.json', {'title': {'es': 'Curso Ficticio'}, 'units': []})
        self.write('hub/src/content/u1/10-resumen.html', '<article>Resumen U1 aprobado</article>')
        self.write('hub/src/content/u1/50-manual.html', '<article>Manual U1</article>')
        self.write('hub/src/content/u2/10-resumen.html', '<article>Resumen U2</article>')
        self.write('hub/dist/index.html', '<!doctype html><title>aula compilada</title>')
        self.write('canvas/silabo.json', {'curso': 'ficticio'})
        self.write('fuentes/silabo/vigente.pdf', '%PDF-1.4 sílabo ficticio')
        self.write('fuentes/INVENTARIO.md', '# Inventario ficticio\n')
        self.write('fuentes/_texto/silabo/vigente.pdf.txt', 'texto en caché')
        self.write('canvas/exportado/curso.imscc', 'exportación ficticia')
        self.write('fuentes/privado/notas.txt', 'calificaciones ficticias')
        self.write('materiales/privado/lista.txt', 'lista ficticia')
        self.write('.env', 'CLAVE=ficticia')
        self.write('control/credentials.json', '{"token": "ficticio"}')
        self.write('control/VERIFICACION_ESTADO.md', 'informe derivado')
        self.write('PANEL.html', '<!doctype html>panel derivado')
        self.write('videos/unidad-1/V1.1.mp4', 'video ficticio')
        externo = self.write('../externo.txt', 'fuera del aula')
        (self.root / 'hub/src/content/enlace.html').symlink_to(externo)

    def write(self, name, value):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value, encoding='utf-8')
        return p

    def run_tool(self, tool, *args, code=0):
        r = subprocess.run([sys.executable, tool, '--aula', self.root, *map(str, args)], capture_output=True, text=True)
        self.assertEqual(r.returncode, code, r.stdout + r.stderr)
        return r

    def respaldo(self, *args, code=0):
        r = self.run_tool(RESPALDO, *args, '--json', code=code)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def manifiesto(self, nombre):
        return json.loads((self.root / 'respaldos/hitos' / (nombre + '.json')).read_text(encoding='utf-8'))

    def test_crear_guarda_trabajo_y_solo_huellas_de_originales(self):
        r = self.respaldo('crear', '--tipo', 'antes', '--motivo', 'Antes de rehacer la unidad 2')
        m = self.manifiesto(r['respaldo'])
        archivos = set(m['archivos'])
        for rel in ('ESTADO.md', 'PLANIFICACION.md', 'hub/src/content/u1/10-resumen.html', 'canvas/silabo.json', 'fuentes/INVENTARIO.md'):
            self.assertIn(rel, archivos)
        for rel in ('fuentes/silabo/vigente.pdf', 'canvas/exportado/curso.imscc', 'fuentes/privado/notas.txt',
                    'materiales/privado/lista.txt', '.env', 'control/credentials.json', 'control/VERIFICACION_ESTADO.md',
                    'PANEL.html', 'hub/dist/index.html', 'videos/unidad-1/V1.1.mp4', 'hub/src/content/enlace.html',
                    'fuentes/_texto/silabo/vigente.pdf.txt'):
            self.assertNotIn(rel, archivos)
        self.assertIn('fuentes/silabo/vigente.pdf', m['originales'])
        self.assertIn('canvas/exportado/curso.imscc', m['originales'])
        self.assertNotIn('fuentes/privado/notas.txt', m['originales'])
        objetos = list((self.root / 'respaldos/objetos').glob('*/*.gz'))
        self.assertEqual(len(objetos), len({a['sha256'] for a in m['archivos'].values()}))
        contenido = b''.join(gzip.decompress(o.read_bytes()) for o in objetos)
        self.assertNotIn(b'calificaciones', contenido); self.assertNotIn(b'CLAVE=', contenido)
        if os.name == 'posix':
            self.assertEqual((self.root / 'respaldos').stat().st_mode & 0o777, 0o700)
            self.assertEqual((self.root / 'respaldos/hitos' / (r['respaldo'] + '.json')).stat().st_mode & 0o777, 0o600)

    def test_segundo_respaldo_no_duplica_copias(self):
        self.respaldo('crear', '--motivo', 'uno')
        antes = len(list((self.root / 'respaldos/objetos').glob('*/*.gz')))
        self.write('hub/src/content/u2/10-resumen.html', '<article>Resumen U2 cambiado</article>')
        self.respaldo('crear', '--motivo', 'dos')
        self.assertEqual(len(list((self.root / 'respaldos/objetos').glob('*/*.gz'))), antes + 1)
        self.assertEqual(len(self.respaldo('listar')['respaldos']), 2)

    def test_vista_previa_no_cambia_nada_y_aplicar_restaura(self):
        r = self.respaldo('crear', '--tipo', 'aprobado', '--unidad', 'U1', '--motivo', 'U1 aprobada (ficticio)')
        self.write('hub/src/content/u1/10-resumen.html', '<article>Resumen empeorado</article>')
        (self.root / 'hub/src/content/u1/50-manual.html').unlink()
        self.write('hub/src/content/u1/70-nuevo.html', '<article>Pieza nueva</article>')
        self.write('hub/dist/index.html', '<!doctype html><title>recompilada</title>')
        actual = huellas(self.root)
        plan = self.respaldo('restaurar', 'ultimo-aprobado', '--ruta', 'hub/src/content/u1')
        self.assertFalse(plan['aplicado'])
        self.assertEqual(sorted(plan['restaurar']), ['hub/src/content/u1/10-resumen.html', 'hub/src/content/u1/50-manual.html'])
        self.assertEqual(plan['retirar'], ['hub/src/content/u1/70-nuevo.html'])
        self.assertEqual(huellas(self.root), actual, 'la vista previa no modifica el aula')
        hecho = self.respaldo('restaurar', 'ultimo-aprobado', '--ruta', 'hub/src/content/u1', '--aplicar')
        self.assertTrue(hecho['aplicado'])
        self.assertEqual((self.root / 'hub/src/content/u1/10-resumen.html').read_text(encoding='utf-8'), '<article>Resumen U1 aprobado</article>')
        self.assertTrue((self.root / 'hub/src/content/u1/50-manual.html').exists())
        self.assertFalse((self.root / 'hub/src/content/u1/70-nuevo.html').exists())
        self.assertIn('recompilada', (self.root / 'hub/dist/index.html').read_text(encoding='utf-8'), 'sin copia: la salida generada no se toca')
        # El respaldo de seguridad permite deshacer la restauración.
        self.respaldo('restaurar', hecho['respaldo_de_seguridad'], '--aplicar')
        self.assertIn('empeorado', (self.root / 'hub/src/content/u1/10-resumen.html').read_text(encoding='utf-8'))
        self.assertTrue((self.root / 'hub/src/content/u1/70-nuevo.html').exists())
        self.assertFalse((self.root / 'hub/src/content/u1/50-manual.html').exists())

    def test_originales_y_estado_se_conservan(self):
        self.respaldo('crear', '--motivo', 'antes')
        self.write('fuentes/silabo/vigente.pdf', '%PDF-1.4 sílabo corregido por el docente')
        self.write('fuentes/lecturas/nueva.pdf', '%PDF-1.4 lectura nueva')
        self.write('canvas/exportado/curso.imscc', 'exportación nueva')
        self.edit_estado()
        estado = (self.root / 'ESTADO.md').read_text(encoding='utf-8')
        plan = self.respaldo('restaurar', 'ultimo', '--aplicar')
        self.assertEqual(plan['originales']['modificados'], ['canvas/exportado/curso.imscc', 'fuentes/silabo/vigente.pdf'])
        self.assertIn('fuentes/lecturas/nueva.pdf', plan['originales']['nuevos'])
        self.assertIn('corregido', (self.root / 'fuentes/silabo/vigente.pdf').read_text(encoding='utf-8'))
        self.assertTrue((self.root / 'fuentes/lecturas/nueva.pdf').exists())
        self.assertEqual((self.root / 'canvas/exportado/curso.imscc').read_text(encoding='utf-8'), 'exportación nueva')
        self.assertEqual((self.root / 'ESTADO.md').read_text(encoding='utf-8'), estado, 'ESTADO.md no se reemplaza por defecto')
        self.assertEqual(plan['estado_distinto'], ['ESTADO.md'])
        self.assertEqual((self.root / 'fuentes/privado/notas.txt').read_text(encoding='utf-8'), 'calificaciones ficticias')
        self.respaldo('restaurar', 'ultimo', '--ruta', 'fuentes/silabo', code=2)
        self.respaldo('restaurar', 'ultimo', '--ruta', 'canvas/exportado', code=2)

    def edit_estado(self):
        p = self.root / 'ESTADO.md'
        p.write_text(p.read_text(encoding='utf-8').replace('(ninguna todavía)', '- Decisión posterior al respaldo'), encoding='utf-8')

    def test_incluir_estado_solo_por_pedido(self):
        r = self.respaldo('crear', '--motivo', 'antes')
        self.edit_estado()
        self.respaldo('restaurar', r['respaldo'], '--incluir-estado', '--aplicar')
        self.assertNotIn('Decisión posterior', (self.root / 'ESTADO.md').read_text(encoding='utf-8'))
        seguridad = self.respaldo('listar')['respaldos'][0]
        self.assertEqual(seguridad['tipo'], 'seguridad')
        self.assertIn('Decisión posterior', self.leer_copia(seguridad['id'], 'ESTADO.md'))

    def leer_copia(self, nombre, rel):
        d = self.manifiesto(nombre)['archivos'][rel]['sha256']
        return gzip.decompress((self.root / 'respaldos/objetos' / d[:2] / (d + '.gz')).read_bytes()).decode('utf-8')

    def registrar(self, *extra, ident='u1-revision'):
        self.write('control/prueba-u1.txt', 'Compilación ficticia de la unidad 1.')
        self.write('control/aprobacion-u1.txt', 'Revisión docente ficticia de la unidad 1.')
        self.run_tool(ESTADO, 'registrar', ident, '--fase', '4', '--entregable', 'hub/src/content/u1/10-resumen.html',
                      '--entregable', 'hub/dist/index.html', '--fuente', 'hub/src/course.json', '--prueba', 'control/prueba-u1.txt',
                      '--aprobacion', 'control/aprobacion-u1.txt', '--resultado', 'pasado', '--tipo', 'docente', *extra)

    def vigente(self, ident):
        r = subprocess.run([sys.executable, ESTADO, '--aula', self.root, 'verificar', '--json'], capture_output=True, text=True)
        return next(x['vigente'] for x in json.loads(r.stdout)['registros'] if x['id'] == ident)

    def test_volver_al_ultimo_resultado_revisado(self):
        self.registrar()
        r = self.respaldo('crear', '--tipo', 'aprobado', '--unidad', 'U1', '--motivo', 'U1 aprobada')
        self.assertEqual(r['avisos'], [])
        self.assertIn('hub/dist/index.html', self.manifiesto(r['respaldo'])['archivos'], 'una salida citada como evidencia se respalda')
        self.write('hub/src/content/u1/10-resumen.html', '<article>Cambio no revisado</article>')
        self.write('hub/dist/index.html', '<!doctype html><title>otra compilación</title>')
        self.assertFalse(self.vigente('u1-revision'))
        plan = self.respaldo('restaurar', '--evidencia', 'u1-revision', '--aplicar')
        self.assertEqual(sorted(plan['restaurar']), ['hub/dist/index.html', 'hub/src/content/u1/10-resumen.html'])
        self.assertTrue(self.vigente('u1-revision'))
        self.assertTrue(plan['respaldo_de_seguridad'])

    def test_evidencia_sin_copia_no_aplica_nada(self):
        self.registrar()
        self.write('hub/src/content/u1/10-resumen.html', '<article>Cambio no revisado</article>')
        actual = huellas(self.root)
        plan = self.respaldo('restaurar', '--evidencia', 'u1-revision', '--aplicar', code=1)
        self.assertFalse(plan['aplicado'])
        self.assertIn('hub/src/content/u1/10-resumen.html', plan['sin_copia'])
        self.assertEqual(huellas(self.root), actual)

    def test_aprobado_sin_evidencia_avisa(self):
        r = self.respaldo('crear', '--tipo', 'aprobado', '--motivo', 'Sin registro')
        self.assertTrue(any('sin comprobación de la aprobación' in a for a in r['avisos']))

    def test_copia_dañada_se_detecta_y_no_restaura_a_medias(self):
        r = self.respaldo('crear', '--motivo', 'antes')
        m = self.manifiesto(r['respaldo'])
        self.write('hub/src/content/u1/10-resumen.html', '<article>cambio A</article>')
        self.write('hub/src/content/u2/10-resumen.html', '<article>cambio B</article>')
        d = m['archivos']['hub/src/content/u2/10-resumen.html']['sha256']
        (self.root / 'respaldos/objetos' / d[:2] / (d + '.gz')).write_bytes(gzip.compress(b'alterado'))
        self.assertEqual(self.respaldo('comprobar', code=1)['resultado'], 'con_problemas')
        actual = huellas(self.root)
        self.respaldo('restaurar', r['respaldo'], '--aplicar', code=2)
        self.assertEqual(huellas(self.root), actual, 'ningún archivo se restaura si una copia está dañada')

    def test_manifiesto_alterado_no_se_usa(self):
        r = self.respaldo('crear', '--motivo', 'antes')
        p = self.root / 'respaldos/hitos' / (r['respaldo'] + '.json')
        for ruta in ('../fuera.txt', 'fuentes/silabo/vigente.pdf', 'fuentes/privado/notas.txt'):
            m = self.manifiesto(r['respaldo'])
            m['archivos'][ruta] = next(iter(m['archivos'].values()))
            p.write_text(json.dumps(m), encoding='utf-8')
            self.respaldo('restaurar', r['respaldo'], '--aplicar', code=2)
            self.assertEqual((self.root / 'fuentes/silabo/vigente.pdf').read_text(encoding='utf-8'), '%PDF-1.4 sílabo ficticio')
            self.assertFalse((self.base / 'fuera.txt').exists())
        self.assertTrue(self.respaldo('listar')['respaldos'][0]['error'])

    def test_candados(self):
        self.respaldo('crear', '--motivo', 'uno')
        (self.root / 'respaldos/.respaldo.lock').touch()
        self.respaldo('crear', '--motivo', 'dos', code=2)
        (self.root / 'respaldos/.respaldo.lock').unlink()
        (self.root / '.estado.lock').touch()
        self.respaldo('crear', '--motivo', 'dos', code=2)

    def test_extraer_fuera_del_aula(self):
        r = self.respaldo('crear', '--motivo', 'para otro equipo')
        destino = self.base / 'reconstruida'
        out = self.respaldo('extraer', r['respaldo'], '--destino', destino)
        self.assertEqual(out['archivos'], len(self.manifiesto(r['respaldo'])['archivos']))
        self.assertTrue((destino / 'RESPALDO.json').exists())
        self.assertEqual((destino / 'hub/src/content/u1/10-resumen.html').read_text(encoding='utf-8'), '<article>Resumen U1 aprobado</article>')
        self.assertFalse((destino / 'fuentes/silabo/vigente.pdf').exists())
        self.respaldo('extraer', r['respaldo'], '--destino', self.root / 'copia', code=2)
        self.respaldo('extraer', r['respaldo'], '--destino', destino, code=2)

    def test_respaldos_no_son_evidencia_y_el_panel_los_resume(self):
        r = self.respaldo('crear', '--motivo', 'antes')
        nombre = 'respaldos/hitos/' + r['respaldo'] + '.json'
        e = self.run_tool(ESTADO, 'registrar', 'x', '--fase', '0', '--entregable', nombre, '--fuente', 'hub/src/course.json',
                          '--resultado', 'no_ejecutado', code=2)
        self.assertIn('respaldos', e.stderr)
        self.registrar()
        datos = json.loads(self.run_tool(PANEL, '--json').stdout)
        rs = datos['comprobaciones']['respaldos']
        self.assertEqual(rs['total'], 1)
        self.assertEqual(rs['aprobadas_sin_copia'], ['u1-revision'])
        self.assertIn('<h3>Respaldos</h3>', (self.root / 'PANEL.html').read_text(encoding='utf-8'))
        self.respaldo('crear', '--tipo', 'aprobado', '--unidad', 'U1', '--motivo', 'U1 aprobada')
        rs = json.loads(self.run_tool(PANEL, '--json').stdout)['comprobaciones']['respaldos']
        self.assertEqual(rs['aprobadas_sin_copia'], [])
        self.assertEqual(rs['ultimo_aprobado']['unidad'], 'U1')


if __name__ == '__main__':
    unittest.main()
