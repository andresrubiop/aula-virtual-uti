#!/usr/bin/env python3
"""Ficha de extracción y revisión del sílabo: cada dato de canvas/silabo.json con su documento y página.

python3 control/ficha_silabo.py iniciar --documento fuentes/silabo/vigente.pdf
python3 control/ficha_silabo.py completar      # propone páginas solo donde el texto coincide sin ambigüedad
python3 control/ficha_silabo.py verificar [--json]
En aulas anteriores: python3 <skill>/assets/plantilla-aula/control/ficha_silabo.py --aula <aula> verificar

Lee el texto ya extraído por scripts/fuentes.py (fuentes/_texto/). Comprueba que cada valor aparezca en la página
declarada, que el documento y el valor no hayan cambiado y que no queden marcas COMPLETAR. Escribe
control/FICHA_SILABO.md y control/FICHA_SILABO.html para el cotejo del docente. Una coincidencia de palabras no
certifica la transcripción: la revisión docente se registra aparte con control/estado.py y nunca se infiere.
"""
import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import sys
import unicodedata

from estado import analizar, clave_ruta, digest, escribir, leer, ruta, sin_duplicados

SILABO = 'canvas/silabo.json'
MAPA = 'control/ficha_silabo.json'
INFORME = 'control/FICHA_SILABO.md'
VISTA = 'control/FICHA_SILABO.html'
TEXTO = 'fuentes/_texto'
PENDIENTE = re.compile(r'\[\s*COMPLETAR\b', re.I)
LIMITE = ('Ficha de cotejo. La coincidencia de palabras con la página indicada no certifica la transcripción: '
          'tablas, mayúsculas y columnas pueden mezclar el texto extraído. La revisión docente se declara aparte.')
# Datos que no se transcriben del sílabo: configuración del aula, privacidad, numeración e identificadores internos.
EXCLUIDOS = [r'/_[^/]*(/.*)?', r'/no_publicar(/.*)?', r'/curso/canvas_id', r'/curso/bienvenida',
             r'/momentos/\d+/n', r'/momentos/\d+/sesiones/\d+/n', r'/momentos/\d+/sesiones/\d+/aula(/.*)?',
             r'/momentos/\d+/ra/\d+', r'/ra/\d+/0', r'/practicas/\d+/(id|momento|sesion|unidad|archivo)(/.*)?',
             r'/practicas/\d+/ra/\d+', r'/bibliografia/\d+/[1-9]\d*']
ESTADOS = {
    'exacta': ('✔', 'Texto localizado en la página'),
    'palabras': ('✔', 'Palabras localizadas en la página (orden o columnas distintos)'),
    'declarado': ('◐', 'Cotejo visual declarado por el asistente'),
    'cotejo_visual': ('◐', 'Dato breve: cotejar a la vista en la página'),
    'parcial': ('▲', 'Coincidencia parcial: cotejar'),
    'no_localizado': ('✖', 'No aparece en la página indicada'),
    'sin_referencia': ('✖', 'Sin documento o página'),
    'valor_cambiado': ('▲', 'El dato cambió después de asignar la página'),
    'documento_cambiado': ('✖', 'El documento cambió después de crear la ficha'),
    'completar': ('✖', 'Pendiente: COMPLETAR'),
}
RESUELTOS = ('exacta', 'palabras', 'declarado')


def cargar(root, rel):
    return json.loads(ruta(root, rel).read_text(encoding='utf-8'), object_pairs_hook=sin_duplicados)


def puntero(parts):
    return '/' + '/'.join(str(p).replace('~', '~0').replace('/', '~1') for p in parts)


def hojas(value, parts=()):
    if isinstance(value, dict):
        for k, v in value.items():
            yield from hojas(v, parts + (k,))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from hojas(v, parts + (i,))
    elif value is not None and not isinstance(value, bool):
        yield puntero(parts), parts, value


def campos(data):
    """Datos transcritos del sílabo, en orden de lectura. Las cadenas vacías también se listan: faltan."""
    if not isinstance(data, dict):
        raise ValueError(SILABO + ': se esperaba un objeto.')
    out = []
    for ptr, parts, value in hojas(data):
        if any(re.fullmatch(x, ptr) for x in EXCLUIDOS):
            continue
        out.append({'campo': ptr, 'partes': list(parts), 'valor': value if isinstance(value, str) else str(value)})
    return out


def huella_valor(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


# ───────────── texto del documento ─────────────
def plano(text):
    text = unicodedata.normalize('NFKD', str(text))
    text = ''.join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def palabras(text):
    return [t for t in plano(text).split() if len(t) > 2 or t.isdigit()]


def variantes(value):
    """Fechas: el sílabo institucional usa dd/mm/aaaa en tablas y aaaa-mm-dd en la portada."""
    out = [value]
    for d, m, y in re.findall(r'\b(\d{2})/(\d{2})/(\d{4})\b', value):
        out.append(value.replace(f'{d}/{m}/{y}', f'{y}-{m}-{d}'))
    return out


def paginas(root, documento):
    """[(número, texto)] desde la caché de fuentes.py: PDF por salto de página, PPTX por diapositiva, resto entero."""
    src = ruta(root, documento)
    if not clave_ruta(documento).startswith('fuentes/') or clave_ruta(documento).startswith('fuentes/_texto/'):
        raise ValueError(f'{documento}: el documento debe ser un original dentro de fuentes/.')
    cache = ruta(root, f'{TEXTO}/{src.relative_to(root).relative_to("fuentes").as_posix()}.txt', existe=False)
    if not cache.is_file():
        raise ValueError(f'Falta el texto extraído de {documento}: ejecuta scripts/fuentes.py de la skill sobre el aula.')
    if cache.stat().st_mtime_ns < src.stat().st_mtime_ns:
        raise ValueError(f'El texto extraído de {documento} es anterior al documento: vuelve a ejecutar scripts/fuentes.py.')
    text = cache.read_text(encoding='utf-8')
    if src.suffix.lower() == '.pdf':
        parts = text.split('\f')
        if parts and not parts[-1].strip():
            parts = parts[:-1]
        return list(enumerate(parts, 1))
    if src.suffix.lower() in ('.pptx', '.ppt'):
        trozos = re.split(r'^=== Diapositiva (\d+) ===\s*$', text, flags=re.M)
        return [(int(trozos[i]), trozos[i + 1]) for i in range(1, len(trozos) - 1, 2)]
    return [(1, text)]


def comparar(value, text):
    """(estado, proporción de palabras encontradas). No interpreta el sentido del texto."""
    if not value.strip():
        return 'completar', 0.0
    norm = plano(text)
    if any(plano(v) and f' {plano(v)} ' in f' {norm} ' for v in variantes(value)):
        tokens = palabras(value)
        return ('exacta' if len(tokens) >= 2 or any(len(t) >= 4 for t in tokens) else 'cotejo_visual'), 1.0
    tokens = palabras(value)
    present = set(norm.split())
    if not tokens or (len(tokens) < 3 and all(len(t) < 4 for t in tokens)):
        # Dato breve (una cifra, un código): su presencia no lo identifica; lo confirma la revisión visual.
        brief = tokens or plano(value).split()
        return ('cotejo_visual', 1.0) if brief and all(t in present for t in brief) else ('no_localizado', 0.0)
    ratio = sum(t in present for t in tokens) / len(tokens)
    if ratio >= 0.9 and len(tokens) >= 3:
        return 'palabras', ratio
    return ('parcial' if ratio >= 0.6 else 'no_localizado'), ratio


ORDEN = {'exacta': 0, 'palabras': 1, 'cotejo_visual': 2, 'parcial': 3, 'no_localizado': 4, 'completar': 5}


def mejor_pagina(value, pages):
    return sorted(((comparar(value, t), n) for n, t in pages), key=lambda x: (ORDEN[x[0][0]], -x[0][1], x[1]))


def elegir(value, pages, cerca=0):
    """(estado, página, otras páginas igual de buenas). Ante un empate elige la página más cercana en el orden de
    lectura del sílabo (la primera desde la del dato anterior): los RA, por ejemplo, se repiten en los momentos."""
    ranking = mejor_pagina(value, pages)
    (est, prop), _ = ranking[0]
    iguales = [n for (e, pr), n in ranking if e == est and pr == prop]
    desde = [n for n in iguales if n >= cerca]
    n = desde[0] if desde else iguales[0]
    return est, n, [x for x in iguales if x != n]


# ───────────── mapa ─────────────
def leer_mapa(root):
    p = ruta(root, MAPA, existe=False)
    if not p.exists():
        return None
    data = cargar(root, MAPA)
    if not isinstance(data, dict) or set(data) != {'version', 'documento', 'documentos', 'referencias'} or data['version'] != 1:
        raise ValueError('Formato de ficha incompatible; conserva control/ficha_silabo.json y revisa su versión.')
    if not isinstance(data['documentos'], dict) or not all(isinstance(k, str) and isinstance(v, str) and re.fullmatch(r'[a-f0-9]{64}', v)
                                                            for k, v in data['documentos'].items()):
        raise ValueError('ficha_silabo.json: «documentos» debe asociar rutas a huellas SHA-256.')
    if data['documento'] not in data['documentos']:
        raise ValueError('ficha_silabo.json: el documento principal debe tener su huella en «documentos».')
    vistos = set()
    for r in data['referencias'] if isinstance(data['referencias'], list) else [None]:
        if not isinstance(r, dict) or set(r) != {'campo', 'archivo', 'pagina', 'valor_sha256', 'nota', 'origen'}:
            raise ValueError('Cada referencia requiere campo, archivo, pagina, valor_sha256, nota y origen.')
        if not isinstance(r['campo'], str) or not r['campo'].startswith('/') or r['campo'] in vistos:
            raise ValueError('Referencia con campo vacío, no válido o repetido: ' + str(r.get('campo')))
        if r['archivo'] not in data['documentos']:
            raise ValueError(f'{r["campo"]}: el archivo {r["archivo"]} no tiene huella en «documentos».')
        if r['pagina'] is not None and (type(r['pagina']) is not int or r['pagina'] < 1):
            raise ValueError(f'{r["campo"]}: la página debe ser un entero positivo o null.')
        if r['origen'] not in ('asistente', 'sugerida', 'docente') or not isinstance(r['nota'], str):
            raise ValueError(f'{r["campo"]}: origen debe ser asistente, sugerida o docente, y nota un texto.')
        if not isinstance(r['valor_sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', r['valor_sha256']):
            raise ValueError(f'{r["campo"]}: falta la huella del valor.')
        vistos.add(r['campo'])
    return data


def guardar_mapa(root, data):
    escribir(ruta(root, MAPA, existe=False), json.dumps(data, ensure_ascii=False, indent=2) + '\n')


# ───────────── revisión docente declarada ─────────────
def revisiones(root, documentos):
    """Registros de ESTADO.md que declaran la revisión docente de esta ficha y siguen vigentes."""
    _, evidence = leer(root)
    detalles, _ = analizar(root, evidence['registros'])
    vig = {d['id']: d for d in detalles}
    requeridas = {clave_ruta(SILABO)}
    fuentes = {clave_ruta(MAPA)} | {clave_ruta(d) for d in documentos}
    out = []
    for ident, item in evidence['registros'].items():
        if clave_ruta(SILABO) not in {clave_ruta(x) for x in item['entregables']}:
            continue
        if clave_ruta(MAPA) not in {clave_ruta(x) for x in item['fuentes']}:
            continue
        motivos = list(vig[ident]['problemas'])
        if item['tipo'] != 'docente' and not item['aprobacion']:
            motivos.append('No declara revisión docente ni evidencia de aprobación.')
        faltan = sorted(fuentes - {clave_ruta(x) for x in item['fuentes']})
        if faltan:
            motivos.append('Faltan como fuentes: ' + ', '.join(faltan))
        if not requeridas.issubset({clave_ruta(x) for x in item['entregables']}):
            motivos.append('No incluye canvas/silabo.json como entregable.')
        out.append({'registro': ident, 'vigente': not motivos, 'pendientes': motivos, 'fecha': item['fecha']})
    return out


# ───────────── comprobación ─────────────
def comprobar(root):
    data = cargar(root, SILABO)
    lista = campos(data)
    mapa = leer_mapa(root)
    hallazgos = []
    if mapa is None:
        hallazgos.append('Falta control/ficha_silabo.json: inicia la ficha con el sílabo vigente (iniciar --documento).')
        mapa = {'documento': '', 'documentos': {}, 'referencias': []}
    refs = {r['campo']: r for r in mapa['referencias']}
    docs, cambiados = {}, set()
    for rel, esperado in mapa['documentos'].items():
        try:
            actual = digest(ruta(root, rel))
        except (ValueError, OSError):
            actual = None
        if actual != esperado:
            cambiados.add(rel)
            hallazgos.append(f'{rel}: ' + ('ausente o no permitido' if actual is None else 'cambió después de crear la ficha') +
                             '. Revisa todas sus referencias y vuelve a iniciar o actualizar la huella con el asistente.')
            continue
        try:
            docs[rel] = paginas(root, rel)
        except (ValueError, OSError) as ex:
            hallazgos.append(str(ex))
    filas = []
    for c in lista:
        r = refs.get(c['campo'])
        fila = {**c, 'archivo': r['archivo'] if r else '', 'pagina': r['pagina'] if r else None,
                'nota': r['nota'] if r else '', 'origen': r['origen'] if r else '', 'proporcion': 0.0, 'sugerencia': None}
        if PENDIENTE.search(c['valor']) or not c['valor'].strip():
            fila['estado'] = 'completar'
        elif not r:
            fila['estado'] = 'sin_referencia'
        elif r['archivo'] in cambiados:
            fila['estado'] = 'documento_cambiado'
        elif r['valor_sha256'] != huella_valor(c['valor']):
            fila['estado'] = 'valor_cambiado'
        elif r['archivo'] not in docs:
            fila['estado'] = 'no_localizado'
        else:
            pages = dict(docs[r['archivo']])
            if r['pagina'] is None and len(pages) > 1:
                fila['estado'], fila['proporcion'] = 'sin_referencia', 0.0
            elif r['pagina'] is not None and r['pagina'] not in pages:
                fila['estado'] = 'no_localizado'
                fila['nota'] = (fila['nota'] + ' ' if fila['nota'] else '') + f'(el documento no tiene la página {r["pagina"]})'
            else:
                fila['estado'], fila['proporcion'] = comparar(c['valor'], pages[r['pagina'] or 1])
                if (fila['estado'] in ('parcial', 'no_localizado', 'cotejo_visual') and r['origen'] != 'sugerida'
                        and r['nota'].strip() and not PENDIENTE.search(r['nota'])):
                    fila['estado'] = 'declarado'
        if fila['estado'] in ('sin_referencia', 'no_localizado', 'parcial', 'valor_cambiado') and mapa['documento'] in docs:
            est, n, otras = elegir(c['valor'], docs[mapa['documento']], fila['pagina'] or 0)
            if est in ('exacta', 'palabras', 'cotejo_visual') and n != fila['pagina']:
                fila['sugerencia'] = {'archivo': mapa['documento'], 'pagina': n, 'estado': est, 'otras': otras}
        filas.append(fila)
    rev = revisiones(root, list(mapa['documentos'])) if mapa['documento'] else []
    revisada = any(x['vigente'] for x in rev)
    if not revisada:
        hallazgos.append('Falta la revisión docente vigente de la ficha (registro en ESTADO.md con canvas/silabo.json como entregable y el '
                         'documento y control/ficha_silabo.json como fuentes, de tipo docente o con aprobación).')
    cuenta = {k: sum(f['estado'] == k for f in filas) for k in ESTADOS}
    # Un dato breve presente en su página se da por cotejado solo con la revisión docente vigente.
    resueltos = sum(cuenta[k] for k in RESUELTOS) + (cuenta['cotejo_visual'] if revisada else 0)
    for f in filas:
        f['resuelto'] = f['estado'] in RESUELTOS or (f['estado'] == 'cotejo_visual' and revisada)
    return {'limite': LIMITE, 'documento': mapa['documento'], 'documentos': mapa['documentos'], 'filas': filas,
            'revisiones': rev, 'hallazgos': hallazgos,
            'resumen': {'campos': len(filas), 'localizados_o_declarados': resueltos, 'pendientes': len(filas) - resueltos, 'por_estado': cuenta}}


# ───────────── informes ─────────────
SECCIONES = [
    ('curso', 'Datos del proyecto formativo'), ('docente', 'Docente'), ('competencia_perfil', 'Mapa de formación'),
    ('competencia_pf', 'Mapa de formación'), ('metacompetencia', 'Mapa de formación'), ('habilidades', 'Mapa de formación'),
    ('ejes', 'Mapa de formación'), ('ra', 'Resultados de aprendizaje'), ('contribucion', 'Problema, reto y PIS'),
    ('problema', 'Problema, reto y PIS'), ('reto', 'Problema, reto y PIS'), ('producto_final', 'Problema, reto y PIS'),
    ('pis', 'Problema, reto y PIS'), ('aporte_pis', 'Problema, reto y PIS'), ('metodologias', 'Metodología'),
    ('momentos', 'Momentos y sesiones'), ('practicas', 'Guías prácticas'), ('rubrica_final', 'Rúbrica del producto final'),
    ('bibliografia', 'Bibliografía'),
]
NIVELES = ['Indicador', 'Receptivo', 'Resolutivo', 'Reflexivo', 'Crítico', 'Cocreativo']


def seccion(fila):
    top = str(fila['partes'][0])
    for k, nombre in SECCIONES:
        if k == top:
            return nombre
    return 'Otros datos'


NOMBRES = {'codigo': 'código', 'creditos': 'créditos', 'periodo': 'período', 'competencia_perfil': 'competencia del perfil de egreso',
           'competencia_pf': 'competencia del proyecto formativo', 'contribucion': 'contribución', 'metodologias': 'metodologías',
           'practico': 'práctico-experimental', 'autonomo': 'autónomo', 'docente': 'docente', 'proposito': 'propósito',
           'evaluacion': 'evaluación', 'aporte_pis': 'aporte al PIS', 'pis': 'PIS', 'producto_final': 'producto final',
           'correquisitos': 'correquisitos', 'posgrado': 'posgrado', 'titulo': 'título', 'unidad': 'unidad de organización'}


def etiqueta(partes):
    """Nombre legible para el docente: «Momento 1 · Sesión 2 · contenidos»."""
    out, prev = [], None
    for p in partes:
        if isinstance(p, int):
            if prev == 'momentos':
                out[-1] = f'Momento {p + 1}'
            elif prev == 'sesiones':
                out[-1] = f'Sesión {p + 1}'
            elif prev == 'ra':
                out[-1] = f'RA{p + 1}'
            elif prev == 'practicas':
                out[-1] = f'Práctica {p + 1}'
            elif prev in ('rubrica', 'rubrica_final'):
                out[-1] = f'{"Rúbrica" if prev == "rubrica" else "Rúbrica final"} · fila {p + 1}'
            elif prev == 'bibliografia':
                out[-1] = f'Referencia {p + 1}'
            elif out and out[-1].startswith('Referencia'):
                continue
            elif out and out[-1].startswith(('Rúbrica', 'Rúbrica final')) and len(NIVELES) > p:
                out.append(NIVELES[p])
            elif out and out[-1].startswith('RA'):
                out.append(['', 'resultado', 'evidencia'][p] if p < 3 else str(p + 1))
            else:
                out.append(str(p + 1))
        else:
            out.append(NOMBRES.get(str(p), str(p).replace('_', ' ')))
        prev = p
    return ' · '.join(x for x in out if x)


def fuente_txt(f, principal=''):
    if not f['archivo']:
        return 'Sin referencia'
    nombre = '' if f['archivo'] == principal else f['archivo'] + (', ' if f['pagina'] else '')
    return (nombre + (f'p. {f["pagina"]}' if f['pagina'] else '')) or 'documento completo'


def informe(rep):
    def md(v):
        return escape(str(v), quote=False).replace('|', '&#124;').replace('\r', ' ').replace('\n', '<br>')
    s = rep['resumen']
    lines = ['# Ficha de extracción del sílabo', '', rep['limite'], '',
             f'**Documento vigente:** {md(rep["documento"] or "sin definir")}  ',
             f'**Campos:** {s["campos"]} · localizados o declarados: {s["localizados_o_declarados"]} · pendientes: {s["pendientes"]}', '']
    rv = [r for r in rep['revisiones'] if r['vigente']]
    lines.append('**Revisión docente:** ' + (', '.join(md(r['registro']) for r in rv) + ' (vigente)' if rv else 'pendiente'))
    lines += ['', '| Sección | Campo | Valor extraído | Fuente | Estado | Sugerencia / nota |', '|---|---|---|---|---|---|']
    for f in rep['filas']:
        icono, texto = ESTADOS[f['estado']]
        extra = []
        if f['sugerencia']:
            extra.append(f'¿p. {f["sugerencia"]["pagina"]}?')
        if f['nota']:
            extra.append(f['nota'])
        if f['estado'] in ('parcial', 'no_localizado') and f['proporcion']:
            extra.append(f'{round(f["proporcion"] * 100)} % de palabras')
        lines.append('| ' + ' | '.join(md(x) for x in (seccion(f), etiqueta(f['partes']), f['valor'], fuente_txt(f),
                                                         f'{icono} {texto}', '; '.join(extra))) + ' |')
    lines += ['', '## Hallazgos', ''] + (['- ' + md(h) for h in rep['hallazgos']] or ['- Ninguno.'])
    for r in rep['revisiones']:
        if not r['vigente']:
            lines.append('- ' + md(f'Registro {r["registro"]} no vale como revisión: ' + '; '.join(r['pendientes'])))
    lines += ['', '## Huellas de los documentos', ''] + [f'- {md(k)}: `{v}`' for k, v in sorted(rep['documentos'].items())]
    return '\n'.join(lines) + '\n'


def vista(rep, titulo):
    """HTML autónomo para el docente: se abre con doble clic, se imprime y no carga nada de internet."""
    e = lambda v: escape(str(v))
    s = rep['resumen']
    tono = {'✔': 'ok', '◐': 'warn', '▲': 'warn', '✖': 'err'}
    rv = [r for r in rep['revisiones'] if r['vigente']]
    grupos = {}
    for f in rep['filas']:
        grupos.setdefault(seccion(f), []).append(f)
    cuerpo = []
    for nombre, filas in grupos.items():
        pend = sum(not f['resuelto'] for f in filas)
        rows = []
        for f in filas:
            icono, texto = ESTADOS[f['estado']]
            extra = []
            if f['sugerencia']:
                extra.append(f'Quizá está en la página {f["sugerencia"]["pagina"]}.')
            if f['nota']:
                extra.append(f['nota'])
            rows.append(f'<tr><th scope="row">{e(etiqueta(f["partes"]))}</th><td class="valor">{e(f["valor"])}</td>'
                        f'<td>{e(fuente_txt(f, rep["documento"]))}</td><td class="estado {tono[icono]}">{icono} {e(texto)}'
                        + (f'<small>{e(" ".join(extra))}</small>' if extra else '') + '</td></tr>')
        cuerpo.append(f'<details{" open" if pend else ""}><summary>{e(nombre)} <span>{len(filas)} datos · {pend} por revisar</span></summary>'
                      '<table><thead><tr><th>Dato</th><th>Lo que se transcribió</th><th>Dónde está</th><th>Comprobación</th></tr></thead>'
                      f'<tbody>{"".join(rows)}</tbody></table></details>')
    hall = ''.join(f'<li>{e(h)}</li>' for h in rep['hallazgos'])
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ficha del sílabo · {e(titulo)}</title>
<style>
:root{{--morado:#3C235F;--naranja:#EA600A;--naranja-texto:#B34A07;--tinta:#1B1722;--tinta2:#5D5866;--linea:#E2DDEA;--suave:#F3EFF8;--ok:#1E7B4A;--warn:#8F5A00;--err:#C62828}}
body{{font-family:Arial,'Helvetica Neue',sans-serif;color:var(--tinta);margin:0;background:#F7F5FA;line-height:1.5}}
header{{background:var(--morado);color:#fff;padding:22px 28px;border-bottom:5px solid var(--naranja)}}
header h1{{margin:0 0 4px;font-size:1.45rem}} header p{{margin:0;opacity:.85}}
main{{max-width:1180px;margin:0 auto;padding:22px}}
.card{{background:#fff;border:1px solid var(--linea);border-radius:10px;padding:16px 20px;margin-bottom:18px}}
.cifras{{display:flex;gap:28px;flex-wrap:wrap}} .cifras b{{font-size:1.6rem;color:var(--morado);display:block}}
details{{background:#fff;border:1px solid var(--linea);border-radius:10px;margin-bottom:14px}}
summary{{cursor:pointer;padding:12px 18px;font-weight:bold;color:var(--morado);border-bottom:3px solid var(--naranja)}}
summary span{{font-weight:normal;color:var(--tinta2);margin-left:8px;font-size:.9rem}}
table{{width:100%;border-collapse:collapse;font-size:.92rem}} th,td{{text-align:left;vertical-align:top;padding:8px 12px;border-bottom:1px solid var(--linea)}}
thead th{{background:var(--suave);color:var(--morado)}} tbody th{{width:17%;color:var(--morado);font-weight:600}}
td.valor{{white-space:pre-wrap;width:45%}} td:nth-child(3){{width:9%;white-space:nowrap}} td.estado{{width:29%}} td.estado small{{display:block;color:var(--tinta2)}}
.ok{{color:var(--ok)}} .warn{{color:var(--warn)}} .err{{color:var(--err);font-weight:600}}
ol li{{margin-bottom:4px}} .limite{{color:var(--tinta2);font-size:.88rem}}
@media print{{body{{background:#fff}} details{{break-inside:avoid}} details:not([open]){{display:block}} details>*{{display:block}}}}
</style></head><body>
<header><h1>Ficha del sílabo para revisar</h1><p>{e(titulo)} · Universidad Tecnológica Indoamérica</p></header>
<main>
<section class="card"><div class="cifras"><div><b>{s['campos']}</b>datos transcritos</div><div><b>{s['localizados_o_declarados']}</b>localizados en el documento</div>
<div><b>{s['pendientes']}</b>por revisar</div><div><b>{"Sí" if rv else "Pendiente"}</b>revisión docente</div></div>
<p>Documento vigente: <strong>{e(rep['documento'] or 'sin definir')}</strong>. La columna «Dónde está» indica su página, salvo que se nombre otro archivo.</p></section>
<section class="card"><h2 style="margin-top:0;color:var(--morado);font-size:1.1rem">Cómo revisar esta ficha</h2><ol>
<li>Abre el sílabo en la página indicada y compara cada dato con lo que se transcribió, en especial los marcados con ▲ o ✖.</li>
<li>Fíjate en fechas, horas, resultados de aprendizaje, evidencias y rúbricas: el aula y Canvas se construyen con estos datos.</li>
<li>Dile a tu asistente qué corregir o confirma que la ficha es fiel. Tu confirmación queda registrada en ESTADO.md.</li></ol>
<p class="limite">{e(rep['limite'])}</p></section>
{"<section class='card'><h2 style='margin-top:0;color:var(--err);font-size:1.1rem'>Pendientes generales</h2><ul>" + hall + "</ul></section>" if hall else ""}
{"".join(cuerpo)}
</main></body></html>
'''


# ───────────── comandos ─────────────
def iniciar(root, documento):
    if ruta(root, MAPA, existe=False).exists():
        raise ValueError('Ya existe control/ficha_silabo.json; no se sobrescribe. Revisa y corrige sus referencias.')
    campos(cargar(root, SILABO))
    paginas(root, documento)                    # comprueba que existe su texto extraído y está al día
    rel = ruta(root, documento).relative_to(root).as_posix()
    guardar_mapa(root, {'version': 1, 'documento': rel, 'documentos': {rel: digest(ruta(root, rel))}, 'referencias': []})
    return f'Ficha iniciada con {rel}. Ejecuta completar para proponer páginas y verificar para ver todos los datos.'


def completar(root):
    mapa = leer_mapa(root)
    if mapa is None:
        raise ValueError('Primero inicia la ficha: iniciar --documento <sílabo vigente>.')
    doc = mapa['documento']
    if digest(ruta(root, doc)) != mapa['documentos'][doc]:
        raise ValueError(f'{doc} cambió después de crear la ficha: revisa sus referencias antes de proponer páginas.')
    pages = paginas(root, doc)
    ya = {r['campo']: r for r in mapa['referencias']}
    nuevas, repetidas, dudosas, cerca = 0, 0, 0, 0
    for c in campos(cargar(root, SILABO)):
        if c['campo'] in ya:
            if ya[c['campo']]['archivo'] == doc and ya[c['campo']]['pagina']:
                cerca = ya[c['campo']]['pagina']
            continue
        if PENDIENTE.search(c['valor']) or not c['valor'].strip():
            continue
        est, n, otras = elegir(c['valor'], pages, cerca)
        if est not in ('exacta', 'palabras', 'cotejo_visual'):
            dudosas += 1
            continue
        nota = ('También aparece en p. ' + ', '.join(map(str, otras)) + '.') if otras and len(otras) <= 6 else (
            f'También aparece en otras {len(otras)} páginas.' if otras else '')
        mapa['referencias'].append({'campo': c['campo'], 'archivo': doc, 'pagina': n if len(pages) > 1 else None,
                                    'valor_sha256': huella_valor(c['valor']), 'nota': nota, 'origen': 'sugerida'})
        nuevas += 1
        repetidas += bool(otras)
        cerca = n
    guardar_mapa(root, mapa)
    return (f'{nuevas} página(s) propuestas ({repetidas} de datos que aparecen en varias páginas: se eligió la más cercana en el orden '
            f'del sílabo y se anotan las demás); {dudosas} dato(s) quedan para ubicar y cotejar a mano. '
            'No se cambiaron referencias existentes. Ejecuta verificar.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--aula', type=Path, default=Path(__file__).resolve().parents[1])
    sub = ap.add_subparsers(dest='cmd', required=True)
    i = sub.add_parser('iniciar', help='Crear la ficha con el sílabo vigente, sin sobrescribir una existente')
    i.add_argument('--documento', required=True, help='ruta del sílabo vigente dentro de fuentes/')
    sub.add_parser('completar', help='Proponer páginas solo para datos sin referencia y con coincidencia inequívoca')
    v = sub.add_parser('verificar', help='Escribir control/FICHA_SILABO.md y .html desde los archivos actuales')
    v.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    root = args.aula.expanduser().resolve()
    try:
        if args.cmd == 'iniciar':
            print(iniciar(root, args.documento)); return 0
        if args.cmd == 'completar':
            print(completar(root)); return 0
        rep = comprobar(root)
        titulo = ''
        try:
            titulo = cargar(root, SILABO).get('curso', {}).get('nombre', '')
        except (ValueError, OSError, AttributeError):
            pass
        escribir(ruta(root, INFORME, existe=False), informe(rep))
        escribir(ruta(root, VISTA, existe=False), vista(rep, titulo or 'Proyecto formativo'))
        print(json.dumps(rep, ensure_ascii=False, indent=2) if args.json else informe(rep))
        return 1 if rep['hallazgos'] or rep['resumen']['pendientes'] else 0
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as ex:
        if args.cmd == 'verificar':
            aviso = '# Ficha no comprobada\n\nNo uses una ficha anterior como vigente. Corrige el problema y vuelve a verificar.\n\n'
            for rel, txt in ((INFORME, aviso + escape(str(ex)) + '\n'),
                             (VISTA, '<!doctype html><meta charset="utf-8"><title>Ficha no comprobada</title><h1>Ficha no comprobada</h1><p>'
                              + escape(str(ex)) + '</p>')):
                try:
                    escribir(ruta(root, rel, existe=False), txt)
                except (ValueError, OSError):
                    pass
        print('No se completó la ficha: ' + str(ex), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
