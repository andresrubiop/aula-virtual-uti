#!/usr/bin/env python3
"""Aula virtual de Canvas (UTI) a partir del sílabo y del aula interactiva: genera el paquete que se importa.

Entradas
  canvas/silabo.json              datos del sílabo (esquema: canvas/LEEME.md; lo valida canvas/validar_silabo.py)
  canvas/exportado/*.imscc        el export de TU curso de Canvas (Configuración → Exportar contenido del curso).
                                  Si no hay ninguno se usa canvas/plantilla/plantilla-uti.imscc (plantilla institucional).
  canvas/fuentes/silabo.pdf       copia del sílabo SIN datos personales del docente (opcional; se publica)
  autonomo/<archivo>.html         el aula en un solo archivo (python3 hub/build.py && python3 hub/tools/autonomo.py)
  materiales/unidad-N/*.pdf       manuales, presentaciones y prácticas en PDF (python3 hub/tools/pdfs.py)
  videos/unidad-N/V#.#.(es|en).mp4  videos ya procesados (hub/tools/video_cards.py), los que existan

Salidas
  canvas/salida/<archivo>-canvas.imscc   paquete para Canvas → Configuración → Importar contenido del curso
  canvas/salida/pegar/*.html             el HTML de cada página, para pegarlo a mano si la importación duplica páginas

Qué hace con la plantilla institucional
  - Inicio: intacta, byte a byte.
  - Presentación: rellenada con el sílabo (mapa de formación, RA, problema, PIS, metodología, evaluación, docente).
  - Un módulo y una página por momento del sílabo (RA, evidencia, sesiones, rúbrica) y, por sesión, su página
    «Sesión» y su página «Recursos de aprendizaje» (PDF del aula, animaciones, videos). Los momentos de la plantilla
    que el sílabo no usa quedan sin publicar.
  - Actividad N = evidencia de desempeño del momento N, con su rúbrica socioformativa. Prácticas (guías prácticas):
    una tarea por cada una, sin publicar, para que el docente revise fechas y publique.
  - Páginas nuevas «Aula interactiva», «Materiales del curso» y «Guía del docente» (oculta).
Los identificadores generados son estables; el resultado de reimportar depende de Canvas y del curso.
No se garantiza ausencia de duplicados. Conserva un export original anterior a esta herramienta.

Uso:  python3 canvas/generar_canvas.py [--sin-videos] [--solo-es]
"""
import hashlib
import html
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import quote, unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'salida'
DATA = json.loads((HERE / 'silabo.json').read_text(encoding='utf-8'))
COURSE = json.loads((ROOT / 'hub/src/course.json').read_text(encoding='utf-8'))
CLAVE = COURSE['key']
ARCHIVO = COURSE.get('archivo', 'UTI-aula')
NOMBRE = DATA['curso']['nombre']
CURSO_ID = str(DATA['curso'].get('canvas_id') or 'ID_DEL_CURSO')
CARPETA = 'Aula y materiales'                              # carpeta visible en Archivos del curso
IDIOMAS = [('', 'ES')] if '--solo-es' in sys.argv else [('', 'ES'), ('.en', 'EN')]
SIN_VIDEOS = '--sin-videos' in sys.argv
UNIDAD = {u['n']: u for u in COURSE['units']}
ANIM = {a['id']: a['es'] for u in COURSE['units'] for a in u.get('anims', [])}
PRAC = (COURSE.get('practice') or {'es': 'Práctica'})['es']
AVISOS = []
e = html.escape


def aviso(msg):
    AVISOS.append(msg)


def gid(clave: str) -> str:
    """Identificador estable para lo nuevo; no garantiza la política de reimportación de Canvas."""
    return 'g' + hashlib.md5((CLAVE + ':' + clave).encode()).hexdigest()


def plantilla() -> Path:
    propios = sorted((HERE / 'exportado').glob('*.imscc'), key=lambda f: f.stat().st_mtime)
    if propios:
        return propios[-1]
    aviso('No hay un export de tu curso en canvas/exportado/: se usó la plantilla institucional incluida. Al importar, '
          'Canvas puede crear páginas duplicadas (presentacion-2, momento-1-2…): usa canvas/salida/pegar/ (ver LEEME).')
    return HERE / 'plantilla' / 'plantilla-uti.imscc'


# ───────────────────────── Sesiones, unidades y recursos del aula ─────────────────────────
def sesiones():
    """Todas las sesiones en orden: (momento, sesión, semana corrida)."""
    k = 0
    for M in DATA['momentos']:
        for s in M['sesiones']:
            k += 1
            yield M, s, k


SEMANA = {(M['n'], s['n']): k for M, s, k in sesiones()}


def videos_es():
    out = {}
    for f in sorted((ROOT / 'hub/src/content').glob('u*/*-preparacion.html')):
        for m in re.finditer(r'data-video="(V[\d.]+)".*?video-poster__title"><span lang="es">(.*?)</span><span lang="en">(.*?)</span>',
                             f.read_text(), re.S):
            out[m.group(1)] = (re.sub('<[^>]+>', '', m.group(2)), re.sub('<[^>]+>', '', m.group(3)))
    return out


VIDEO = videos_es()


def plan(M, s) -> dict:
    """Qué del aula corresponde a la sesión. Sale de sesiones[].aula en silabo.json; si falta, de course.json
    (unidades cuyo "moment" y "sessions" coinciden). {'u': [unidades], 'man', 'an', 'v', 'repaso': [unidades]}"""
    a = dict(s.get('aula') or {})
    us = a.get('unidad')
    us = [us] if isinstance(us, int) else list(us or [])
    if not us and not a.get('repaso'):
        us = [u['n'] for u in COURSE['units'] if u.get('moment') == M['n'] and s['n'] in (u.get('sessions') or [])]
    us = [n for n in us if n in UNIDAD]
    an = a.get('anims')
    if an is None:
        an = [x['id'] for n in us for x in UNIDAD[n].get('anims', [])]
    v = a.get('videos')
    if v is None:
        v = sorted(x for x in VIDEO if any(x.startswith(f'V{n}.') for n in us))
    return dict(u=us, man=a.get('manual') or '', an=[x for x in an if x in ANIM], v=[x for x in v if x in VIDEO],
                repaso=[n for n in a.get('repaso', []) if n in UNIDAD], tema=s.get('tema') or f'Sesión {s["n"]}')


def sub_practica(n):
    carpeta = ROOT / 'hub/src/content' / UNIDAD[n]['id']
    return next((x for x in ('practica', 'laboratorio', 'actividad') if list(carpeta.glob(f'*-{x}.html'))), None)


def tiene(n, sub):
    return bool(list((ROOT / 'hub/src/content' / UNIDAD[n]['id']).glob(f'*-{sub}.html')))


def pdfs(n, ext=''):
    """PDF de la unidad n en un idioma ('' = español, '.en'): (ruta en el paquete, título, origen)."""
    lab = UNIDAD[n].get('lab') or f'PR{n}'
    out = []
    for f, t in ((f'M{n}_manual{ext}.pdf', f'Manual M{n}'), (f'P{n}_presentacion{ext}.pdf', f'Presentación P{n}'),
                 (f'{lab}_practica{ext}.pdf', f'{PRAC} {lab}')):
        src = ROOT / 'materiales' / f'unidad-{n}' / f
        if src.exists():
            out.append((f'{CARPETA}/unidad-{n}/{f}', t, src))
    return out


def guia_nombre(g):
    slug = re.sub(r'[^a-zA-Z0-9_-]+', '-', g['id'])
    return slug + '-' + Path(g['archivo']).name


def video_files(v):
    """MP4 y póster ya procesados de un video, por idioma: {'es': (mp4, jpg|None), 'en': …} con rutas (paquete, origen)."""
    if SIN_VIDEOS:
        return {}
    d = ROOT / 'videos' / f'unidad-{v[1:].split(".")[0]}'
    out = {}
    for lang in ('es', 'en'):
        mp4 = d / f'{v}.{lang}.mp4'
        if mp4.exists():
            jpg = d / f'{v}.{lang}.jpg'
            out[lang] = ((f'{CARPETA}/videos/{mp4.name}', mp4), (f'{CARPETA}/videos/{jpg.name}', jpg) if jpg.exists() else None)
    return out


def page_ref(key):
    return f'$WIKI_REFERENCE$/pages/{key}'


def file_ref(path, modo='ver'):
    q = {'ver': '?canvas_=1&amp;canvas_qs_wrap=1', 'abrir': '?canvas_download=1',
         'bajar': '?canvas_download=1&amp;canvas_qs_download_frd=1'}[modo]
    return '$IMS-CC-FILEBASE$/' + '/'.join(quote(p) for p in path.split('/')) + q


# ───────────────────────── Estilos (los de la plantilla institucional) ─────────────────────────
FONT = "Verdana, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
TABLE = (f"width: 100%; max-width: 1000px; margin: 0px auto 28px; border-collapse: separate; table-layout: fixed; "
         f"border-radius: 10px; font-family: {FONT}; color: #2d3748; line-height: 1.65; border: 1px solid #cbd5e0;")
TH_HERO = ("background: linear-gradient(135deg, #3A1467 0%, #230C3E 100%); color: #ffffff; text-align: left; vertical-align: top; "
           "padding: clamp(18px, 3vw, 28px) clamp(14px, 3vw, 24px); border-bottom: 5px solid #F37121; border-radius: 10px 10px 0 0; "
           "font-size: clamp(17px, 4.2vw, 25px); line-height: 1.3;")
TH_SEC = ("background: linear-gradient(135deg, #3A1467 0%, #230C3E 100%); color: #ffffff; text-align: left; vertical-align: top; "
          "padding: clamp(14px, 2.5vw, 20px) clamp(10px, 2.5vw, 20px); border-bottom: 4px solid #F37121; border-radius: 10px 10px 0 0; "
          "font-size: clamp(15px, 3vw, 19px); line-height: 1.35;")
SUB = "display: block; margin-top: 10px; color: rgba(255, 255, 255, 0.78); font-size: clamp(11.5px, 2.2vw, 13px); line-height: 1.5; font-weight: normal;"
TH_ROW = ("background: #F7F3FB; color: #3a1467; text-align: left; vertical-align: top; padding: clamp(12px, 2.5vw, 18px) clamp(10px, 2.5vw, 20px); "
          "border-bottom: 1px solid #E2E8F0; font-size: clamp(12px, 2.3vw, 13.5px); line-height: 1.45;")
TD = ("vertical-align: top; padding: clamp(12px, 2.5vw, 18px) clamp(10px, 2.5vw, 20px); border-bottom: 1px solid #E2E8F0; "
      "font-size: clamp(13px, 2.4vw, 14.5px); line-height: 1.6;")
TD_LAST = ("background: #FCFAFE; vertical-align: top; padding: clamp(12px, 2.5vw, 18px) clamp(10px, 2.5vw, 20px); border-radius: 0 0 10px 10px; "
           "font-size: clamp(13px, 2.4vw, 14.5px); line-height: 1.6;")
GH = ("background: #3a1467; color: #ffffff; text-align: left; vertical-align: middle; padding: clamp(9px, 2vw, 14px) clamp(4px, 1.4vw, 14px); "
      "border-right: 1px solid #4e2a80; border-bottom: 2px solid #230c3e; font-size: clamp(9.5px, 2.1vw, 13px); line-height: 1.35;")
GR = ("background: #f7f3fb; color: #3a1467; text-align: left; vertical-align: top; padding: clamp(12px, 2.2vw, 16px) clamp(4px, 1.4vw, 14px); "
      "border-right: 1px solid #e4d9f0; border-bottom: 1px solid #e2e8f0; font-size: clamp(10.5px, 2.1vw, 13.5px); line-height: 1.4;")
GD = ("vertical-align: top; padding: clamp(12px, 2.2vw, 16px) clamp(4px, 1.4vw, 14px); border-right: 1px solid #e2e8f0; "
      "border-bottom: 1px solid #e2e8f0; font-size: clamp(10.5px, 2.1vw, 13px); line-height: 1.5;")
SUMMARY = ("cursor: pointer; background: #f7f3fb; color: #230c3e; padding: clamp(12px, 2.5vw, 18px) clamp(10px, 2.5vw, 20px); border-width: 1px 1px 3px; "
           "border-style: solid; border-color: #cbd5e0 #cbd5e0 #f37121; border-radius: 10px; font-size: clamp(15px, 3vw, 19px); line-height: 1.3;")
ITEM = ("vertical-align: top; padding: clamp(14px, 2.8vw, 20px) clamp(12px, 3vw, 22px); border-left: 6px solid #3A1467; border-bottom: 1px solid #E2E8F0;")
BTN = ("display: inline-block; text-decoration: none; padding: clamp(8px, 2vw, 11px) clamp(14px, 3.5vw, 22px); background-color: #3a1467; color: #ffffff; "
       "border-radius: 4px; font-family: LatoExtended, 'Source Sans Pro', sans-serif; font-size: clamp(13px, 2.6vw, 16px); border: 1px solid #230c3e; margin: 0 8px 8px 0;")
BTN2 = BTN.replace('background-color: #3a1467; color: #ffffff', 'background-color: #ffffff; color: #3a1467').replace('border: 1px solid #230c3e', 'border: 1px solid #3a1467')
PILL = ("display: inline-block; margin: 0 8px 8px 0; padding: clamp(6px, 1.6vw, 9px) clamp(12px, 3vw, 20px); background: #3A1467; color: #ffffff; "
        "border-radius: 999px; font-size: clamp(12px, 2.3vw, 13.5px); line-height: 1.3;")
VIDEO_BOX = ("border: 2px dashed #F37121; border-radius: 10px; background: #FFF8F2; padding: clamp(14px, 3vw, 22px); text-align: center; "
             "color: #a6480c; font-size: clamp(12px, 2.3vw, 13.5px); line-height: 1.5; margin: 10px 0 0 0;")
P_T = "margin: 0 0 6px 0; font-size: clamp(13px, 2.5vw, 15px); line-height: 1.5;"
P_D = "margin: 0 0 6px 0; color: #4a5568; font-size: clamp(11.5px, 2.2vw, 13px); line-height: 1.6;"
P_R = "margin: 0; color: #6b4a96; font-size: clamp(10.5px, 2vw, 11.5px); line-height: 1.5;"



def card(title, rows, sub=None, hero=False):
    """Tarjeta de la plantilla: encabezado morado con borde naranja y filas (rótulo opcional, contenido)."""
    head = f'<th style="{TH_HERO if hero else TH_SEC}" scope="col">{title}' + (f'<span style="{SUB}">{sub}</span>' if sub else '') + '</th>'
    body = []
    for i, (label, content) in enumerate(rows):
        if label:
            body.append(f'<tr><th style="{TH_ROW}" scope="row">{label}</th></tr>')
        body.append(f'<tr><td style="{TD_LAST if i == len(rows) - 1 else TD}">{content}</td></tr>')
    return f'<table style="{TABLE}"><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def grid(cols, rows, widths=None, first_th=True):
    widths = widths or [f'{100 / len(cols):.1f}%'] * len(cols)
    h = ''.join(f'<th style="width: {w}; {GH}" scope="col">{c}</th>' for c, w in zip(cols, widths))
    b = []
    for r in rows:
        cells = []
        for j, (c, w) in enumerate(zip(r, widths)):
            if j == 0 and first_th:
                cells.append(f'<th style="width: {w}; {GR}" scope="row">{c}</th>')
            else:
                cells.append(f'<td style="width: {w}; {GD}">{c}</td>')
        b.append('<tr>' + ''.join(cells) + '</tr>')
    return h, ''.join(b)


def grid_table(title, cols, rows, widths=None, sub=None):
    h, b = grid(cols, rows, widths)
    top = f'<tr><th style="{TH_SEC}" colspan="{len(cols)}" scope="col">{title}' + (f'<span style="{SUB}">{sub}</span>' if sub else '') + '</th></tr>'
    return f'<table style="{TABLE}"><thead>{top}<tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def details(summary, inner, hint='(clic para mostrar u ocultar)', sub=None):
    s = f'<span style="vertical-align: middle;">{summary}</span> <span style="font-size: clamp(11px, 2vw, 12px); color: #5a6472; vertical-align: middle;">{hint}</span>'
    if sub:
        s += f'<span style="display: block; margin-top: 6px; color: #5a6472; font-size: clamp(11.5px, 2.2vw, 12.5px); line-height: 1.5;">{sub}</span>'
    return f'<details style="max-width: 1000px; margin: 0 auto 28px auto; font-family: {FONT};"><summary style="{SUMMARY}">{s}</summary>{inner}</details>'


def rubric(evid, rows, ra=True):
    cols = ['Indicador', 'Receptivo', 'Resolutivo', 'Reflexivo', 'Crítico', 'Cocreativo']
    h, b = grid(cols, [[e(c) for c in r] for r in rows], ['20%'] + ['16%'] * 5)
    ra_txt = ''.join(f'<p style="margin: 0 0 6px 0;"><strong style="color: #3a1467;">{r[0]}:</strong> {e(r[1])}</p>' for r in DATA['ra']) if ra else ''
    top = (f'<tr><th style="{TH_ROW}" colspan="6" scope="row">Evidencia de desempeño (producto esperado)</th></tr>'
           f'<tr><td style="{TD}" colspan="6">{e(evid)}</td></tr>')
    if ra:
        top += f'<tr><th style="{TH_ROW}" colspan="6" scope="row">Resultados de aprendizaje</th></tr><tr><td style="{TD}" colspan="6">{ra_txt}</td></tr>'
    return (f'<table style="width: 100%; margin: 14px 0px 0px; border-collapse: separate; table-layout: fixed; border-radius: 10px; color: #2d3748; '
            f'line-height: 1.65; border: 1px solid #cbd5e0;"><tbody>{top}<tr>{h}</tr>{b}</tbody></table>')


def item(title, desc='', ref='', alt=False, extra=''):
    bg = '#FFFFFF' if alt else '#FCFAFE'
    return (f'<tr><td style="background: {bg}; {ITEM}"><p style="{P_T}">{title}</p>'
            + (f'<p style="{P_D}">{desc}</p>' if desc else '') + extra
            + (f'<p style="{P_R}">{ref}</p>' if ref else '') + '</td></tr>')


def item_card(title, items):
    head = (f'<th style="background: linear-gradient(135deg, #3A1467 0%, #230C3E 100%); color: #ffffff; text-align: left; vertical-align: top; '
            f'padding: clamp(16px, 3vw, 26px) clamp(12px, 3vw, 22px); border-bottom: 5px solid #F37121; border-radius: 12px 12px 0 0;" scope="col">'
            f'<span style="font-size: clamp(17px, 3.6vw, 23px);">{title}</span></th>')
    return (f'<table style="width: 100%; max-width: 1000px; margin: 0px auto 20px; border-collapse: separate; border-radius: 12px; '
            f'font-family: {FONT}; color: #2d3748; line-height: 1.65; border: 1px solid #cbd5e0;"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(items)}</tbody></table>')


def ra_html(solo=None):
    return ''.join(f'<p style="margin: 0 0 6px 0;"><strong style="color: #3a1467;">{r[0]}:</strong> {e(r[1])}</p>'
                   for r in DATA['ra'] if not solo or r[0].replace(' ', '') in [x.replace(' ', '') for x in solo])


def video_box(v):
    es, en = VIDEO.get(v, (v, v))
    vf = video_files(v)
    if vf:
        out = ''
        for lang, ((mp4, _), jpg) in vf.items():
            poster = f' poster="{file_ref(jpg[0], "abrir")}"' if jpg else ''
            out += (f'<p style="margin: 10px 0 6px 0;"><video style="width: 100%; max-width: 760px; border-radius: 8px; background: #000;" '
                    f'controls="controls" preload="none"{poster} src="{file_ref(mp4, "abrir")}"></video></p>'
                    f'<p style="{P_R}">«{e(es if lang == "es" else en)}» · {"en español" if lang == "es" else "en inglés"} · '
                    f'<a href="{file_ref(mp4)}">Abrir el video</a> · <a href="{file_ref(mp4, "bajar")}">Descargar</a></p>')
        return out
    return (f'<div style="{VIDEO_BOX}"><strong>🎬 Video {v} · {e(es)}</strong><br>'
            f'<span style="color: #6b4a96;">disponible próximamente en este espacio</span></div>')


def nav():
    """Barra de navegación del curso (va arriba en todas las páginas generadas)."""
    b = [('Presentación', T['presentacion'])] + [(f'Momento {M["n"]}', MOM[M['n']]) for M in DATA['momentos']]
    b += [('Aula interactiva', PAGES['aula']['id']), ('Materiales', PAGES['materiales']['id'])]
    if T.get('clases'):
        b.append(('Clases grabadas', T['clases']))
    st = ("display: inline-block; text-decoration: none; margin: 3px; padding: 6px 12px; border: 1px solid #3a1467; border-radius: 999px; "
          "color: #3a1467; background: #ffffff; font-size: clamp(12px, 2.3vw, 13.5px); font-family: LatoExtended, 'Source Sans Pro', sans-serif;")
    return (f'<p style="max-width: 1000px; margin: 0 auto 22px auto; text-align: center;">'
            + ''.join(f'<a style="{st}" href="{page_ref(i)}">{x}</a>' for x, i in b if i) + '</p>')


def link(href, text, cls=BTN, blank=False):
    t = ' target="_blank" rel="noopener"' if blank else ''
    return f'<a style="{cls}" href="{href}"{t}>{text}</a>'


def wrap_page(title, key, body, home, published=True):
    return (f'<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n<title>{e(title)}</title>\n'
            f'<meta name="identifier" content="{key}"/>\n<meta name="editing_roles" content="teachers"/>\n'
            f'<meta name="workflow_state" content="{"active" if published else "unpublished"}"/>\n<meta name="editor_type" content="rce"/>\n'
            f'</head>\n<body>\n{home}\n{body}\n</body>\n</html>\n')


def ul(xs, style='margin: 0; padding-left: 22px;'):
    return f'<ul style="{style}">' + ''.join(f'<li>{x}</li>' for x in xs) + '</ul>'


def ddmm(d):
    return d[:5]


def horas(s, k, defecto=''):
    h = (s.get('horas') or {}).get(k)
    return f' ({h} h)' if h else defecto


def lista(x):
    """Texto o lista de textos del sílabo → HTML."""
    if isinstance(x, (list, tuple)):
        return ul([e(i) for i in x])
    return e(x or '')


# ───────────────────────── Páginas ─────────────────────────
def reemplazar(t, viejo, nuevo, que, n=1):
    if viejo not in t:
        aviso(f'Presentación: no se encontró el bloque «{que}» de la plantilla; revísalo a mano en Canvas.')
        return t
    return t.replace(viejo, nuevo, n)


def presentacion(tpl: str) -> str:
    """Rellena la plantilla de Presentación con el sílabo (mismo diseño, mismos bloques)."""
    t, D = tpl, DATA
    m = re.search(r'(Bienvenidos al Proyecto Formativo.*?<p[^>]*>)(.*?)(</p>)', t, re.S)
    bienvenida = D['curso'].get('bienvenida')
    if m and bienvenida:
        t = t[:m.start(2)] + bienvenida + t[m.end(2):]
    elif bienvenida:
        aviso('Presentación: no se encontró el párrafo de bienvenida de la plantilla.')
    # Resultados de aprendizaje: tantas filas como RA tenga el sílabo (la plantilla trae cuatro)
    filas = list(re.finditer(r'<tr>\s*<th[^>]*scope="row">RA \d+</th>.*?</tr>', t, re.S))
    if filas:
        modelo = filas[0].group(0)
        nuevas = []
        for r in D['ra']:
            f = re.sub(r'>RA \d+</th>', f'>{e(r[0])}</th>', modelo, count=1)
            f = f.replace('Copiar pegar del sílabo', e(r[1]), 1).replace('Copiar pegar del sílabo', e(r[2] if len(r) > 2 else ''), 1)
            nuevas.append(f)
        t = t[:filas[0].start()] + '\n'.join(nuevas) + t[filas[-1].end():]
    else:
        aviso('Presentación: no se encontró la tabla de resultados de aprendizaje de la plantilla.')
    reps = [e(D['competencia_perfil']), e(D['competencia_pf']), e(D['contribucion']),
            '<br><br>'.join(e(p) for p in ([D['problema']] if isinstance(D['problema'], str) else D['problema'])),
            e(D['reto']), e(D.get('pis') or 'No aplica en este período.'), e(D.get('aporte_pis') or 'No aplica en este período.')]
    n = t.count('Copiar pegar del sílabo')
    if n != len(reps):
        aviso(f'Presentación: la plantilla tiene {n} campos «Copiar pegar del sílabo» y se esperaban {len(reps)}; revisa el orden en Canvas.')
    for r in reps[:n]:
        t = t.replace('Copiar pegar del sílabo', r, 1)
    # Metacompetencia: la elegida en el sílabo, resaltada
    t = t.replace('<p>(Seleccionar la metacompetencia que se aborde con mayor profundidad en el PF y cuyo logro pueda ser demostrado mediante evidencias)</p>',
                  '<p style="margin: 0 0 8px 0;">Metacompetencia que el PF aborda con mayor profundidad (sílabo):</p>')
    a, b = t.find('Metacompetencia transversal'), t.find('Habilidades blandas')
    if 0 <= a < b:
        hallada = False
        for li in re.findall(r'<li>([^<]*)</li>', t[a:b]):
            if li.strip().lower() == D['metacompetencia'].strip().lower():
                t = t.replace(f'<li>{li}</li>', f'<li><strong style="color: #3a1467;">✔ {li}</strong></li>', 1)
                hallada = True
            else:
                t = t.replace(f'<li>{li}</li>', f'<li style="color: #a0aec0;">{li}</li>', 1)
        if not hallada:
            aviso(f'Presentación: la metacompetencia «{D["metacompetencia"]}» no coincide con ninguna de la lista institucional.')
    t = t.replace('(Seleccionar a partir de la tabla de metacompetencias asociadas a las habilidades blandas.)', ul([e(h) for h in D['habilidades']]))
    a = t.find('<ul>', t.find('Ejes transversales'))
    if a > 0 and D.get('ejes'):
        b = t.find('</ul>', a) + 5
        ejes = ''.join(f'<p style="margin: 0 0 10px 0;"><strong style="color: #3a1467;">{e(k)}.</strong> {e(v)}</p>' for k, v in D['ejes'])
        t = t[:a] + ejes + t[b:]
    # Metodología: la del sílabo (la primera es la principal)
    i = t.find('Metodología activa')
    a = t.find('<p style="margin: 0;">', i) if i > 0 else -1
    if a > 0:
        b = t.find('</p>', a) + 4
        t = t[:a] + '<p style="margin: 0;">' + ' '.join(f'<span style="{PILL}">{e(x)}</span>' for x in D['metodologias'][:1]) + '</p>' + t[b:]
        t = t.replace('<p style="margin: 0 0 10px 0;">(metodologías complementarias propuestas por el docente)</p>',
                      '<p style="margin: 0 0 10px 0;">Metodologías complementarias (sílabo):</p>')
        a = t.find('<ul style="margin: 0; padding-left: 22px;">', t.find('Metodología activa'))
        if a > 0:
            b = t.find('</ul>', a) + 5
            t = t[:a] + ul([e(x) for x in D['metodologias'][1:]]) + t[b:]
        # Evaluación (bloque nuevo, después de la metodología y antes del perfil docente)
        ms = [f'<strong>Momento {M["n"]}</strong> ({M["fechas"]}): {e(M["evidencia"])}' for M in D['momentos']]
        eva = details('Evaluación', card('Cómo se evalúa', [
            (None, '<p style="margin: 0 0 10px 0;">La evaluación es <strong>socioformativa</strong>: se valoran evidencias de desempeño (productos) con '
                   '<strong>rúbricas</strong> que conoces desde el inicio, con cinco niveles de dominio (receptivo, resolutivo, reflexivo, crítico y '
                   'cocreativo), retroalimentación y oportunidad de mejora.</p>' + ul(ms)),
            ('Producto final del PF', e(D['producto_final'])),
        ]) + (details('Rúbrica del producto final del PF', rubric(D['producto_final'], D['rubrica_final'], ra=False), hint='(clic)') if D.get('rubrica_final') else ''),
            sub='Momentos, evidencias y rúbricas del sílabo.')
        j = t.find('<details', t.find('Metodología activa'))
        if j > 0:
            t = t[:j] + eva + t[j:]
    # Perfil docente (el teléfono no se publica: queda el marcador de la plantilla para que el docente decida)
    doc = D['docente']
    t = t.replace('Nombre del docente</strong>', f'{e(doc["nombre"])}</strong>')
    desc = '. '.join(e(x) for x in [doc.get('grado')] + list(doc.get('posgrado') or []) if x)
    t = re.sub(r'(<p[^>]*>)Descripción del docente(</p>)', lambda m: m.group(1) + desc + ('.' if desc else '') + m.group(2), t, count=1)
    if doc.get('email'):
        t = t.replace('<br>correo@indoamerica.edu.ec</p>', f'<br><a href="mailto:{doc["email"]}">{doc["email"]}</a></p>')
    if doc.get('orcid'):
        t = re.sub(r'<a class="inline_disabled" href="https://orcid.org/[\d-]+" target="_blank">\s*</a>https://orcid.org/</p>',
                   f'<a class="inline_disabled" href="https://orcid.org/{doc["orcid"]}" target="_blank">https://orcid.org/{doc["orcid"]}</a></p>', t)
    # Sílabo del curso: la copia publicada (sin datos personales)
    if SILABO_PDF:
        t = re.sub(r'\$IMS-CC-FILEBASE\$/Multimedia%20cargada/S%C3%ADlabo\.pdf\?canvas_=1&amp;canvas_qs_wrap=1', lambda m: file_ref(f'{CARPETA}/{SILABO_PDF.name}'), t)
    i = t.find('</table>') + len('</table>')
    t = t[:i] + '\n' + nav() + t[i:]
    if 'Copiar pegar del sílabo' in t:
        aviso('Presentación: quedaron campos «Copiar pegar del sílabo» sin llenar.')
    return t


def home_button(tpl_page: str) -> str:
    m = re.search(r'<body>\s*(<table.*?</table>)', tpl_page, re.S)
    return m.group(1) if m else ''


def momento_page(M):
    n = M['n']
    rows = []
    for s in M['sesiones']:
        p = plan(M, s)
        key = f'm{n}-sesion-{s["n"]}'
        ses = (f'<a href="{page_ref(PAGES[key]["id"])}"><strong>Sesión {s["n"]}</strong></a>'
               f'<span style="display: block; margin-top: 4px; color: #4a5568; font-size: clamp(10px, 2vw, 12.5px); line-height: 1.45;">'
               f'Semana {SEMANA[(n, s["n"])]}<br>{ddmm(s["desde"])}–{ddmm(s["hasta"])}<br>{e(p["tema"])}</span>')
        rows.append([ses, lista(s.get('docente')), lista(s.get('autonomo')), lista(s.get('practico')), lista(s.get('contenidos')),
                     '<span style="color: #a0aec0;">(Pegar enlace)</span>'])
    a, _, b = M['fechas'].partition(' al ')
    sem = [SEMANA[(n, s['n'])] for s in M['sesiones']]
    hero = card(f'Momento {n}: {e(M["titulo"])}', [('Resultado(s) de aprendizaje (RA)', ra_html(M.get('ra')))],
                sub=f'Fecha inicio: {a} · Fecha fin: {b} · Semanas {min(sem)}–{max(sem)}', hero=True)
    s0 = M['sesiones'][0]
    tabla = grid_table('Evidencias de desempeño (producto esperado):',
                       ['Sesión', 'Actividades en contacto con el docente' + horas(s0, 'docente'), 'Actividades de trabajo autónomo' + horas(s0, 'autonomo'),
                        'Actividades práctico-experimentales' + horas(s0, 'practico'), 'Contenidos', 'Enlace de clase'],
                       rows, ['15%', '19%', '17%', '20%', '17%', '12%'], sub=e(M['evidencia']))
    act = link(f'$CANVAS_OBJECT_REFERENCE$/assignments/{ACT[n]}', f'Actividad {n}: entrega de la evidencia del momento')
    aula = link(page_ref(PAGES['aula']['id']), 'Abrir el aula interactiva', BTN2)
    filas = []
    if M.get('recursos'):
        filas.append(('Recursos para el aprendizaje', lista(M['recursos'])))
    if M.get('ia'):
        filas.append(('Política de gobernanza crítica y ética de la IA', lista(M['ia'])))
    extra = card('Recursos y política de IA del momento', filas + [(None, act + aula)])
    rub = details('Rúbrica de evaluación de la evidencia de desempeño del Momento', rubric(M['evidencia'], M['rubrica'])) if M.get('rubrica') else ''
    return hero + tabla + rub + extra


def momento_extra(n):
    """La portada institucional tiene botones para más momentos de los que usa este sílabo: esas páginas remiten a los que sí existen."""
    ms = DATA['momentos']
    return card(f'Momento {n}', [
        (None, f'<p style="margin: 0 0 12px 0;">En este período, el sílabo organiza el proyecto formativo en <strong>{len(ms)} momento(s)</strong>. '
               'Todo el contenido está en:</p><p style="margin: 0;">'
               + ''.join(link(page_ref(MOM[M['n']]), f'Momento {M["n"]}: {e(M["titulo"])}') for M in ms) + '</p>'
               f'<p style="margin: 6px 0 0 0;">{link(page_ref(PAGES["aula"]["id"]), "Aula interactiva", BTN2)}'
               f'{link(page_ref(PAGES["materiales"]["id"]), "Materiales del curso", BTN2)}</p>')],
        sub=' · '.join(f'Momento {M["n"]}: {M["fechas"]}' for M in ms), hero=True)


def aula_cards(p):
    out = ''
    for n in p['u']:
        u = UNIDAD[n]
        pasos = []
        vids = ', '.join(f'{v} ({e(VIDEO[v][0])})' for v in p['v'] if v.startswith(f'V{n}.'))
        if tiene(n, 'preparacion'):
            pasos.append('<strong>Antes de clase</strong>: ' + (f'videos {vids} y ' if vids else '') + 'la preparación de la unidad.')
        if tiene(n, 'presentacion'):
            pasos.append(f'<strong>Presentación P{n}</strong>: la de la clase (con las animaciones en vivo).')
        ani = [a for a in p['an'] if a in [x['id'] for x in u.get('anims', [])]]
        if ani:
            pasos.append('<strong>Animaciones</strong>:<ul style="margin: 4px 0 0 0; padding-left: 20px;">'
                         + ''.join(f'<li><strong>{a}</strong> · {e(ANIM[a])}</li>' for a in ani) + '</ul>')
        if tiene(n, 'manual'):
            pasos.append(f'<strong>Manual M{n}</strong>' + (f': {e(p["man"])}.' if p['man'] else ': lectura de la unidad.'))
        if sub_practica(n):
            pasos.append(f'<strong>{e(PRAC)} {e(u.get("lab") or "")}</strong>: la actividad práctico-experimental, con su desafío con IA.')
        if tiene(n, 'quiz'):
            pasos.append(f'<strong>Cuestionario Q{n}</strong> para comprobar lo aprendido.')
        out += (f'<p style="margin: 0 0 8px 0;">En el aula interactiva, abre la <strong>Unidad {n}: {e(u["title"]["es"])}</strong>:</p>' + ul(pasos))
    return out + f'<p style="margin: 12px 0 0 0;">{link(page_ref(PAGES["aula"]["id"]), "Abrir el aula interactiva", BTN2)}</p>'


def sesion_page(M, s):
    n = M['n']
    p = plan(M, s)
    rec = PAGES[f'm{n}-recursos-{s["n"]}']['id']
    sub = (f'Momento {n} · Semana {SEMANA[(n, s["n"])]} · del {s["desde"]} al {s["hasta"]}'
           + (f' · Unidad {", ".join(map(str, p["u"]))} del aula' if p['u'] else ''))
    filas = [(f'Actividades en contacto con el docente{horas(s, "docente")}', lista(s.get('docente'))),
             (f'Actividades práctico-experimentales{horas(s, "practico")}', lista(s.get('practico'))),
             (f'Actividades de trabajo autónomo{horas(s, "autonomo")}', lista(s.get('autonomo'))),
             ('Contenidos', lista(s.get('contenidos')))]
    hero = card(f'Sesión {s["n"]}: {e(p["tema"])}', [f for f in filas if f[1]], sub=sub, hero=True)
    if p['u']:
        aula = card('En el aula interactiva', [(None, aula_cards(p))])
    elif p['repaso']:
        aula = card('Preparación de la evaluación', [(None,
            '<p style="margin: 0 0 8px 0;">Repasa en el aula interactiva, unidad por unidad:</p>'
            + ul([f'Unidad {k}: {e(UNIDAD[k]["title"]["es"])} — resumen, cuestionario y práctica.' for k in p['repaso']])
            + f'<p style="margin: 12px 0 0 0;">{link(page_ref(PAGES["aula"]["id"]), "Abrir el aula interactiva", BTN2)}</p>')])
    else:
        aula = ''
    recursos = card('Recursos de aprendizaje', [(None,
        '<p style="margin: 0 0 10px 0;">Aquí encontrarás el material de estudio y los recursos multimedia que necesitas para desarrollar las actividades de esta sesión.</p>'
        f'<p style="margin: 0;"><a href="{page_ref(rec)}"><strong>Acceder a los recursos de la sesión</strong></a></p>')])
    ia = card('Política de gobernanza crítica y ética de la IA', [(None,
        (f'<p style="margin: 0 0 10px 0;">{lista(M["ia"])}</p>' if M.get('ia') else '')
        + '<p style="margin: 0;">Cuando una actividad permite IA generativa, su uso se <strong>declara</strong>: qué herramienta usaste, para qué y '
          'cómo verificaste el resultado. Se evalúa que puedas explicar y comprobar cada decisión.</p>')])
    return hero + aula + recursos + ia


def recursos_page(M, s):
    n = M['n']
    p = plan(M, s)
    hero = card(f'Recursos de aprendizaje · Sesión {s["n"]}', [(None,
        f'<p style="margin: 0;"><a href="{page_ref(PAGES[f"m{n}-sesion-{s["n"]}"]["id"])}">← Volver a la sesión {s["n"]}</a></p>')],
        sub=f'{e(p["tema"])} · Semana {SEMANA[(n, s["n"])]}', hero=True)
    autor = f'{e(DATA["docente"]["nombre"])} ({DATA["curso"].get("inicio", "")[-4:]}). <em>Aula interactiva de {e(NOMBRE)}</em>. Universidad Tecnológica Indoamérica.'
    mat, alt = [], False
    for k in (p['u'] or p['repaso']):
        for path, title, _ in pdfs(k):
            what = {'Man': 'Lectura de la unidad' + (f' ({e(p["man"])}).' if p['man'] and p['u'] else '.'),
                    'Pre': 'Las diapositivas de la clase, para repasar y anotar.'}.get(title[:3], 'La guía de la actividad práctico-experimental, con su rúbrica y su desafío con IA.')
            en = path.replace('.pdf', '.en.pdf')
            otro = f' · <a href="{file_ref(en)}">English version</a>' if any(en == x[0] for x in pdfs(k, '.en')) and len(IDIOMAS) > 1 else ''
            mat.append(item(f'<a href="{file_ref(path)}"><strong>{title}</strong> · {e(UNIDAD[k]["title"]["es"])} (PDF)</a>{otro}', what, autor, alt))
            alt = not alt
    for g in [g for g in DATA.get('practicas', []) if g.get('momento') == n and g.get('sesion') == s['n'] and g.get('archivo')]:
        mat.append(item(f'<a href="{file_ref(f"{CARPETA}/guias/{guia_nombre(g)}")}"><strong>Guía práctica {e(g["id"])}</strong> · {e(g["titulo"])}</a>',
                        'Guía original de la práctica entregada por el docente.', '', alt))
        alt = not alt
    if DATA.get('bibliografia'):
        mat.append(item('Bibliografía básica del sílabo (Biblioteca Virtual UTI)',
                        'Para profundizar en los temas de la sesión. Ingrese con sus credenciales institucionales desde la Biblioteca Virtual.',
                        '<br>'.join(f'{b} ' + (f'<a href="{e(u)}" target="_blank" rel="noopener">Acceder</a>' if u else '') for b, u in DATA['bibliografia']), alt))
    multi = []
    for v in p['v']:
        multi.append(item(f'<strong>Video {v} · {e(VIDEO[v][0])}</strong>',
                          'Míralo antes de la clase y anota las ideas centrales; la sesión parte de ellas.',
                          'Video generado con IA a partir del manual y la práctica de la unidad, y revisado por el docente.', extra=video_box(v)))
    for k in p['u']:
        ani = [a for a in p['an'] if a in [x['id'] for x in UNIDAD[k].get('anims', [])]]
        multi.append(item(f'<strong>Aula interactiva · Unidad {k}</strong>',
                          'Presentación interactiva' + (', animaciones con recorrido guiado (' + ', '.join(f'{a} {e(ANIM[a])}' for a in ani) + ')' if ani else '') + ' y cuestionario.',
                          'En el aula: menú de la unidad → Presentación, Animaciones y Cuestionario.', True,
                          extra=f'<p style="margin: 8px 0;">{link(page_ref(PAGES["aula"]["id"]), "Abrir el aula interactiva")}</p>'))
    return hero + (item_card('Material de estudio', mat) if mat else '') + (item_card('Recurso multimedia', multi) if multi else '')


def aula_page():
    f = f'{CARPETA}/{ARCHIVO}.html'
    na = len(ANIM)
    botones = (link(file_ref(f, 'abrir'), 'Abrir el aula en una pestaña nueva', blank=True)
               + link(file_ref(f, 'bajar'), 'Descargar el aula (un solo archivo, sin conexión)', BTN2))
    intro = card(f'Aula interactiva de {e(NOMBRE)}', [
        (None, f'<p style="margin: 0 0 10px 0;">Todo el curso en un solo archivo: <strong>{len(UNIDAD)} unidades</strong> con resumen, «Antes de clase», '
               f'presentación, {f"<strong>{na} animaciones</strong> con recorrido guiado, " if na else ""}manual, práctica con desafío de IA, '
               'cuestionario y bibliografía. En español e inglés.</p>'
               f'<p style="margin: 0 0 10px 0;">{botones}</p>'),
        ('Para tener en cuenta', ul([
            'Funciona sin conexión: descárgalo y ábrelo con Chrome, Edge o Firefox; tu progreso queda guardado en ese navegador.',
            'Los botones «Descargar en PDF» abren la impresión del navegador: elige «Guardar como PDF». Los PDF de todas las unidades están en la página Materiales y en los Recursos de aprendizaje de cada sesión.',
            'Los videos están en la página Materiales y en los Recursos de aprendizaje de su sesión (dentro del aula verás su portada).']))],
        sub='Presentaciones, animaciones, manuales, prácticas y cuestionarios', hero=True)
    marco = (f'<p style="max-width: 1000px; margin: 0 auto 10px auto; font-family: {FONT}; color: #4a5568; font-size: 13px;">Vista previa integrada '
             '(para trabajar con comodidad, ábrela en una pestaña nueva):</p>'
             f'<p style="max-width: 1000px; margin: 0 auto 28px auto;"><iframe style="width: 100%; height: 820px; border: 1px solid #cbd5e0; border-radius: 10px;" '
             f'title="Aula interactiva" src="{file_ref(f, "abrir")}" allowfullscreen="allowfullscreen" allow="fullscreen"></iframe></p>')
    return intro + marco


def materiales_page():
    f = f'{CARPETA}/{ARCHIVO}.html'
    top = card('Materiales del curso', [
        (None, '<p style="margin: 0 0 10px 0;">Todo el material del curso en un solo lugar: el aula interactiva, el sílabo y, por unidad, '
               'el manual, la presentación y la práctica en PDF, y los videos.</p>'
               f'<p style="margin: 0;">{link(page_ref(PAGES["aula"]["id"]), "Aula interactiva")}'
               f'{link(file_ref(f, "bajar"), "Descargar el aula (un solo archivo)", BTN2)}'
               + (link(file_ref(f"{CARPETA}/{SILABO_PDF.name}"), "Sílabo del curso (PDF)", BTN2) if SILABO_PDF else '') + '</p>'),
        ('Dónde están los archivos', f'También están en <strong>Archivos → {CARPETA}</strong>.')],
        sub='Aula interactiva, sílabo, PDF y videos', hero=True)
    rows = []
    for n, u in sorted(UNIDAD.items()):
        cells = []
        for k in range(3):
            langs = []
            for ext, lab in IDIOMAS:
                ps = pdfs(n, ext)
                tipo = ('Manual', 'Presentación', PRAC)[k]
                hit = next((x for x in ps if x[1].startswith(tipo)), None)
                if hit:
                    langs.append(f'<a href="{file_ref(hit[0])}"><strong>{lab}</strong></a>' if lab == 'ES' else f'<a href="{file_ref(hit[0])}">{lab}</a>')
            cells.append(' · '.join(langs) or '—')
        vids = []
        for v in sorted(x for x in VIDEO if x.startswith(f'V{n}.')):
            vf = video_files(v)
            if vf:
                vids.append(f'{v} · {e(VIDEO[v][0])}: ' + ' · '.join(f'<a href="{file_ref(x[0][0])}">{l.upper()}</a>' for l, x in vf.items()))
            else:
                vids.append(f'<span style="color: #a0aec0;">{v} · {e(VIDEO[v][0])} (próximamente)</span>')
        ses = [f'<a href="{page_ref(PAGES[f"m{M["n"]}-recursos-{s["n"]}"]["id"])}">M{M["n"]} S{s["n"]}</a>' for M, s, _ in sesiones() if n in plan(M, s)['u']]
        rows.append([f'<strong>Unidad {n}</strong><br>{e(u["title"]["es"])}' + (f'<br><span style="color: #4a5568;">Recursos: {", ".join(ses)}</span>' if ses else ''),
                     *cells, '<br>'.join(vids) or '—'])
    tabla = grid_table('Material por unidad', ['Unidad', 'Manual (PDF)', 'Presentación (PDF)', f'{PRAC} (PDF)', 'Videos'],
                       rows, ['24%', '16%', '16%', '16%', '28%'], sub='ES = español · EN = inglés')
    return top + tabla


def guia_page():
    vids = []
    for M, s, _ in sesiones():
        for v in plan(M, s)['v']:
            ok = bool(video_files(v))
            vids.append([v, e(VIDEO[v][0]), f'Momento {M["n"]} · Recursos de aprendizaje · Sesión {s["n"]}',
                         f'videos/unidad-{v[1:].split(".")[0]}/{v}.es.mp4 / .en.mp4', '✅ ya en Canvas' if ok else '⏳ subir cuando esté'])
    h, b = grid(['Video', 'Título', 'Página de Canvas', 'Archivo', 'Estado'], vids, ['8%', '27%', '27%', '26%', '12%'])
    pasos = card('Guía del docente (página oculta a los estudiantes)', [
        ('1 · Subir un video', ul([
            'Los videos listos al generar el paquete ya vienen incrustados (tabla de abajo, «ya en Canvas»). Para los demás:',
            'Abre la página «Recursos de aprendizaje» de la sesión → <strong>Editar</strong>.',
            'Haz clic dentro del recuadro naranja punteado del video, borra su texto y usa <strong>Insertar → Medios → Cargar o grabar medios</strong> con el MP4.',
            'Guarda. Los MP4 listos están en la carpeta <code>videos/unidad-N/</code> del proyecto (ya llevan portada y cierre UTI).'])),
        ('2 · Actualizar el aula interactiva', ul([
            f'En Canvas: <strong>Archivos → {CARPETA} → Cargar</strong> el nuevo <code>{ARCHIVO}.html</code> (carpeta <code>autonomo/</code> del proyecto) y elige <strong>Reemplazar</strong>. '
            'Con el mismo nombre y carpeta, los enlaces y la vista integrada siguen funcionando.',
            'Para otra importación, prueba primero en un curso de ensayo y revisa duplicados; conserva el export original y usa las páginas para pegar cuando corresponda.',
            f'La edición docente (<code>{ARCHIVO}-profesor.html</code>) no se sube a Canvas.'])),
        ('3 · Antes de publicar', ul([
            'Enlaces de clase: columna «Enlace de clase» de las páginas de cada momento, y «Clases grabadas».',
            'Las actividades y las prácticas están sin publicar: revisa fechas, puntajes y rúbricas, y publícalas cuando corresponda.',
            'Perfil docente: falta la foto (Presentación → Perfil docente) y el teléfono, si quieres publicarlo.']))],
        sub='Videos, actualización del aula y pendientes', hero=True)
    tabla = f'<table style="{TABLE}"><thead><tr><th style="{TH_SEC}" colspan="5" scope="col">Videos por sesión</th></tr><tr>{h}</tr></thead><tbody>{b}</tbody></table>' if vids else ''
    return pasos + tabla


def clases_page():
    rows = [[f'{k}', f'M{M["n"]} · Sesión {s["n"]}: {e(plan(M, s)["tema"])}', f'{s["desde"]} al {s["hasta"]}',
             '<span style="color: #a0aec0;">Ver grabación (pegar enlace)</span>', '<span style="color: #a0aec0;">(Pegar enlace)</span>'] for M, s, k in sesiones()]
    return grid_table('Clases grabadas', ['Semana', 'Sesión y tema', 'Fecha', 'Grabación', 'Enlace de clase en caso de contingencia'],
                      rows, ['9%', '37%', '20%', '17%', '17%'])


def tarea_html(titulo, body, home):
    return (f'<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>\n<title>Assignment: {e(titulo)}</title>\n</head>\n'
            f'<body>\n{home}\n{body}\n</body>\n</html>\n')


def actividad(M, home):
    n = M['n']
    prob = DATA['problema'] if isinstance(DATA['problema'], str) else DATA['problema'][-1]
    filas = [('Resultados de aprendizaje relacionados', ra_html(M.get('ra')))]
    if M.get('proposito'):
        filas.append(('¿Para qué realizas esta actividad?', lista(M['proposito'])))
    filas += [('Problema o reto del territorio', f'<p style="margin: 0 0 8px 0;">{e(prob)}</p><p style="margin: 0;"><strong>Reto:</strong> {e(DATA["reto"])}</p>'),
              ('Evidencia de desempeño (sílabo)', e(M['evidencia']))]
    if M.get('entregables'):
        filas.append(('Entregable de este momento', lista(M['entregables'])))
    filas.append(('Recursos que debes utilizar', ul(['Aula interactiva (manuales, prácticas y animaciones de las unidades del momento).',
                                                     'Recursos de aprendizaje de cada sesión del momento.', 'Bibliografía básica del sílabo (Biblioteca Virtual UTI).'])))
    if M.get('rubrica'):
        filas.append(('Evaluación', 'Rúbrica de la evidencia de desempeño del momento (niveles receptivo, resolutivo, reflexivo, crítico y cocreativo). '
                                    'Recibirás retroalimentación con logros y sugerencias, y podrás mejorar tu producto:' + rubric(M['evidencia'], M['rubrica'], ra=False)))
    filas.append(('Condiciones de entrega', lista(M.get('condiciones') or [
        'Fecha límite: la indica el docente en esta tarea.',
        'Uso de IA: según la política del momento, siempre con declaración (herramienta, para qué y cómo verificaste el resultado).'])))
    body = card(f'Actividad {n}: evidencia de desempeño del Momento {n}', filas, sub=f'Momento {n}: {e(M["titulo"])} · {M["fechas"]}', hero=True)
    return tarea_html(f'Actividad {n}', body, home)


def practica_tarea(g, home):
    u = UNIDAD.get(g.get('unidad'))
    filas = []
    if g.get('proposito'):
        filas.append(('¿Para qué realizas esta práctica?', lista(g['proposito'])))
    if g.get('ra'):
        filas.append(('Resultados de aprendizaje relacionados', ra_html(g['ra'])))
    if g.get('entregable'):
        filas.append(('Qué entregar', lista(g['entregable'])))
    donde = []
    if u and sub_practica(u['n']):
        donde.append(f'Aula interactiva → Unidad {u["n"]}: {e(u["title"]["es"])} → {e(PRAC)} {e(u.get("lab") or "")}. {link(page_ref(PAGES["aula"]["id"]), "Abrir el aula", BTN2)}')
        for path, title, _ in pdfs(u['n']):
            if not title.startswith(('Manual', 'Presentación')):
                donde.append(f'<a href="{file_ref(path)}">{title} en PDF</a>')
    if g.get('archivo'):
        donde.append(f'<a href="{file_ref(f"{CARPETA}/guias/{guia_nombre(g)}")}">Guía práctica original (documento del docente)</a>')
    if donde:
        filas.append(('Dónde está la guía', ul(donde)))
    filas.append(('Evaluación', lista(g.get('evaluacion') or 'Forma parte de las actividades práctico-experimentales del momento; se valora con la rúbrica de la evidencia del momento.')))
    filas.append(('Uso de IA', 'Permitido donde la guía lo indica (desafío con IA), siempre con declaración: herramienta, para qué y cómo verificaste el resultado.'))
    body = card(f'{e(PRAC)} {e(g["id"])} · {e(g["titulo"])}', filas,
                sub=(f'Unidad {u["n"]}: {e(u["title"]["es"])}' if u else f'Momento {g.get("momento", "")}'), hero=True)
    return tarea_html(f'{PRAC} {g["id"]}', body, home)


def pis_fill(t: str) -> str:
    ra = ''.join(f'<p style="margin: 0 0 6px 0;"><strong>{e(NOMBRE)} · {r[0]}:</strong> {e(r[1])}</p>' for r in DATA['ra'])
    t = t.replace('(Resultados de Aprendizaje oficiales de los Proyectos Formativos que aportan al PIS, señalando a qué asignatura pertenece cada uno)',
                  ra + '<p style="margin: 0; color: #4a5568;">(Agregar los RA de los demás proyectos formativos del PIS.)</p>')
    prob = DATA['problema'] if isinstance(DATA['problema'], str) else DATA['problema'][0]
    t = t.replace('(Contextualiza la situación real que abordará el equipo: dónde ocurre, a quiénes afecta, qué datos o antecedentes existen, qué Proyectos Formativos intervienen y por qué importa para el territorio)',
                  f'<strong>{e(DATA["pis"])}.</strong> {e(prob)}<br><br><strong>Aporte de {e(NOMBRE)}:</strong> {e(DATA.get("aporte_pis") or "")}')
    return t


# ───────────────────────── Ensamblado del paquete ─────────────────────────
PAGES = {}     # clave → {id, file, title, pub}   (páginas nuevas)
T = {}         # páginas de la plantilla: inicio, presentacion, clases → identificador
MOM = {}       # n → identificador de la página «Momento n» (de la plantilla o nuevo)
ACT = {}       # n → identificador de la tarea «Actividad n» (de la plantilla o nuevo)
SILABO_PDF = next(iter(sorted((HERE / 'fuentes').glob('*.pdf'))), None)


def module_item(ident, ctype, state, title, ref, pos, indent):
    return (f'      <item identifier="{ident}">\n        <content_type>{ctype}</content_type>\n        <workflow_state>{state}</workflow_state>\n'
            f'        <title>{e(title)}</title>\n        <identifierref>{ref}</identifierref>\n        <position>{pos}</position>\n'
            f'        <new_tab>false</new_tab>\n        <indent>{indent}</indent>\n        <link_settings_json>null</link_settings_json>\n      </item>\n')


def module(ident, title, state, pos, items):
    body = ''.join(module_item(*it, i + 1, ind) for i, (it, ind) in enumerate(items))
    return (f'  <module identifier="{ident}">\n    <title>{e(title)}</title>\n    <workflow_state>{state}</workflow_state>\n    <position>{pos}</position>\n'
            f'    <require_sequential_progress>false</require_sequential_progress>\n    <locked>false</locked>\n    <items>\n{body}    </items>\n  </module>\n')


def assignment_xml(ident, title, group, points, grading, pos, state='unpublished'):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<assignment identifier="{ident}" xmlns="http://canvas.instructure.com/xsd/cccv1p0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://canvas.instructure.com/xsd/cccv1p0 https://canvas.instructure.com/xsd/cccv1p0.xsd">
  <title>{e(title)}</title>
  <due_at/>
  <lock_at/>
  <unlock_at/>
  <module_locked>false</module_locked>
  <assignment_group_identifierref>{group}</assignment_group_identifierref>
  <workflow_state>{state}</workflow_state>
  <assignment_overrides>
  </assignment_overrides>
  <allowed_extensions></allowed_extensions>
  <has_group_category>false</has_group_category>
  <points_possible>{points}</points_possible>
  <grading_type>{grading}</grading_type>
  <all_day>false</all_day>
  <submission_types>online_upload</submission_types>
  <position>{pos}</position>
  <turnitin_enabled>false</turnitin_enabled>
  <vericite_enabled>false</vericite_enabled>
  <peer_review_count>0</peer_review_count>
  <peer_reviews>false</peer_reviews>
  <automatic_peer_reviews>false</automatic_peer_reviews>
  <anonymous_peer_reviews>false</anonymous_peer_reviews>
  <grade_group_students_individually>false</grade_group_students_individually>
  <freeze_on_copy>false</freeze_on_copy>
  <omit_from_final_grade>{"true" if grading == "not_graded" else "false"}</omit_from_final_grade>
  <hide_in_gradebook>false</hide_in_gradebook>
  <intra_group_peer_reviews>false</intra_group_peer_reviews>
  <only_visible_to_overrides>false</only_visible_to_overrides>
  <post_to_sis>false</post_to_sis>
  <moderated_grading>false</moderated_grading>
  <grader_count>0</grader_count>
  <grader_comments_visible_to_graders>true</grader_comments_visible_to_graders>
  <anonymous_grading>false</anonymous_grading>
  <graders_anonymous_to_graders>false</graders_anonymous_to_graders>
  <grader_names_visible_to_final_grader>true</grader_names_visible_to_final_grader>
  <anonymous_instructor_annotations>false</anonymous_instructor_annotations>
  <lockdown_browser_settings>{{"require_lockdown_browser":false}}</lockdown_browser_settings>
  <post_policy>
    <post_manually>false</post_manually>
  </post_policy>
</assignment>
'''


def descubrir(tmp: Path) -> dict:
    """Lee la plantilla (o el export del curso): páginas, módulos, tareas y grupos, por título. Nada de identificadores fijos."""
    W = tmp / 'wiki_content'
    d = dict(paginas={}, momentos={}, viejas=[], modulos=[], tareas={}, pis=[], grupos={})
    for f in sorted(W.glob('*.html')):
        t = f.read_text()
        ident = (re.search(r'<meta name="identifier" content="(\w+)"', t) or [None, None])[1]
        title = html.unescape((re.search(r'<title>(.*?)</title>', t, re.S) or [None, ''])[1]).strip()
        d['paginas'][f.stem] = (ident, title)
        low = title.lower()
        if (m := re.fullmatch(r'momento (\d+)', low)):
            d['momentos'][int(m.group(1))] = (ident, f.stem)
        elif low == 'inicio':
            T['inicio'], T['inicio_file'] = ident, f.stem
        elif low.startswith('presentaci'):
            T['presentacion'], T['presentacion_file'] = ident, f.stem
        elif low.startswith('clases grabadas'):
            T['clases'], T['clases_file'] = ident, f.stem
        elif re.fullmatch(r'(sesión|sesion|recursos de aprendizaje) \d+', low):
            d['viejas'].append(f.stem)
    mm = (tmp / 'course_settings/module_meta.xml').read_text()
    for m in re.finditer(r'  <module identifier="(\w+)">\s*<title>(.*?)</title>.*?</module>\n', mm, re.S):
        items = re.findall(r'<item identifier="(\w+)">\s*<content_type>([\w:]+)</content_type>\s*<workflow_state>\w+</workflow_state>\s*<title>(.*?)</title>\s*<identifierref>(\w+)</identifierref>', m.group(0), re.S)
        d['modulos'].append(dict(id=m.group(1), titulo=html.unescape(m.group(2)).strip(), xml=m.group(0), items=items))
    for f in sorted(tmp.glob('*/assignment_settings.xml')):
        x = f.read_text()
        title = html.unescape((re.search(r'<title>(.*?)</title>', x, re.S) or [None, ''])[1]).strip()
        page = next((p for p in f.parent.glob('*.html')), None)
        if (m := re.fullmatch(r'actividad (\d+)', title.lower())):
            d['tareas'][int(m.group(1))] = (f.parent.name, page)
        elif 'interdisciplinario' in title.lower():
            d['pis'].append(page)
    ag = (tmp / 'course_settings/assignment_groups.xml')
    if ag.exists():
        for m in re.finditer(r'<assignmentGroup identifier="(\w+)">\s*<title>(.*?)</title>', ag.read_text(), re.S):
            d['grupos'][html.unescape(m.group(2)).strip().lower()] = m.group(1)
    for k in ('inicio', 'presentacion'):
        if k not in T:
            sys.exit(f'La plantilla no tiene la página «{k}»: ¿es un export del curso con la plantilla institucional de la UTI?')
    return d


def pegar(htmltext: str, by_id: dict) -> str:
    """Versión para pegar en el editor HTML de una página que ya existe en el curso (enlaces absolutos al curso)."""
    body = re.search(r'<body>\s*(.*?)\s*</body>', htmltext, re.S).group(1)
    body = re.sub(r'\$WIKI_REFERENCE\$/pages/(g[0-9a-f]{32})', lambda m: f'/courses/{CURSO_ID}/pages/{by_id.get(m.group(1), m.group(1))}', body)
    body = re.sub(r'\$CANVAS_OBJECT_REFERENCE\$/assignments/g[0-9a-f]{32}', f'/courses/{CURSO_ID}/assignments', body)
    body = re.sub(r'\$IMS-CC-FILEBASE\$/([^"?]*)(\?[^"]*)?', lambda m: f'/courses/{CURSO_ID}/file_contents/course%20files/{m.group(1)}', body)
    return body + '\n'


def main() -> int:
    import subprocess
    if subprocess.run([sys.executable, str(HERE / 'validar_silabo.py')]).returncode:
        return 1
    aula_html = ROOT / 'autonomo' / f'{ARCHIVO}.html'
    if not aula_html.exists():
        sys.exit(f'Falta autonomo/{ARCHIVO}.html: corre python3 hub/build.py && python3 hub/tools/autonomo.py --sin-paquete')
    src = plantilla()
    with zipfile.ZipFile(src) as source_zip:
        if gid('mod-aula') in source_zip.read('course_settings/module_meta.xml').decode('utf-8'):
            sys.exit('El export ya contiene el aula generada por esta herramienta. Usa un export original anterior o la plantilla institucional y la vía pegar; no se admite regenerar desde un paquete ya generado.')
    tmp = Path(tempfile.mkdtemp(prefix='canvas-uti-'))
    with zipfile.ZipFile(src) as z:
        z.extractall(tmp)
    W = tmp / 'wiki_content'
    d = descubrir(tmp)
    inicio_antes = (W / f'{T["inicio_file"]}.html').read_bytes()

    # Identificadores: los de la plantilla donde existen; estables y nuevos donde no
    momentos = DATA['momentos']
    for M in momentos:
        MOM[M['n']] = d['momentos'][M['n']][0] if M['n'] in d['momentos'] else gid(f'momento-{M["n"]}')
        ACT[M['n']] = d['tareas'][M['n']][0] if M['n'] in d['tareas'] else gid(f'actividad-{M["n"]}')
    PAGES['aula'] = dict(id=gid('aula'), file='aula-interactiva', title='Aula interactiva', pub=True)
    PAGES['materiales'] = dict(id=gid('materiales'), file='materiales-del-curso', title='Materiales del curso', pub=True)
    PAGES['guia'] = dict(id=gid('guia'), file='guia-del-docente', title='Guía del docente (oculta)', pub=False)
    for M in momentos:
        for s in M['sesiones']:
            for kind in ('sesion', 'recursos'):
                k = f'm{M["n"]}-{kind}-{s["n"]}'
                PAGES[k] = dict(id=gid(k), file=k, title=f'M{M["n"]} Sesión {s["n"]}' if kind == 'sesion' else f'M{M["n"]} Recursos {s["n"]}', pub=True)
    modelo = next((W / f'{v}.html' for v in d['viejas'] if (W / f'{v}.html').exists()), W / f'{T["presentacion_file"]}.html')
    home = home_button(modelo.read_text()) + '\n' + nav()
    new_res = []

    # Presentación, momentos, clases grabadas
    pf = W / f'{T["presentacion_file"]}.html'
    pf.write_text(presentacion(pf.read_text()))
    for M in momentos:
        n = M['n']
        stem = d['momentos'][n][1] if n in d['momentos'] else f'momento-{n}-{CLAVE}'
        (W / f'{stem}.html').write_text(wrap_page(f'Momento {n}', MOM[n], momento_page(M), home))
        if n not in d['momentos']:
            new_res.append(f'    <resource identifier="{MOM[n]}" type="webcontent" href="wiki_content/{stem}.html">\n      <file href="wiki_content/{stem}.html"/>\n    </resource>\n')
            d['paginas'][stem] = (MOM[n], f'Momento {n}')
    usados = {M['n'] for M in momentos}
    for n, (ident, stem) in d['momentos'].items():
        if n not in usados:
            (W / f'{stem}.html').write_text(wrap_page(f'Momento {n}', ident, momento_extra(n), home))
    if T.get('clases'):
        (W / f'{T["clases_file"]}.html').write_text(wrap_page('Clases Grabadas', T['clases'], clases_page(), home))
    for v in d['viejas']:
        f = W / f'{v}.html'
        f.write_text(f.read_text().replace('<meta name="workflow_state" content="active"/>', '<meta name="workflow_state" content="unpublished"/>'))
    for M in momentos:
        for s in M['sesiones']:
            for kind, fn in (('sesion', sesion_page), ('recursos', recursos_page)):
                P = PAGES[f'm{M["n"]}-{kind}-{s["n"]}']
                (W / f'{P["file"]}.html').write_text(wrap_page(P['title'], P['id'], fn(M, s), home))
    for k, fn in (('aula', aula_page), ('materiales', materiales_page), ('guia', guia_page)):
        P = PAGES[k]
        (W / f'{P["file"]}.html').write_text(wrap_page(P['title'], P['id'], fn(), home, P['pub']))
    assert (W / f'{T["inicio_file"]}.html').read_bytes() == inicio_antes, 'La página Inicio no debe cambiar'

    # Tareas: Actividad N (evidencia de cada momento), PIS y prácticas
    g_act = d['grupos'].get('actividades') or next(iter(d['grupos'].values()), gid('grupo'))
    g_pra = d['grupos'].get('actividades práctico experimentales') or g_act
    for M in momentos:
        n = M['n']
        if n in d['tareas']:
            carpeta, page = d['tareas'][n]
            page.write_text(actividad(M, home))
            st = tmp / carpeta / 'assignment_settings.xml'
            st.write_text(re.sub(r'<title>.*?</title>', f'<title>Actividad {n} · Evidencia del Momento {n}</title>', st.read_text(), count=1, flags=re.S))
        else:
            dd = tmp / ACT[n]
            dd.mkdir()
            (dd / f'actividad-{n}.html').write_text(actividad(M, home))
            (dd / 'assignment_settings.xml').write_text(assignment_xml(ACT[n], f'Actividad {n} · Evidencia del Momento {n}', g_act, str(M.get('puntos', 0)), 'points' if M.get('puntos') else 'not_graded', n))
            new_res.append(f'    <resource identifier="{ACT[n]}" type="associatedcontent/imscc_xmlv1p1/learning-application-resource" href="{ACT[n]}/actividad-{n}.html">\n'
                           f'      <file href="{ACT[n]}/actividad-{n}.html"/>\n      <file href="{ACT[n]}/assignment_settings.xml"/>\n    </resource>\n')
    if DATA.get('pis'):
        for page in d['pis']:
            if page:
                page.write_text(pis_fill(page.read_text()))
    practicas = {}
    for k, g in enumerate(DATA.get('practicas', [])):
        ident = gid(f'practica-{g["id"]}')
        slug = re.sub(r'[^a-z0-9]+', '-', g['id'].lower()).strip('-')
        dd = tmp / ident
        dd.mkdir()
        (dd / f'practica-{slug}.html').write_text(practica_tarea(g, home))
        pts = g.get('puntos') or 0
        (dd / 'assignment_settings.xml').write_text(assignment_xml(ident, f'{PRAC} {g["id"]} · {g["titulo"]}', g_pra, f'{float(pts):.1f}',
                                                                   'points' if pts else 'not_graded', 20 + k))
        new_res.append(f'    <resource identifier="{ident}" type="associatedcontent/imscc_xmlv1p1/learning-application-resource" href="{ident}/practica-{slug}.html">\n'
                       f'      <file href="{ident}/practica-{slug}.html"/>\n      <file href="{ident}/assignment_settings.xml"/>\n    </resource>\n')
        practicas[g['id']] = ident

    # Archivos: aula en un solo archivo, sílabo público, PDF por unidad, videos y guías originales
    WR = tmp / 'web_resources'
    files = [(f'{CARPETA}/{ARCHIVO}.html', aula_html)]
    if SILABO_PDF:
        files.append((f'{CARPETA}/{SILABO_PDF.name}', SILABO_PDF))
    for n in sorted(UNIDAD):
        for ext, _ in IDIOMAS:
            files += [(p, s) for p, _, s in pdfs(n, ext)]
    for v in sorted(VIDEO):
        for (mp4, jpg) in video_files(v).values():
            files += [mp4] + ([jpg] if jpg else [])
    for g in DATA.get('practicas', []):
        if g.get('archivo'):
            f = (ROOT / g['archivo']).resolve()
            if not f.is_relative_to(ROOT.resolve()) or f.is_relative_to((ROOT / 'fuentes/privado').resolve()):
                sys.exit(f'Práctica {g["id"]}: la guía debe estar dentro del aula y fuera de fuentes/privado.')
            if f.exists():
                files.append((f'{CARPETA}/guias/{guia_nombre(g)}', f))
            else:
                aviso(f'Práctica {g["id"]}: no existe el archivo {g["archivo"]}')
    for rel, origen in dict(files).items():
        dst = WR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, dst)
        new_res.append(f'    <resource type="webcontent" identifier="{gid("file:" + rel)}" href="web_resources/{e(rel)}">\n      <file href="web_resources/{e(rel)}"/>\n    </resource>\n')
    for P in PAGES.values():
        new_res.append(f'    <resource identifier="{P["id"]}" type="webcontent" href="wiki_content/{P["file"]}.html">\n'
                       f'      <file href="wiki_content/{P["file"]}.html"/>\n    </resource>\n')
    man = (tmp / 'imsmanifest.xml').read_text()
    man = man.replace('  </resources>', ''.join(new_res) + '  </resources>')

    # Módulos
    old = (tmp / 'course_settings/module_meta.xml').read_text()
    por_titulo = {m['titulo'].lower(): m for m in d['modulos']}
    repos = lambda xml, pos, estado=None: re.sub(r'<position>\d+</position>\n    <require', f'<position>{pos}</position>\n    <require',
                                                xml if not estado else xml.replace('<workflow_state>active</workflow_state>\n    <position>', f'<workflow_state>{estado}</workflow_state>\n    <position>', 1), count=1)
    mods, usados_mod, pos = [], set(), 1
    pres = next((m for m in d['modulos'] if m['titulo'].lower().startswith('presentaci')), None)
    if pres:
        mods.append(repos(pres['xml'], pos)); usados_mod.add(pres['id']); pos += 1
    mods.append(module(gid('mod-aula'), 'Aula interactiva y materiales', 'active', pos, [
        ((gid('it-aula'), 'WikiPage', 'active', 'Aula interactiva (abrir o descargar)', PAGES['aula']['id']), 0),
        ((gid('it-materiales'), 'WikiPage', 'active', 'Materiales del curso: PDF por unidad y videos', PAGES['materiales']['id']), 0),
        ((gid('it-aula-file'), 'Attachment', 'active', f'{ARCHIVO}.html (archivo del aula)', gid(f'file:{CARPETA}/{ARCHIVO}.html')), 1)]
        + ([((gid('it-silabo-file'), 'Attachment', 'active', 'Sílabo del curso (PDF)', gid(f'file:{CARPETA}/{SILABO_PDF.name}')), 1)] if SILABO_PDF else [])))
    pos += 1
    for M in momentos:
        n = M['n']
        tm = por_titulo.get(f'momento {n}')
        item_id = lambda ref, clave: next((i[0] for i in (tm['items'] if tm else []) if i[3] == ref), gid(clave))
        its = [((item_id(MOM[n], f'it-m{n}'), 'WikiPage', 'active', f'Momento {n}: {M["titulo"]}', MOM[n]), 0)]
        for s in M['sesiones']:
            p = plan(M, s)
            its.append(((gid(f'it-m{n}-s{s["n"]}'), 'WikiPage', 'active', f'Sesión {s["n"]} · {p["tema"]} ({ddmm(s["desde"])}–{ddmm(s["hasta"])})', PAGES[f'm{n}-sesion-{s["n"]}']['id']), 1))
            its.append(((gid(f'it-m{n}-r{s["n"]}'), 'WikiPage', 'active', f'Recursos de aprendizaje · Sesión {s["n"]}', PAGES[f'm{n}-recursos-{s["n"]}']['id']), 2))
            for g in DATA.get('practicas', []):
                if g.get('momento') == n and g.get('sesion') == s['n']:
                    its.append(((gid(f'it-pr-{g["id"]}'), 'Assignment', 'unpublished', f'{PRAC} {g["id"]} · {g["titulo"]}', practicas[g['id']]), 2))
        its.append(((item_id(ACT[n], f'it-act{n}'), 'Assignment', 'unpublished', f'Actividad {n} · Evidencia del Momento {n}', ACT[n]), 1))
        mods.append(module(tm['id'] if tm else gid(f'mod-m{n}'), f'Momento {n}: {M["titulo"]}', 'active', pos, its))
        if tm:
            usados_mod.add(tm['id'])
        pos += 1
    for m in d['modulos']:                       # momentos de la plantilla que el sílabo no usa: sin publicar
        if m['id'] not in usados_mod and re.fullmatch(r'momento \d+', m['titulo'].lower()):
            mods.append(repos(m['xml'], pos, 'unpublished')); usados_mod.add(m['id']); pos += 1
    for m in d['modulos']:                       # el resto de la plantilla (Encuesta, PIS…), tal cual
        if m['id'] not in usados_mod:
            mods.append(repos(m['xml'], pos)); pos += 1
    mods.append(module(gid('mod-guia'), 'Guía del docente (oculto)', 'unpublished', pos,
                       [((gid('it-guia'), 'WikiPage', 'unpublished', 'Guía del docente: videos y actualización del aula', PAGES['guia']['id']), 0)]))
    head = old[:old.find('  <module ')]
    (tmp / 'course_settings/module_meta.xml').write_text(head + ''.join(mods) + '</modules>\n')

    # Organización del manifiesto (espejo de los módulos)
    org = []
    for m in re.finditer(r'<module identifier="(\w+)">\s*<title>(.*?)</title>(.*?)</module>', (tmp / 'course_settings/module_meta.xml').read_text(), re.S):
        items = ''.join(f'          <item identifier="{i[0]}" identifierref="{i[2]}">\n            <title>{i[1]}</title>\n          </item>\n'
                        for i in re.findall(r'<item identifier="(\w+)">\s*<content_type>[\w:]+</content_type>\s*<workflow_state>\w+</workflow_state>\s*<title>(.*?)</title>\s*<identifierref>(\w+)</identifierref>', m.group(3), re.S))
        org.append(f'        <item identifier="{m.group(1)}">\n          <title>{m.group(2)}</title>\n{items}        </item>\n')
    man = re.sub(r'(<item identifier="LearningModules">\n).*?(      </item>\n    </organization>)', lambda m: m.group(1) + ''.join(org) + m.group(2), man, flags=re.S)
    (tmp / 'imsmanifest.xml').write_text(man)

    # La carpeta nueva es visible en Archivos (las de la plantilla siguen ocultas)
    fmf = tmp / 'course_settings/files_meta.xml'
    if fmf.exists():
        fmf.write_text(fmf.read_text().replace('  </folders>', f'    <folder path="{CARPETA}">\n      <hidden>false</hidden>\n    </folder>\n  </folders>', 1))

    # Comprobaciones: enlaces internos, archivos citados y datos que no deben publicarse
    todo_html = {f: f.read_text(errors='ignore') for f in tmp.rglob('*.html')}
    for f, t in todo_html.items():
        for ref in re.findall(r'\$WIKI_REFERENCE\$/pages/(g[0-9a-f]{32})', t):
            assert ref in man, f'{f.name}: enlace a una página que no está en el paquete ({ref})'
    for ref in set(re.findall(r'\$IMS-CC-FILEBASE\$/([^"?]*)', ''.join(todo_html.values()))):
        assert (WR / unquote(ref)).exists(), f'Archivo enlazado que no está en el paquete: {unquote(ref)}'
    for secreto in DATA.get('no_publicar', []):
        hit = [f.name for f, t in todo_html.items() if secreto and secreto in t]
        assert not hit, f'«{secreto}» (no_publicar) aparece en: {hit}'
    pendientes = sorted({f.name for f, t in todo_html.items() if '[COMPLETAR' in t})
    if pendientes:
        aviso('Quedan marcas [COMPLETAR] en: ' + ', '.join(pendientes))

    # Paquete y versiones para pegar
    OUT.mkdir(exist_ok=True)
    pkg = OUT / f'{ARCHIVO}-canvas.imscc'
    pkg.unlink(missing_ok=True)
    with zipfile.ZipFile(pkg, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(tmp / 'imsmanifest.xml', 'imsmanifest.xml')
        for f in sorted(tmp.rglob('*')):
            if f.is_file() and f.name != 'imsmanifest.xml':
                z.write(f, f.relative_to(tmp).as_posix())
    pg = OUT / 'pegar'
    if pg.exists():
        shutil.rmtree(pg)
    pg.mkdir()
    by_id = {v[0]: k for k, v in d['paginas'].items()}
    by_id.update({P['id']: P['file'] for P in PAGES.values()})
    for f in sorted(W.glob('*.html')):
        if f.stem not in d['viejas'] and f.stem != T['inicio_file']:
            (pg / f.name).write_text(pegar(f.read_text(), by_id))
    mb = pkg.stat().st_size / 1e6
    nf = len(dict(files))
    print(f'  plantilla: {src.name}')
    print(f'  → {pkg.relative_to(ROOT)} ({mb:.1f} MB): {len(momentos)} momento(s), {sum(len(M["sesiones"]) for M in momentos)} sesiones, '
          f'{len(PAGES)} páginas nuevas, {len(practicas)} práctica(s), {nf} archivos')
    print(f'  → {pg.relative_to(ROOT)}/ (HTML para pegar en las páginas existentes del curso)')
    if mb > 450:
        aviso(f'El paquete pesa {mb:.0f} MB: la cuota habitual de un curso es de unos 500 MB. Considera --sin-videos y subir los videos a mano.')
    for a in AVISOS:
        print('  AVISO:', a)
    shutil.rmtree(tmp)
    return 0


if __name__ == '__main__':
    sys.exit(main())
