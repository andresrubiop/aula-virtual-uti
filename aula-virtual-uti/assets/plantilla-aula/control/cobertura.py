#!/usr/bin/env python3
"""Matriz local del sílabo. Relaciones explícitas y revisión vigente, no certificación pedagógica.

python3 control/cobertura.py iniciar
python3 control/cobertura.py verificar [--json]
En aulas anteriores: python3 <skill>/assets/plantilla-aula/control/cobertura.py --aula <aula> verificar
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import quote

from estado import analizar, clave_ruta, digest, escribir, leer, ruta, sin_duplicados

SILABO = 'canvas/silabo.json'
CURSO = 'hub/src/course.json'
MAPA = 'control/cobertura.json'
INFORME = 'control/COBERTURA.md'
PENDIENTE = re.compile(r'\[\s*COMPLETAR\b', re.I)


def objeto(value, label):
    if not isinstance(value, dict):
        raise ValueError(label+': se esperaba un objeto.')
    return value


def lista(value, label):
    if not isinstance(value, list):
        raise ValueError(label+': se esperaba una lista.')
    return value


def cadena(value, label):
    if not isinstance(value, str) or any(ord(c) < 32 and c not in '\n\r\t' for c in value):
        raise ValueError(label+': se esperaba texto válido.')
    return value.strip()


def numero(value, label):
    if type(value) is not int or value < 1:
        raise ValueError(label+': se esperaba entero positivo.')
    return value


def textos(value, label):
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [cadena(x, label) for x in lista(value, label)]


def numeros(value, label):
    values = [value] if type(value) is int else lista(value, label)
    result = [numero(n, label) for n in values]
    if len(set(result)) != len(result):
        raise ValueError(label+': unidades repetidas.')
    return result


def cargar(root, rel):
    return json.loads(ruta(root, rel).read_text(encoding='utf-8'), object_pairs_hook=sin_duplicados)


def catalogo(data, course):
    """Deriva todos los requisitos, incluso los que no tienen un vínculo en el mapa."""
    objeto(data, SILABO); objeto(course, CURSO)
    rows, issues, units, ras, sessions = [], [], {}, {}, {}
    unit_ids = set()
    for unit in lista(course.get('units', []), 'units'):
        objeto(unit, 'unidad'); n = numero(unit.get('n'), 'unidad.n')
        ident = cadena(unit.get('id'), 'unidad.id')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', ident):
            raise ValueError('unidad.id debe ser un nombre de carpeta simple.')
        if n in units or ident.casefold() in unit_ids:
            raise ValueError('Número o carpeta de unidad duplicado.')
        unit_ids.add(ident.casefold()); units[n] = unit
        if 'moment' in unit: numero(unit['moment'], 'unidad.moment')
        numeros(unit.get('sessions', []), 'unidad.sessions')
    if not units: issues.append('No hay unidades en course.json.')

    def add(ident, kind, label, ra=(), us=(), missing=()):
        row = {'id': ident, 'tipo': kind, 'descripcion': label, 'ra': list(ra),
               'unidades': sorted(set(us)), 'pendientes': list(missing)}
        if not label.strip() or PENDIENTE.search(label):
            row['pendientes'].append('Texto ausente o pendiente de completar en el sílabo.')
        for r in ra:
            if r not in ras: row['pendientes'].append('RA inexistente: '+r)
        for n in us:
            if n not in units: row['pendientes'].append('Unidad inexistente: '+str(n))
        rows.append(row); return row

    for raw in lista(data.get('ra', []), 'ra'):
        if not isinstance(raw, list) or len(raw) != 3:
            raise ValueError('Cada RA debe tener ID, texto y evidencia.')
        ident, label, evidence = [cadena(x, 'ra') for x in raw]
        if not ident or ident in ras: raise ValueError('RA vacío o duplicado.')
        ras[ident] = (label, evidence)
    if not ras: issues.append('El sílabo no tiene resultados de aprendizaje.')
    for ident, (label, evidence) in ras.items():
        missing = [] if evidence and not PENDIENTE.search(evidence) else ['Falta evidencia de desempeño del RA.']
        add('RA/'+quote(ident, safe=''), 'resultado', label, [ident], missing=missing)

    def rubric(value):
        if not isinstance(value, list) or not value: return False
        return all(isinstance(r, list) and len(r) == 6 and all(isinstance(c, str) and c.strip() and not PENDIENTE.search(c) for c in r) for r in value)

    moments = lista(data.get('momentos', []), 'momentos'); seen = set(); used = set(); linked_ra = set()
    if not moments: issues.append('El sílabo no tiene momentos ni sesiones.')
    for moment in moments:
        objeto(moment, 'momento'); mn = numero(moment.get('n'), 'momento.n')
        if mn in seen: raise ValueError('Momento duplicado.')
        seen.add(mn); mr = textos(moment.get('ra', []), 'momento.ra')
        ms = lista(moment.get('sesiones', []), 'sesiones'); moment_units = set()
        if not ms: issues.append(f'M{mn}: sin sesiones.')
        for session in ms:
            objeto(session, 'sesión'); sn = numero(session.get('n'), 'sesión.n'); key = (mn, sn)
            if key in sessions: raise ValueError('Sesión duplicada dentro del momento.')
            a = objeto(session.get('aula', {}), 'sesión.aula')
            explicit = 'unidad' in a or 'repaso' in a
            us = numeros(a.get('unidad', []), 'aula.unidad') + numeros(a.get('repaso', []), 'aula.repaso')
            if not explicit:
                us = [n for n,u in units.items() if u.get('moment') == mn and sn in u.get('sessions', [])]
            us = sorted(set(us)); sr = textos(session.get('ra', mr), 'sesión.ra')
            linked_ra.update(sr); used.update(us); moment_units.update(us)
            missing = ([] if us else ['Sesión sin unidad ni repaso asociado.']) + ([] if sr else ['Sesión sin RA.'])
            row = add(f'M{mn}/S{sn}', 'sesion', cadena(session.get('tema', ''), 'tema'), sr, us, missing)
            sessions[key] = row
            contents = textos(session.get('contenidos', []), 'contenidos')
            if not contents: row['pendientes'].append('Sesión sin contenidos declarados.')
            for i, content in enumerate(contents, 1):
                add(f'M{mn}/S{sn}/C{i}', 'contenido', content, sr, us, missing)
        missing = [] if rubric(moment.get('rubrica')) else ['Falta rúbrica con indicador y cinco niveles completos.']
        if not mr: missing.append('Evaluación sin RA asociado.')
        add(f'EV/M{mn}', 'evaluacion', cadena(moment.get('evidencia', ''), 'evidencia'), mr, moment_units, missing)
    for row in rows:
        if row['tipo'] == 'resultado':
            ident = row['ra'][0]
            if ident not in linked_ra: row['pendientes'].append('RA sin sesión asociada.')
            row['unidades'] = sorted({n for s in sessions.values() if ident in s['ra'] for n in s['unidades']})
    for n in sorted(set(units)-used): issues.append(f'U{n}: ninguna sesión del sílabo utiliza esta unidad.')
    # Detectar asociaciones en course.json que apuntan a sesiones inexistentes.
    for n,u in units.items():
        for sn in u.get('sessions', []):
            if (u.get('moment'),sn) not in sessions:
                issues.append(f'U{n}: asociación a momento/sesión inexistente ({u.get("moment")}/{sn}).')
    practices = lista(data.get('practicas', []), 'practicas'); seen = set()
    for p in practices:
        objeto(p, 'práctica'); ident = cadena(p.get('id'), 'práctica.id')
        if not ident or ident in seen: raise ValueError('ID de práctica vacío o duplicado.')
        seen.add(ident)
        key = (numero(p.get('momento'), 'práctica.momento'), numero(p.get('sesion'), 'práctica.sesion'))
        us = numeros(p.get('unidad', []), 'práctica.unidad'); pr = textos(p.get('ra', []), 'práctica.ra')
        missing = []
        if key not in sessions: missing.append('Práctica con sesión inexistente.')
        elif not set(us).issubset(sessions[key]['unidades']): missing.append('Unidad de práctica no vinculada a su sesión.')
        if key in sessions and not set(pr).issubset(sessions[key]['ra']):
            missing.append('RA de práctica no asociado a su sesión.')
        if not us: missing.append('Práctica sin unidad.')
        if not pr: missing.append('Práctica sin RA.')
        for name in ('proposito','entregable','evaluacion'):
            vals = textos(p.get(name, []), 'práctica.'+name)
            if not vals or any(not x.strip() or PENDIENTE.search(x) for x in vals): missing.append('Falta '+name+' de la práctica.')
        row = add('PR/'+quote(ident,safe=''), 'practica', cadena(p.get('titulo',''), 'práctica.titulo'), pr, us, missing)
        if p.get('archivo'): row['guia_original'] = cadena(p['archivo'], 'práctica.archivo')
    missing = [] if rubric(data.get('rubrica_final')) else ['Falta rúbrica final con indicador y cinco niveles completos.']
    add('EV/FINAL', 'evaluacion', cadena(data.get('producto_final',''), 'producto_final'), list(ras), used, missing)
    return rows, units, issues


class Fragmentos(HTMLParser):
    """Ubica IDs y texto por idioma, sin ejecutar HTML o contenido de documentos."""
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self, section):
        super().__init__(convert_charrefs=True)
        self.section = section; self.stack = []; self.ids = Counter(); self.texts = {'es': [], 'en': []}
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); ident = a.get('id'); lang = a.get('lang')
        if ident: self.ids[ident] += 1
        parent = self.stack[-1] if self.stack else ('', '', not self.section, False)
        current = (tag, lang or parent[1], parent[2] or ident == self.section,
                   parent[3] or tag in ('script','style','template','noscript') or 'hidden' in a or a.get('aria-hidden') == 'true')
        if tag not in self.VOID: self.stack.append(current)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0] == tag:
                del self.stack[i:]; break
    def handle_data(self, data):
        if self.stack:
            _,lang,selected,hidden = self.stack[-1]
            if selected and not hidden and lang in self.texts and data.strip(): self.texts[lang].append(data.strip())


def leer_mapa(root):
    p = ruta(root, MAPA, existe=False)
    if not p.exists(): return [], False
    data = objeto(cargar(root, MAPA), MAPA)
    if set(data) != {'version','vinculos'} or type(data['version']) is not int or data['version'] != 1:
        raise ValueError('Formato de cobertura incompatible; conserva el mapa y revisa su versión.')
    links = lista(data['vinculos'], 'vinculos'); seen = set()
    for v in links:
        if not isinstance(v,dict) or set(v) != {'elemento','archivo','seccion','idioma','registro','nota'}:
            raise ValueError('Cada vínculo requiere elemento, archivo, seccion, idioma, registro y nota.')
        for k,val in v.items(): cadena(val, 'vínculo.'+k)
        if not v['elemento'] or v['idioma'] not in ('es','en'):
            raise ValueError('Elemento vacío o idioma distinto de es/en.')
        key = (v['elemento'], clave_ruta(v['archivo']), v['seccion'], v['idioma'])
        if key in seen: raise ValueError('Vínculo de cobertura duplicado.')
        seen.add(key)
    return links, True


def comprobar(root):
    data = cargar(root, SILABO); course = cargar(root, CURSO)
    rows, units, issues = catalogo(data,course)
    links, mapped = leer_mapa(root)
    _, evidence = leer(root)
    details, _ = analizar(root, evidence['registros']); current = {d['id']:d for d in details}
    by_id = {row['id']:row for row in rows}; source_hashes = {}
    for rel in (SILABO,CURSO,'ESTADO.md') + ((MAPA,) if mapped else ()):
        source_hashes[rel] = digest(ruta(root,rel))
    resources = []
    for n,u in sorted(units.items()):
        for name in ('30-presentacion.html','50-manual.html'):
            rel = f'hub/src/content/{u["id"]}/{name}'
            try: source_hashes[rel] = digest(ruta(root,rel)); exists = True
            except (ValueError,OSError): exists = False; issues.append(f'U{n}: falta recurso FSO permitido y no vacío: {rel}')
            resources.append({'unidad':n,'archivo':rel,'existe':exists})
    cache = {}
    for v in links:
        if v['elemento'] not in by_id:
            issues.append('Vínculo a elemento inexistente: '+v['elemento']); continue
        row = by_id[v['elemento']]; reasons = []
        try:
            p = ruta(root,v['archivo']); rel = p.relative_to(root).as_posix()
            if p.suffix.lower() != '.html' or not rel.startswith('hub/src/content/'):
                raise ValueError('La cobertura estudiantil debe apuntar a contenido HTML dentro de hub/src/content/.')
            allowed = [f'hub/src/content/{units[n]["id"]}/' for n in row['unidades'] if n in units]
            if row['tipo'] != 'evaluacion' or row['id'] != 'EV/FINAL':
                if not allowed or not any(rel.startswith(folder) for folder in allowed):
                    reasons.append('Recurso fuera de las unidades asociadas al elemento.')
            source_hashes[rel] = digest(p)
            key = (rel,v['seccion'])
            if key not in cache:
                raw = p.read_text(encoding='utf-8')
                # Se respeta la separación de la edición docente usada por el compilador.
                raw = re.sub(r'<!--docente-->.*?<!--/docente-->', '', raw, flags=re.S)
                parsed = Fragmentos(v['seccion']); parsed.feed(raw); parsed.close(); cache[key] = parsed
            parsed = cache[key]
            if v['seccion'] and parsed.ids[v['seccion']] != 1: reasons.append('Sección HTML ausente o ID duplicado.')
            text = ' '.join(parsed.texts[v['idioma']])
            if not text or PENDIENTE.search(text): reasons.append('No hay texto estudiantil del idioma indicado o contiene COMPLETAR.')
        except (ValueError,OSError) as ex:
            rel = v['archivo']; reasons.append('Recurso no comprobable: '+str(ex))
        record = evidence['registros'].get(v['registro'])
        if not record: reasons.append('Registro de revisión inexistente.')
        else:
            if not current[v['registro']]['vigente']: reasons.append('Evidencia de revisión obsoleta o pendiente.')
            if record['tipo'] != 'docente' and not record['aprobacion']: reasons.append('Falta declaración de revisión docente o evidencia de aprobación.')
            if clave_ruta(rel) not in {clave_ruta(x) for x in record['entregables']}: reasons.append('El recurso no está entre los entregables de la revisión.')
            required = [SILABO,CURSO,MAPA] + ([row['guia_original']] if 'guia_original' in row else [])
            if not {clave_ruta(x) for x in required}.issubset({clave_ruta(x) for x in record['fuentes']}):
                reasons.append('La revisión debe incluir sílabo, course.json, mapa de cobertura y guía original declarada como fuentes.')
        if not v['nota'].strip() or PENDIENTE.search(v['nota']): reasons.append('Falta nota concreta sobre la relación académica revisada.')
        row.setdefault('vinculos', []).append({**v,'vigente':not reasons,'pendientes':reasons})
    for row in rows:
        row.setdefault('vinculos', [])
        if 'guia_original' in row:
            try: source_hashes[row['guia_original']] = digest(ruta(root,row['guia_original']))
            except (ValueError,OSError): row['pendientes'].append('Guía original declarada ausente o no permitida.')
        langs = {v['idioma'] for v in row['vinculos'] if v['vigente']}
        missing = sorted({'es','en'}-langs)
        if missing: row['pendientes'].append('Sin vínculo con revisión vigente en: '+', '.join(missing))
        # Un vínculo incorrecto nunca queda oculto por otro válido.
        if any(not v['vigente'] for v in row['vinculos']): row['pendientes'].append('Hay vínculos que requieren corrección o nueva revisión.')
        row['estado'] = 'revision_declarada_vigente' if not row['pendientes'] else 'pendiente'
    completed = sum(r['estado']=='revision_declarada_vigente' for r in rows)
    warnings = ['Las huellas y declaraciones no certifican pertinencia, traducción ni autenticidad de la revisión docente.']
    if not mapped: issues.append('Falta control/cobertura.json: iniciar el mapa sin inventar relaciones.')
    return {'fecha':datetime.now(timezone.utc).isoformat(), 'fuentes_sha256':source_hashes, 'filas':rows,
            'recursos_unidad':resources,'hallazgos':issues,'avisos':warnings,
            'resumen':{'elementos':len(rows),'revision_declarada_vigente':completed,'pendientes':len(rows)-completed},
            'limite':'Matriz de relaciones y evidencia declarada. Un archivo existente no acredita cobertura académica; no aprueba fases ni importa en Canvas.'}


def informe(report):
    def md(v): return escape(str(v), quote=False).replace('|','&#124;').replace('\r',' ').replace('\n','<br>')
    lines = ['# Cobertura del sílabo', '', report['limite'], '', '**Fecha:** '+report['fecha'], '',
             '| Elemento | RA | Tema, práctica o evidencia | Unidades | Revisión declarada | Pendientes |', '|---|---|---|---|---|---|']
    for r in report['filas']:
        lines.append('| '+' | '.join(md(x) for x in (r['id'],', '.join(r['ra']),r['descripcion'],', '.join('U'+str(x) for x in r['unidades']),r['estado'],'; '.join(r['pendientes'])))+' |')
    lines += ['', '## Recursos y revisiones por elemento', '']
    for row in report['filas']:
        lines += ['### '+md(row['id']), '']
        for v in row['vinculos']:
            lines.append('- '+md(f'{v["idioma"]}: {v["archivo"]}'+('#'+v['seccion'] if v['seccion'] else '')+f' · registro {v["registro"]} · {v["nota"]}'))
            if v['pendientes']: lines.append('  Pendiente: '+md('; '.join(v['pendientes'])))
        if not row['vinculos']: lines.append('Sin recursos vinculados.')
        lines.append('')
    lines += ['## Recursos FSO por unidad (existencia, no cobertura)', '']
    lines += ['- '+md(f'U{r["unidad"]}: {r["archivo"]} · '+('existe' if r['existe'] else 'pendiente')) for r in report['recursos_unidad']]
    lines += ['', '## Hallazgos y límites', '']+['- '+md(x) for x in report['hallazgos']+report['avisos']]
    lines += ['', '## Huellas de los archivos consultados', '']+['- '+md(k)+': `'+v+'`' for k,v in sorted(report['fuentes_sha256'].items())]
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--aula',type=Path,default=Path(__file__).resolve().parents[1])
    sub = ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('iniciar',help='Crear un mapa vacío, conservando cualquier mapa existente')
    check = sub.add_parser('verificar',help='Generar control/COBERTURA.md desde archivos actuales')
    check.add_argument('--json',action='store_true')
    args = ap.parse_args(argv); root = args.aula.expanduser().resolve()
    try:
        if args.cmd == 'iniciar':
            catalogo(cargar(root,SILABO),cargar(root,CURSO))
            p = ruta(root,MAPA,existe=False); p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('x',encoding='utf-8') as f: f.write(json.dumps({'version':1,'vinculos':[]},ensure_ascii=False,indent=2)+'\n')
            print('Mapa creado. Ejecuta verificar para ver todos los elementos pendientes; el asistente declara los vínculos tras revisar los recursos.')
            return 0
        report = comprobar(root); escribir(ruta(root,INFORME,existe=False),informe(report))
        print(json.dumps(report,ensure_ascii=False,indent=2) if args.json else informe(report))
        return 1 if report['hallazgos'] or report['resumen']['pendientes'] else 0
    except (ValueError,OSError) as ex:
        if args.cmd == 'verificar':
            try: escribir(ruta(root,INFORME,existe=False),'# Cobertura no comprobada\n\nNo uses el informe anterior como vigente. Corrige el formato o las rutas y vuelve a verificar.\n\n'+escape(str(ex))+'\n')
            except (ValueError,OSError): pass
        print('No se completó la cobertura: '+str(ex),file=sys.stderr); return 2


if __name__ == '__main__':
    sys.exit(main())
