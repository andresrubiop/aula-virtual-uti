#!/usr/bin/env python3
"""Panel local de avance para el profesor: PANEL.html en la carpeta del aula, derivado de ESTADO.md.

python3 control/panel.py            # escribe PANEL.html (se abre con doble clic)
python3 control/panel.py --json     # además imprime los datos del panel
En aulas anteriores: python3 <skill>/assets/plantilla-aula/control/panel.py --aula <aula>

No es otro registro: lee ESTADO.md (fases, unidades, preguntas, decisiones, próximos pasos y operaciones) y las
comprobaciones existentes (estado, impacto, ficha del sílabo y cobertura) sin modificarlas. Solo escribe PANEL.html.
Los accesos apuntan a archivos locales que existen; la fecha de modificación solo sugiere si algo quedó anterior a
otro cambio. El panel no aprueba fases, no ejecuta pruebas ni compilaciones y no realiza operaciones remotas.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote

from estado import FIN, INICIO, RESERVADOS, analizar, clave_ruta, escribir, leer, plan_impacto, ruta, verificar

SALIDA = 'PANEL.html'
LIMITE = ('Panel derivado de ESTADO.md y de las comprobaciones locales. No es un registro aparte: si algo no coincide, '
          'manda ESTADO.md. No aprueba fases, no certifica calidad académica y no comprueba Canvas ni NotebookLM.')
ICONOS = ('✅', '🟡', '⬜', '⛔', '⏭')
TONO = {'✅': 'ok', '🟡': 'warn', '⬜': 'idle', '⛔': 'err', '⏭': 'idle'}
VACIOS = {'', '—', '-', '(ninguna todavía)', '(ninguno todavía)', 'ninguna', 'ninguno', '(ninguna)', '(ninguno)'}


# ───────────── lectura de ESTADO.md (solo texto visible) ─────────────
def visible(text):
    text = re.sub(re.escape(INICIO) + r'.*?' + re.escape(FIN), '', text, flags=re.S)
    return re.sub(r'^```.*?^```[^\n]*', '', text, flags=re.M | re.S)


def secciones(text):
    result = {}
    for parte in re.split(r'^##\s+', visible(text), flags=re.M)[1:]:
        titulo, _, cuerpo = parte.partition('\n')
        clave = re.sub(r'^\d+\.\s*', '', titulo.strip()).casefold()
        result.setdefault(clave, cuerpo)
    return result


def buscar(secs, *nombres):
    for nombre in nombres:
        for clave, cuerpo in secs.items():
            if clave.startswith(nombre):
                return cuerpo
    return ''


def tabla(cuerpo):
    filas = []
    for line in cuerpo.splitlines():
        if not line.lstrip().startswith('|'):
            if filas:
                break
            continue
        celdas = [c.strip() for c in line.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-+:?', c) for c in celdas if c):
            continue
        filas.append(celdas)
    return (filas[0], filas[1:]) if filas else ([], [])


def lista(cuerpo):
    items, actual = [], None
    for line in cuerpo.splitlines():
        m = re.match(r'^\s*(?:[-*]|\d+[.)])\s+(.*)$', line)
        if m:
            actual = m[1].strip(); items.append(actual)
        elif line.strip() and items and line.startswith(('  ', '\t')):
            items[-1] += ' ' + line.strip()
    if not items:
        texto = ' '.join(l.strip() for l in cuerpo.splitlines() if l.strip() and not l.lstrip().startswith(('|', '<!--')))
        if texto and texto.casefold() not in VACIOS:
            items = [texto]
    return [i for i in items if i.casefold() not in VACIOS and not re.fullmatch(r'\[[^\]]*\]', i)]


def reanudacion(cuerpo):
    campos = []
    for etiqueta, valor in re.findall(r'^-\s*\*\*([^*]+?):\*\*\s*(.*)$', cuerpo, re.M):
        valor = valor.strip()
        campos.append({'campo': etiqueta.strip(), 'valor': valor, 'sin_definir': not valor or valor.startswith('[')})
    return campos


def fases_tabla(cuerpo):
    _, filas = tabla(cuerpo)
    result = []
    for celdas in filas:
        m = re.match(r'^(\d+)\s*[.·-]?\s*(.*)$', celdas[0]) if celdas else None
        if not m or len(celdas) < 2:
            continue
        estado = celdas[1]
        icono = next((i for i in ICONOS if estado.startswith(i)), '')
        result.append({'fase': int(m[1]), 'nombre': m[2].strip(), 'estado': estado, 'icono': icono,
                       'notas': ' | '.join(c for c in celdas[2:] if c)})
    return result


# ───────────── archivos del aula ─────────────
def seguro(root, rel):
    """Ruta dentro del aula, sin privados ni enlaces; None si no existe o no está permitida."""
    try:
        p = ruta(root, rel, existe=False)
    except ValueError:
        return None
    return p if p.exists() else None


def mtime(p):
    return p.stat().st_mtime if p else None


def mas_reciente(root, rel, patron='*'):
    base = seguro(root, rel)
    if not base or not base.is_dir():
        return None, None
    mejor = (None, None)
    for folder, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = [d for d in dirs if d.casefold() not in RESERVADOS and not (Path(folder) / d).is_symlink()]
        for name in files:
            f = Path(folder) / name
            if f.is_symlink() or not f.match(patron):
                continue
            t = f.stat().st_mtime
            if mejor[0] is None or t > mejor[0]:
                mejor = (t, f.relative_to(root).as_posix())
    return mejor


def archivos(root, rel, patron):
    base = seguro(root, rel)
    if not base or not base.is_dir():
        return []
    out = []
    for folder, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d.casefold() not in RESERVADOS and not (Path(folder) / d).is_symlink())
        for name in sorted(files):
            f = Path(folder) / name
            if not f.is_symlink() and f.match(patron) and f.stat().st_size:
                out.append(f.relative_to(root).as_posix())
    return out


def acceso(root, rel, titulo, para, evidencias, previo=None, ancla=''):
    p = seguro(root, rel)
    item = {'titulo': titulo, 'ruta': rel, 'ancla': ancla, 'para': para, 'existe': bool(p and p.is_file() and p.stat().st_size),
            'avisos': [], 'comprobacion': ''}
    if not item['existe']:
        return item
    for antes, motivo in previo or []:
        if antes and antes > mtime(p) + 1:
            item['avisos'].append(motivo)
    if evidencias is None:
        return item
    regs = evidencias.get(clave_ruta(rel), [])
    if regs:
        vigentes = [r for r in regs if r['vigente']]
        item['comprobacion'] = (f'Comprobado y vigente ({", ".join(r["id"] for r in vigentes)})' if vigentes
                                else f'Cambió o depende de algo que cambió desde la comprobación ({", ".join(r["id"] for r in regs)})')
    else:
        item['comprobacion'] = 'Sin comprobación registrada en ESTADO.md'
    return item


def accesos(root, registros, detalles, unidades=()):
    vigencia = {d['id']: d for d in detalles}
    evidencias = {}
    for ident, item in registros.items():
        for rel in item['entregables']:
            evidencias.setdefault(clave_ruta(rel), []).append({'id': ident, 'vigente': vigencia.get(ident, {}).get('vigente', False)})
    src, src_rel = mas_reciente(root, 'hub/src')
    dist = mtime(seguro(root, 'hub/dist/index.html'))
    silabo = mtime(seguro(root, 'canvas/silabo.json'))
    recompilar = (src, f'Compilada antes del último cambio en {src_rel}: pide recompilar.')
    grupos = []
    aula = [acceso(root, 'hub/dist/index.html', 'Aula del estudiante', 'Recorrer el aula como la verán los estudiantes (ES/EN).',
                   evidencias, [recompilar]),
            acceso(root, 'hub/dist/profesor.html', 'Edición docente', 'El aula con solucionarios y notas de mediación.',
                   evidencias, [recompilar])]
    for u in unidades:
        uid = u.get('id') if isinstance(u, dict) else None
        if not isinstance(uid, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,30}', uid):
            continue
        nombre = u.get('title', {}).get('es', '') if isinstance(u.get('title'), dict) else ''
        item = acceso(root, 'hub/dist/index.html', f'U{u.get("n", "")} · ' + (u.get('short', {}).get('es', '') if isinstance(u.get('short'), dict) else uid),
                      nombre or 'Abrir la unidad en el aula del estudiante.', None, [recompilar], ancla='#/' + uid)
        aula.append(item)
    grupos.append({'grupo': 'Aula interactiva y unidad piloto', 'accesos': aula})
    revision = [acceso(root, 'control/FICHA_SILABO.html', 'Ficha del sílabo', 'Cotejar cada dato transcrito con su página.', evidencias,
                       [(max(filter(None, (silabo, mtime(seguro(root, 'control/ficha_silabo.json')))), default=None),
                         'Generada antes del último cambio del sílabo en datos o de su ficha: pide verificarla de nuevo.')]),
                acceso(root, 'PLANIFICACION.md', 'Planificación', 'Qué se construye en cada unidad (se abre como texto).', evidencias),
                acceso(root, 'control/COBERTURA.md', 'Cobertura del sílabo', 'RA, temas y prácticas con recursos revisados (texto).', evidencias),
                acceso(root, 'ESTADO.md', 'Estado completo', 'El tablero que genera este panel (texto).', None)]
    grupos.append({'grupo': 'Para revisar y aprobar', 'accesos': revision})
    pdfs = [acceso(root, rel, Path(rel).name, rel.split('/')[1] if rel.count('/') > 1 else 'materiales', evidencias,
                   [(dist, 'Anterior a la última compilación del aula: puede no reflejar los cambios.')])
            for rel in archivos(root, 'materiales', '*.pdf')]
    grupos.append({'grupo': 'PDF de manuales, presentaciones y prácticas', 'accesos': pdfs,
                   'vacio': 'Aún no hay PDF en materiales/ (se generan en la fase 6).'})
    entrega = [acceso(root, rel, Path(rel).name,
                      'Edición docente en un solo archivo: no la compartas con estudiantes.' if rel.endswith('-profesor.html')
                      else 'Aula del estudiante en un solo archivo, para compartir o subir a Canvas.', evidencias,
                      [(dist, 'Anterior a la última compilación del aula: pide regenerarla.')])
               for rel in archivos(root, 'autonomo', '*.html') if rel.count('/') == 1]
    entrega += [acceso(root, 'autonomo/paquete/index.html', 'Aula para llevar (carpeta)', 'Aula con materiales y videos, sin conexión.',
                       evidencias, [(dist, 'Anterior a la última compilación del aula: pide regenerarla.')])]
    entrega += [acceso(root, rel, Path(rel).name, 'Paquete para importar en Canvas (no se abre en el navegador).', evidencias,
                       [(max(filter(None, (src, silabo)), default=None), 'Generado antes del último cambio del aula o del sílabo: pide regenerarlo.')])
                for rel in archivos(root, 'canvas/salida', '*.imscc')]
    entrega.append(acceso(root, 'canvas/LEEME.md', 'Cómo importar en Canvas', 'Pasos de importación y qué revisar (texto).', None))
    grupos.append({'grupo': 'Entrega', 'accesos': [a for a in entrega if a['existe'] or a['ruta'] == 'autonomo/paquete/index.html']})
    return grupos


# ───────────── comprobaciones existentes ─────────────
def intento(fn):
    try:
        return fn(), ''
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, json.JSONDecodeError) as ex:
        return None, str(ex)


def comprobaciones(root):
    out = {}
    rep, err = intento(lambda: verificar(root))
    out['estado'] = {'error': err} if err else {'resultado': rep['resultado'], 'incidencias': rep['errores'],
                                                 'avisos': rep['avisos'], 'siguiente_accion': rep['siguiente_accion']}
    rep, err = intento(lambda: plan_impacto(root))
    out['impacto'] = {'error': err} if err else {'afectados': [{'id': a['id'], 'fase': a['fase'], 'entregables': a['entregables']}
                                                               for a in rep['afectados']],
                                                 'sin_relacion': rep['sin_relacion_declarada']}
    if seguro(root, 'control/ficha_silabo.json'):
        import ficha_silabo
        rep, err = intento(lambda: ficha_silabo.comprobar(root))
        out['ficha'] = {'error': err} if err else {**rep['resumen'], 'revisada': any(r['vigente'] for r in rep['revisiones']),
                                                   'hallazgos': rep['hallazgos']}
    else:
        out['ficha'] = {'no_iniciada': True}
    if seguro(root, 'control/cobertura.json'):
        import cobertura
        rep, err = intento(lambda: cobertura.comprobar(root))
        out['cobertura'] = {'error': err} if err else {**rep['resumen'], 'hallazgos': rep['hallazgos']}
    else:
        out['cobertura'] = {'no_iniciada': True}
    out['videos'] = estado_videos(root)
    import respaldo
    rep, err = intento(lambda: respaldo.resumen(root))
    out['respaldos'] = {'error': err} if err else rep
    return out


def estado_videos(root):
    """Estado de cada video según sus archivos: guion, pedido a NotebookLM, descargado, en el aula y subtítulos."""
    guiones = sorted((g for g in archivos(root, 'videos/guiones', 'V*.md')), key=lambda r: [int(x) for x in re.findall(r'\d+', Path(r).stem)])
    pedidos = {}
    est = seguro(root, 'videos/estado.json')
    if est and est.is_file():
        try:
            for clave, c in json.loads(est.read_text(encoding='utf-8')).items():
                for k, v in c.items():
                    if re.fullmatch(r'V\d+\.\d+', k) and v:
                        pedidos[(k, clave.split('.')[-1])] = True
        except (ValueError, AttributeError):
            pass
    lista = []
    for g in guiones:
        v = Path(g).stem
        n = v[1:].split('.')[0]
        idiomas = {}
        for lang in ('es', 'en'):
            aula = seguro(root, f'videos/unidad-{n}/{v}.{lang}.mp4')
            bruto = seguro(root, f'videos/bruto/{v}.{lang}.mp4')
            idiomas[lang] = ('en el aula' if aula else 'descargado' if bruto else 'en NotebookLM' if pedidos.get((v, lang)) else '')
        subs = [s for s in ('es', 'en') if seguro(root, f'videos/unidad-{n}/{v}.en.{s}.vtt')]
        if not idiomas['es'] and not idiomas['en']:
            estado = 'guion listo'
        else:
            estado = ' · '.join(f'{"inglés" if l == "en" else "español"}: {x}' for l, x in (('en', idiomas['en']), ('es', idiomas['es'])) if x)
            if idiomas['en'] == 'en el aula' and idiomas['es'] != 'en el aula':
                estado += ' · subtítulos en español' if 'es' in subs else ' · faltan subtítulos en español'
        lista.append({'video': v, 'estado': estado, 'en_aula': 'en el aula' in estado, 'subtitulos': subs})
    return {'archivos': len(archivos(root, 'videos', '*.mp4')), 'guiones': len(lista), 'en_aula': sum(x['en_aula'] for x in lista), 'lista': lista}


def unidades_curso(root):
    p = seguro(root, 'hub/src/course.json')
    if not p:
        return '', '', []
    try:
        c = json.loads(p.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        return '', '', []
    titulo = c.get('title', {}).get('es', '') if isinstance(c.get('title'), dict) else str(c.get('title', ''))
    periodo = str(c.get('term', ''))
    return titulo, '' if periodo.startswith('[') else periodo, c.get('units', []) if isinstance(c.get('units'), list) else []


def construir(root):
    p = ruta(root, 'ESTADO.md')
    text = p.read_bytes().decode('utf-8')
    secs = secciones(text)
    try:
        _, data = leer(root)
        registros = data['registros']
        detalles, _ = analizar(root, registros)
        aviso_registro = ''
    except ValueError as ex:
        registros, detalles, aviso_registro = {}, [], str(ex)
    titulo, periodo, unidades_aula = unidades_curso(root)
    cabecera = re.search(r'^>\s*\*\*Última actualización:\*\*\s*(.*)$', text, re.M)
    fases = fases_tabla(buscar(secs, 'fases'))
    reanudar = reanudacion(buscar(secs, 'punto de reanudación'))
    preguntas = lista(buscar(secs, 'preguntas pendientes'))
    bloqueos = [c['valor'] for c in reanudar if c['campo'].casefold().startswith('bloqueos') and not c['sin_definir']
                and c['valor'].casefold().strip(' .') not in {'ninguno', 'ninguna', 'ninguno confirmado', 'sin bloqueos'}]
    checks = comprobaciones(root)
    necesita = [{'tipo': 'pregunta', 'texto': q} for q in preguntas]
    necesita += [{'tipo': 'bloqueo', 'texto': b} for b in bloqueos]
    necesita += [{'tipo': 'fase', 'texto': f'Fase {f["fase"]} · {f["nombre"]}: ' + (f['notas'] or 'espera tu decisión o revisión.')}
                 for f in fases if f['icono'] == '⛔']
    ficha = checks['ficha']
    if ficha.get('campos') and not ficha.get('revisada'):
        necesita.append({'tipo': 'revision', 'texto': f'Revisar la ficha del sílabo ({ficha["pendientes"]} de {ficha["campos"]} datos por cotejar) y confirmar o pedir cambios.'})
    dec_cab, decisiones = tabla(buscar(secs, 'decisiones'))
    ops_cab, operaciones = tabla(buscar(secs, 'operaciones externas'))
    uni_cab, unidades = tabla(buscar(secs, 'unidades'))
    return {'fecha': datetime.now(timezone.utc).astimezone().isoformat(timespec='minutes'),
            'estado_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'titulo': titulo, 'periodo': periodo, 'actualizacion': cabecera[1].strip() if cabecera and not cabecera[1].lstrip().startswith('[') else '',
            'reanudacion': reanudar, 'fases': fases, 'necesita': necesita,
            'unidades': {'columnas': uni_cab, 'filas': [f for f in unidades if any(c not in VACIOS for c in f[1:])]},
            'decisiones': {'columnas': dec_cab, 'filas': [f for f in decisiones if any(c for c in f)]},
            'proximos': lista(buscar(secs, 'próximos pasos')),
            'operaciones': {'columnas': ops_cab, 'filas': [f for f in operaciones if any(c for c in f)]},
            'comprobaciones': checks, 'aviso_registro': aviso_registro,
            'accesos': accesos(root, registros, detalles, unidades_aula), 'limite': LIMITE}


# ───────────── HTML ─────────────
def md(v):
    """Escapa y luego da formato mínimo a `código` y **negrita** del propio ESTADO.md."""
    s = escape(str(v))
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    return re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)


def href(rel):
    return quote(rel, safe='/')


def tabla_html(cab, filas, clase=''):
    if not filas:
        return ''
    th = ''.join(f'<th scope="col">{md(c)}</th>' for c in cab)
    def celda(c):
        icono = next((i for i in ICONOS if c.startswith(i)), '')
        return f'<td class="{TONO[icono]}">{md(c)}</td>' if icono else f'<td>{md(c)}</td>'
    tr = ''.join('<tr>' + ''.join(celda(c) for c in f) + '</tr>' for f in filas)
    return f'<div class="scroll"><table class="{clase}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def fecha_corta(m):
    """«16/11/2026 15:30 · motivo» para un respaldo del resumen."""
    try:
        f = datetime.fromisoformat(m['fecha']).strftime('%d/%m/%Y %H:%M')
    except (TypeError, ValueError, KeyError):
        f = str(m.get('fecha', ''))
    return f + (f' · {m["unidad"]}' if m.get('unidad') else '') + f' · {m.get("motivo", "")}'


def videos_html(v):
    if not v.get('lista'):
        return (f'<div class="chk idle"><h3>Videos</h3><p>Aún no hay guiones de video ({v.get("archivos", 0)} archivo(s) en videos/). '
                'Los videos son opcionales.</p></div>')
    filas = ''.join(f'<tr><th scope="row">{escape(x["video"])}</th><td>{escape(x["estado"])}</td></tr>' for x in v['lista'])
    clase = 'ok' if v['en_aula'] == v['guiones'] else 'idle'
    return (f'<div class="chk {clase}"><h3>Videos</h3><p>{v["en_aula"]} de {v["guiones"]} en el aula. La revisión de cada video '
            'por el docente se anota en ESTADO.md.</p><table class="mini"><tbody>' + filas + '</tbody></table></div>')


def vista(d):
    e = escape
    c = d['comprobaciones']
    hechas = sum(f['icono'] == '✅' for f in d['fases'])
    total = len(d['fases']) or 10
    actual = next((x['valor'] for x in d['reanudacion'] if x['campo'].casefold() == 'fase actual'), '')
    accion = next((x['valor'] for x in d['reanudacion'] if x['campo'].casefold().startswith('próxima acción')), '')
    objetivo = next((x['valor'] for x in d['reanudacion'] if x['campo'].casefold().startswith('objetivo')), '')

    nec = ''.join(f'<li><span class="tag {e(n["tipo"])}">{e({"pregunta": "Pregunta", "bloqueo": "Bloqueo", "fase": "Decisión", "revision": "Revisión"}[n["tipo"]])}</span> {md(n["texto"])}</li>'
                  for n in d['necesita'])
    nec = f'<ul class="necesita">{nec}</ul>' if nec else '<p>Nada registrado por ahora. Si tienes dudas o cambios, díselos a tu asistente.</p>'

    fases = ''.join(f'<li class="{TONO.get(f["icono"], "idle")}"><span class="ico" aria-hidden="true">{e(f["icono"] or "·")}</span>'
                    f'<span><b>{f["fase"]}. {md(f["nombre"])}</b><small>{md(f["estado"][len(f["icono"]):].strip() or {"✅": "Listo", "🟡": "En curso o parcial", "⬜": "Pendiente", "⛔": "Espera tu decisión", "⏭": "Omitido"}.get(f["icono"], ""))}'
                    f'{" · " + md(f["notas"]) if f["notas"] else ""}</small></span></li>' for f in d['fases'])

    rean = ''.join(f'<tr><th scope="row">{e(x["campo"])}</th><td class="{"idle" if x["sin_definir"] else ""}">{md(x["valor"] or "—")}</td></tr>'
                   for x in d['reanudacion'])

    def chk(nombre, info, ok, texto, detalle=()):
        if info.get('error'):
            clase, texto, detalle = 'err', 'No se pudo comprobar: ' + info['error'], ()
        elif info.get('no_iniciada'):
            clase = 'idle'
        else:
            clase = 'ok' if ok else 'warn'
        det = ''.join(f'<li>{md(x)}</li>' for x in list(detalle)[:6])
        mas = f'<li>… y {len(detalle) - 6} más (ver informe).</li>' if len(detalle) > 6 else ''
        return f'<div class="chk {clase}"><h3>{e(nombre)}</h3><p>{md(texto)}</p>{"<ul>" + det + mas + "</ul>" if det else ""}</div>'

    es, im, fi, co, rs = c['estado'], c['impacto'], c['ficha'], c['cobertura'], c.get('respaldos', {})
    checks = [chk('Estado y evidencias', es, es.get('resultado') == 'sin_incidencias',
                  'Sin discrepancias entre ESTADO.md y los archivos registrados.' if es.get('resultado') == 'sin_incidencias'
                  else f'{len(es.get("incidencias", []))} punto(s) por resolver.', es.get('incidencias', [])),
              chk('Cambios en materiales', im, not im.get('afectados') and not im.get('sin_relacion'),
                  'Ningún entregable registrado quedó afectado.' if not im.get('afectados') else
                  f'{len(im["afectados"])} entrega(s) por revisar tras cambios: ' + ', '.join(a['id'] for a in im['afectados']) + '.',
                  [f'Fuente sin relación declarada: `{x}`' for x in im.get('sin_relacion', [])]),
              chk('Ficha del sílabo', fi, fi.get('revisada') and not fi.get('pendientes'),
                  'Aún no se preparó.' if fi.get('no_iniciada') else
                  f'{fi.get("localizados_o_declarados", 0)} de {fi.get("campos", 0)} datos localizados · revisión docente: '
                  + ('registrada' if fi.get('revisada') else 'pendiente') + '.', fi.get('hallazgos', [])),
              chk('Cobertura del sílabo', co, not co.get('pendientes') and not co.get('hallazgos'),
                  'Aún no se inició.' if co.get('no_iniciada') else
                  f'{co.get("revision_declarada_vigente", 0)} de {co.get("elementos", 0)} RA, temas y prácticas con recursos revisados.',
                  co.get('hallazgos', [])),
              chk('Respaldos', {'no_iniciada': True} if not rs.get('total') and not rs.get('error') else rs,
                  not rs.get('aprobadas_sin_copia') and not rs.get('dañados'),
                  'Aún no hay respaldos. Pide «haz un respaldo» antes de un cambio amplio.' if not rs.get('total') else
                  f'{rs["total"]} respaldo(s). Último: {fecha_corta(rs["ultimo"])}. Último aprobado: '
                  + (fecha_corta(rs['ultimo_aprobado']) if rs.get('ultimo_aprobado') else 'ninguno todavía') + '.',
                  [f'Evidencia aprobada sin copia guardada: `{x}` (pide un respaldo «aprobado»).' for x in rs.get('aprobadas_sin_copia', [])]
                  + ([f'{rs["dañados"]} respaldo(s) no se pudieron leer: pide «comprueba los respaldos».'] if rs.get('dañados') else [])),
              videos_html(c['videos'])]

    grupos = []
    for g in d['accesos']:
        items = []
        for a in g['accesos']:
            info = ''.join(f'<small class="warn">{md(x)}</small>' for x in a['avisos'])
            info += f'<small>{md(a["comprobacion"])}</small>' if a['comprobacion'] else ''
            if a['existe']:
                items.append(f'<li><a class="btn" href="{e(href(a["ruta"]) + a["ancla"])}">{e(a["titulo"])}</a><span>{md(a["para"])}<small><code>{e(a["ruta"])}</code></small>{info}</span></li>')
            else:
                items.append(f'<li><span class="btn off" aria-disabled="true">{e(a["titulo"])}</span><span>{md(a["para"])}<small>Aún no existe <code>{e(a["ruta"])}</code>.</small></span></li>')
        cuerpo = f'<ul class="accesos">{"".join(items)}</ul>' if items else f'<p class="idle">{e(g.get("vacio", "Nada todavía."))}</p>'
        grupos.append(f'<section class="card"><h2>{e(g["grupo"])}</h2>{cuerpo}</section>')

    proximos = ''.join(f'<li>{md(x)}</li>' for x in d['proximos'])
    uni = tabla_html(d['unidades']['columnas'], d['unidades']['filas'], 'unidades') or '<p class="idle">Todavía no hay unidades registradas en ESTADO.md.</p>'
    dec = tabla_html(d['decisiones']['columnas'], d['decisiones']['filas']) or '<p class="idle">Sin decisiones registradas.</p>'
    ops = tabla_html(d['operaciones']['columnas'], d['operaciones']['filas']) or '<p class="idle">Sin operaciones externas registradas (Canvas, NotebookLM).</p>'
    aviso = f'<p class="err">El bloque de evidencias de ESTADO.md no se pudo leer: {e(d["aviso_registro"])}</p>' if d['aviso_registro'] else ''
    sub = ' · '.join(x for x in (d['titulo'], d['periodo'], 'Universidad Tecnológica Indoamérica') if x)
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel de avance · {e(d['titulo'] or 'Aula virtual')}</title>
<style>
:root{{--morado:#3C235F;--naranja:#EA600A;--tinta:#1B1722;--tinta2:#5D5866;--linea:#E2DDEA;--suave:#F3EFF8;--ok:#1E7B4A;--warn:#8F5A00;--err:#C62828;--idle:#6B6475}}
*{{box-sizing:border-box}} body{{font-family:Arial,'Helvetica Neue',sans-serif;color:var(--tinta);margin:0;background:#F7F5FA;line-height:1.5}}
header{{background:var(--morado);color:#fff;padding:22px 28px;border-bottom:5px solid var(--naranja)}}
header h1{{margin:0 0 4px;font-size:1.5rem}} header p{{margin:0;opacity:.9}}
main{{max-width:1180px;margin:0 auto;padding:22px;display:grid;gap:18px}}
.card{{background:#fff;border:1px solid var(--linea);border-radius:10px;padding:16px 20px}}
h2{{margin:0 0 10px;color:var(--morado);font-size:1.15rem}} h3{{margin:0 0 4px;font-size:1rem;color:var(--morado)}}
.hoy{{border-left:6px solid var(--naranja)}} .hoy .accion{{font-size:1.1rem;margin:.3rem 0}}
.barra{{height:12px;background:var(--suave);border-radius:6px;overflow:hidden;margin:8px 0 4px}} .barra i{{display:block;height:100%;background:var(--naranja)}}
.fases{{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:8px}}
.fases li{{display:flex;gap:10px;padding:8px 10px;border:1px solid var(--linea);border-radius:8px}} .fases .ico{{font-size:1.2rem}}
.fases small,.accesos small{{display:block;color:var(--tinta2)}} .fases li.ok{{background:#EEF7F1}} .fases li.err{{background:#FDEEEE}} .fases li.warn{{background:#FFF7E8}}
.necesita{{padding-left:0;list-style:none;margin:0}} .necesita li{{padding:6px 0;border-bottom:1px solid var(--linea)}}
.tag{{display:inline-block;font-size:.78rem;font-weight:bold;border-radius:4px;padding:1px 7px;margin-right:6px;color:#fff;background:var(--morado)}}
.tag.bloqueo,.tag.fase{{background:var(--err)}} .tag.revision{{background:#9A4A06}}
.checks{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}}
.chk{{border:1px solid var(--linea);border-left:6px solid var(--idle);border-radius:8px;padding:10px 12px}} .chk p{{margin:0}} .chk ul{{margin:6px 0 0;padding-left:18px;font-size:.88rem}}
table.mini{{margin-top:6px;font-size:.85rem}} table.mini th,table.mini td{{padding:4px 8px}} .chk.ok{{border-left-color:var(--ok)}} .chk.warn{{border-left-color:var(--warn)}} .chk.err{{border-left-color:var(--err)}}
.accesos{{list-style:none;padding:0;margin:0;display:grid;gap:10px}} .accesos li{{display:grid;grid-template-columns:minmax(190px,260px) 1fr;gap:14px;align-items:start}}
.btn{{display:block;text-align:center;padding:9px 12px;border-radius:8px;background:var(--morado);color:#fff;text-decoration:none;font-weight:bold;overflow-wrap:anywhere}}
a.btn:hover{{background:#2B1846}} a.btn:focus-visible{{outline:3px solid var(--naranja);outline-offset:2px}}
.btn.off{{background:var(--suave);color:var(--idle);border:1px dashed var(--idle)}}
.scroll{{overflow-x:auto}} table{{width:100%;border-collapse:collapse;font-size:.92rem}} th,td{{text-align:left;vertical-align:top;padding:7px 10px;border-bottom:1px solid var(--linea)}}
thead th{{background:var(--suave);color:var(--morado)}} tbody th{{color:var(--morado);width:28%}}
.ok{{color:var(--ok)}} .warn{{color:var(--warn)}} .err{{color:var(--err)}} .idle{{color:var(--idle)}} small.warn{{font-weight:bold}}
code{{background:var(--suave);padding:0 4px;border-radius:4px;font-size:.88em;overflow-wrap:anywhere}}
.limite{{color:var(--tinta2);font-size:.88rem}} .dos{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
@media (max-width:760px){{.dos,.accesos li{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}} .card{{break-inside:avoid}} a.btn{{color:var(--morado);background:none;border:1px solid var(--morado)}}}}
</style></head><body>
<header><h1>Panel de avance del aula</h1><p>{e(sub)}</p></header>
<main>
<section class="card hoy" aria-labelledby="t-hoy"><h2 id="t-hoy">Dónde vamos</h2>
<p><b>Fase actual:</b> {md(actual or 'sin registrar')}</p>
<p class="accion"><b>Próxima acción:</b> {md(accion or 'sin registrar')}</p>
{f'<p><b>Objetivo de la sesión:</b> {md(objetivo)}</p>' if objetivo and not objetivo.startswith('[') else ''}
<div class="barra" role="img" aria-label="{hechas} de {total} fases listas"><i style="width:{round(100 * hechas / total)}%"></i></div>
<p class="limite">{hechas} de {total} fases marcadas como listas en ESTADO.md. {md(d['actualizacion'])}</p>{aviso}</section>
<section class="card" aria-labelledby="t-nec"><h2 id="t-nec">Lo que necesita de ti</h2>{nec}</section>
<section class="card" aria-labelledby="t-fases"><h2 id="t-fases">Fases</h2><ol class="fases">{fases}</ol></section>
<section class="card" aria-labelledby="t-uni"><h2 id="t-uni">Unidades</h2>{uni}</section>
<section class="card" aria-labelledby="t-chk"><h2 id="t-chk">Comprobaciones automáticas</h2><div class="checks">{''.join(checks)}</div>
<p class="limite">Resultados del momento en que se generó el panel. Una comprobación correcta no reemplaza tu revisión académica.</p></section>
{''.join(grupos)}
<div class="dos"><section class="card"><h2>Próximos pasos</h2>{f'<ol>{proximos}</ol>' if proximos else '<p class="idle">Sin próximos pasos registrados.</p>'}</section>
<section class="card"><h2>Punto de reanudación</h2><div class="scroll"><table><tbody>{rean}</tbody></table></div></section></div>
<section class="card"><h2>Decisiones tomadas</h2>{dec}</section>
<section class="card"><h2>Operaciones externas y entregas</h2>{ops}</section>
<section class="card"><p class="limite">Generado el {e(d['fecha'])} desde ESTADO.md (SHA-256 <code>{e(d['estado_sha256'][:16])}…</code>).
Este panel no se actualiza solo: pide a tu asistente «actualiza el panel» después de cada sesión. {e(d['limite'])}</p></section>
</main></body></html>
'''


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--aula', type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument('--json', action='store_true', help='imprimir también los datos del panel')
    args = ap.parse_args(argv)
    root = args.aula.expanduser().resolve()
    try:
        datos = construir(root)
        escribir(ruta(root, SALIDA, existe=False), vista(datos))
    except (ValueError, OSError, UnicodeError) as ex:
        try:
            escribir(ruta(root, SALIDA, existe=False),
                     '<!doctype html><html lang="es"><meta charset="utf-8"><title>Panel no generado</title><h1>Panel no generado</h1>'
                     '<p>No se pudo leer el estado del aula. No uses un panel anterior como vigente.</p><p>' + escape(str(ex)) + '</p></html>\n')
        except (ValueError, OSError):
            pass
        print('No se generó el panel: ' + str(ex), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(datos, ensure_ascii=False, indent=2))
    else:
        print(f'Panel escrito en {SALIDA}. Ábrelo con doble clic. '
              f'{sum(f["icono"] == "✅" for f in datos["fases"])} de {len(datos["fases"])} fases listas; '
              f'{len(datos["necesita"])} asunto(s) esperan al docente.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
