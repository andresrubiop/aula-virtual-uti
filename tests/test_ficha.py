"""Ficha del sílabo con documento y texto extraído ficticios: no lee sílabos reales ni certifica transcripciones."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1] / 'aula-virtual-uti'
CONTROL = SKILL / 'assets/plantilla-aula/control'
DOC = 'fuentes/silabo/vigente.pdf'
CACHE = 'fuentes/_texto/silabo/vigente.pdf.txt'


class Ficha(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = json.loads((SKILL / 'references/silabo-ejemplo.json').read_text(encoding='utf-8'))
        self.write('ESTADO.md', (SKILL / 'assets/plantilla-aula/ESTADO.md').read_text(encoding='utf-8'))
        self.write('canvas/silabo.json', self.data)
        self.write(DOC, '%PDF-1.4 documento ficticio para la prueba')
        self.write('control/revision.txt', 'Revisión ficticia del escenario de prueba; no es una aprobación docente real.')
        self.paginas()

    # ── utilidades ──
    def write(self, name, value):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else value, encoding='utf-8')
        return p

    def paginas(self, extra=None):
        """Texto extraído ficticio, como el de pdftotext: datos generales en p. 1, mapa y RA en p. 2, momentos en p. 3."""
        d = self.data; m = d['momentos'][0]
        p1 = [d['curso']['nombre'], 'Período ' + d['curso']['periodo'], 'Inicio: 2026-11-16', 'Fin: 2026-11-22',
              f'Horas {d["curso"]["horas"]["docente"]} {d["curso"]["horas"]["practico"]} {d["curso"]["horas"]["autonomo"]}',
              d['docente']['nombre'], d['docente']['email'], d['docente']['grado']]
        p2 = [d['competencia_perfil'].upper(), d['competencia_pf'], d['metacompetencia'], *d['habilidades'],
              *[x for e in d['ejes'] for x in e], *[x for r in d['ra'] for x in r[1:]], d['contribucion'], d['problema'], d['reto'],
              d['producto_final'], d['pis'], d['aporte_pis'], *d['metodologias'], *d['rubrica_final'][0], d['bibliografia'][0][0]]
        def textos(v):
            return v if isinstance(v, list) else [v] if isinstance(v, str) else []
        p3 = [m['titulo'], m['fechas'], m['evidencia'], *textos(m.get('recursos')), *textos(m.get('ia')), *m['rubrica'][0]]
        for s in m['sesiones']:
            p3 += [s['desde'], s['hasta'], s['tema'], *[str(x) for x in s.get('horas', {}).values()]]
            for k in ('docente', 'practico', 'autonomo', 'contenidos'):
                p3 += textos(s.get(k))
        for g in d.get('practicas', []):
            p3 += [g['titulo'], *[str(g[k]) for k in ('puntos',) if k in g]]
            for k in ('proposito', 'entregable', 'evaluacion'):
                p3 += textos(g.get(k))
        pages = ['\n'.join(p1), '\n'.join(p2), '\n'.join(p3)] + (extra or [])
        cache = self.write(CACHE, '\f'.join(pages) + '\f')
        later = (self.root / DOC).stat().st_mtime_ns + 1_000_000_000
        os.utime(cache, ns=(later, later))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(CONTROL / 'ficha_silabo.py'), '--aula', str(self.root), *args],
                              capture_output=True, text=True, encoding='utf-8')

    def state(self, *args):
        return subprocess.run([sys.executable, str(CONTROL / 'estado.py'), '--aula', str(self.root), *args],
                              capture_output=True, text=True, encoding='utf-8')

    def preparar(self):
        r = self.cli('iniciar', '--documento', DOC); self.assertEqual(r.returncode, 0, r.stderr)
        r = self.cli('completar'); self.assertEqual(r.returncode, 0, r.stderr)

    def report(self, code=1):
        r = self.cli('verificar', '--json'); self.assertEqual(r.returncode, code, r.stderr + r.stdout[-800:])
        return json.loads(r.stdout)

    def fila(self, rep, campo):
        return next(f for f in rep['filas'] if f['campo'] == campo)

    def revisar(self, tipo='docente', aprobacion=False):
        args = ['registrar', 'ficha', '--fase', '2', '--tipo', tipo, '--entregable', 'canvas/silabo.json', '--fuente', DOC,
                '--fuente', 'control/ficha_silabo.json', '--prueba', 'control/revision.txt', '--resultado', 'pasado', '--reemplazar']
        if aprobacion:
            self.write('control/aprobacion.md', 'Aprobación ficticia del escenario.'); args += ['--aprobacion', 'control/aprobacion.md']
        r = self.state(*args); self.assertEqual(r.returncode, 0, r.stderr)

    # ── casos ──
    def test_ubica_cada_dato_en_su_pagina_y_espera_la_revision_docente(self):
        self.preparar()
        rep = self.report()
        self.assertEqual(self.fila(rep, '/ra/0/1')['pagina'], 2)
        self.assertEqual(self.fila(rep, '/momentos/0/titulo')['pagina'], 3)
        self.assertEqual(self.fila(rep, '/curso/inicio')['estado'], 'exacta')          # dd/mm/aaaa frente a aaaa-mm-dd
        self.assertEqual(self.fila(rep, '/competencia_perfil')['estado'], 'exacta')    # mayúsculas del PDF
        self.assertEqual(self.fila(rep, '/curso/horas/docente')['estado'], 'cotejo_visual')  # dato breve
        self.assertTrue(any('revisión docente' in h for h in rep['hallazgos']))
        self.assertFalse(any(f['estado'] in ('sin_referencia', 'no_localizado') for f in rep['filas']))
        excluidos = {'/curso/canvas_id', '/curso/bienvenida', '/_fuente/tipo', '/bibliografia/0/1'}
        self.assertFalse(excluidos & {f['campo'] for f in rep['filas']})
        md = (self.root / 'control/FICHA_SILABO.md').read_text(encoding='utf-8')
        self.assertIn('Ficha de extracción del sílabo', md); self.assertIn('no certifica', md)
        self.assertTrue((self.root / 'control/FICHA_SILABO.html').read_text(encoding='utf-8').startswith('<!doctype html>'))

    def test_revision_docente_vigente_cierra_la_ficha(self):
        self.preparar(); self.revisar()
        rep = self.report(0)
        self.assertEqual(rep['resumen']['pendientes'], 0)
        self.assertTrue(rep['revisiones'][0]['vigente'])

    def test_prueba_local_sin_aprobacion_no_cuenta_como_revision(self):
        self.preparar(); self.revisar('local')
        rep = self.report()
        self.assertFalse(rep['revisiones'][0]['vigente'])
        self.revisar('local', aprobacion=True)
        self.report(0)

    def test_cambio_del_dato_invalida_pagina_y_revision(self):
        self.preparar(); self.revisar()
        self.data['ra'][0][1] = 'Resultado reescrito sin cotejar con el documento.'; self.write('canvas/silabo.json', self.data)
        rep = self.report()
        self.assertEqual(self.fila(rep, '/ra/0/1')['estado'], 'valor_cambiado')
        self.assertFalse(rep['revisiones'][0]['vigente'])

    def test_documento_modificado_detiene_y_no_propone_paginas(self):
        self.preparar()
        self.write(DOC, '%PDF-1.4 otra versión ficticia'); self.paginas()
        rep = self.report()
        self.assertTrue(all(f['estado'] in ('documento_cambiado', 'completar') for f in rep['filas']))
        self.assertEqual(self.cli('completar').returncode, 2)

    def test_dato_ausente_de_la_pagina_sugiere_otra_y_admite_cotejo_declarado(self):
        self.preparar()
        mapa = json.loads((self.root / 'control/ficha_silabo.json').read_text(encoding='utf-8'))
        ref = next(r for r in mapa['referencias'] if r['campo'] == '/reto')
        ref['pagina'] = 3
        self.write('control/ficha_silabo.json', mapa)
        rep = self.report()
        f = self.fila(rep, '/reto')
        self.assertEqual(f['estado'], 'no_localizado'); self.assertEqual(f['sugerencia']['pagina'], 2)
        ref.update(pagina=2, nota='', origen='asistente'); self.write('control/ficha_silabo.json', mapa)
        self.data['reto'] += ' Texto añadido que el documento no contiene'; self.write('canvas/silabo.json', self.data)
        ref['valor_sha256'] = __import__('hashlib').sha256(self.data['reto'].encode()).hexdigest()
        self.write('control/ficha_silabo.json', mapa)
        self.assertIn(self.fila(self.report(), '/reto')['estado'], ('parcial', 'no_localizado'))
        ref['nota'] = 'Cotejado a la vista: la frase final continúa en la página siguiente.'; self.write('control/ficha_silabo.json', mapa)
        self.assertEqual(self.fila(self.report(), '/reto')['estado'], 'declarado')

    def test_completar_marca_pendiente_y_no_lo_ubica(self):
        self.data['pis'] = '[COMPLETAR: confirmar si el período tiene PIS]'; self.write('canvas/silabo.json', self.data)
        self.preparar()
        rep = self.report()
        self.assertEqual(self.fila(rep, '/pis')['estado'], 'completar')
        self.assertNotIn('/pis', {r['campo'] for r in json.loads((self.root / 'control/ficha_silabo.json').read_text())['referencias']})

    def test_empate_elige_la_pagina_en_orden_de_lectura_y_anota_las_demas(self):
        self.paginas(extra=[self.data['ra'][0][1]])                 # el RA se repite en un anexo final (p. 4)
        self.preparar()
        rep = self.report()
        f = self.fila(rep, '/ra/0/1')
        self.assertEqual(f['pagina'], 2); self.assertIn('4', f['nota'])

    def test_no_sobrescribe_rechaza_privado_y_cache_desactualizada(self):
        self.preparar()
        before = (self.root / 'control/ficha_silabo.json').read_bytes()
        self.assertEqual(self.cli('iniciar', '--documento', DOC).returncode, 2)
        self.assertEqual((self.root / 'control/ficha_silabo.json').read_bytes(), before)
        (self.root / 'control/ficha_silabo.json').unlink()
        self.write('fuentes/privado/notas.pdf', 'privado')
        self.assertEqual(self.cli('iniciar', '--documento', 'fuentes/privado/notas.pdf').returncode, 2)
        self.assertEqual(self.cli('iniciar', '--documento', 'canvas/silabo.json').returncode, 2)
        old = (self.root / DOC).stat().st_mtime_ns - 5_000_000_000
        os.utime(self.root / CACHE, ns=(old, old))
        r = self.cli('iniciar', '--documento', DOC)
        self.assertEqual(r.returncode, 2); self.assertIn('fuentes.py', r.stderr)

    def test_informes_derivados_no_son_evidencia_y_html_escapa_datos(self):
        self.data['reto'] = '<script>alert(1)</script> reto ficticio'; self.write('canvas/silabo.json', self.data)
        self.preparar(); self.report()
        html = (self.root / 'control/FICHA_SILABO.html').read_text(encoding='utf-8')
        self.assertNotIn('<script>alert', html); self.assertIn('&lt;script&gt;', html)
        r = self.state('registrar', 'x', '--fase', '2', '--entregable', 'canvas/silabo.json', '--fuente', 'control/FICHA_SILABO.md',
                       '--prueba', 'control/revision.txt', '--resultado', 'pasado')
        self.assertEqual(r.returncode, 2)

    def test_sin_ficha_no_declara_nada_localizado(self):
        rep = self.report()
        self.assertEqual(rep['resumen']['localizados_o_declarados'], 0)
        self.assertTrue(any('Falta control/ficha_silabo.json' in h for h in rep['hallazgos']))

    def test_mapa_mal_formado_detiene_sin_informe_vigente(self):
        self.write('control/ficha_silabo.json', {'version': 1, 'documento': DOC, 'documentos': {}, 'referencias': []})
        r = self.cli('verificar'); self.assertEqual(r.returncode, 2)
        self.assertIn('no comprobada', (self.root / 'control/FICHA_SILABO.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
