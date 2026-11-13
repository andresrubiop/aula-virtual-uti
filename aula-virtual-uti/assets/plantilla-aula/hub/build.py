#!/usr/bin/env python3
"""Ensambla el aula interactiva (UTI) en UN SOLO archivo por edición:
  hub/dist/index.html     edición ESTUDIANTE
  hub/dist/profesor.html  edición DOCENTE: incluye además lo marcado con <!--docente--> … <!--/docente-->

Uso:  python3 hub/build.py            (desde la raíz del proyecto o desde hub/)

Sin dependencias externas (solo Python ≥ 3.10). Incrusta:
  - identidad-uti/tokens.css + hub/src/css/*.css                 (orden alfabético)
  - fuentes Poppins / JetBrains Mono / KaTeX como data URI        (hub/vendor)
  - logos oficiales UTI (identidad-uti/)                          como data URI
  - hub/src/course.json → window.HUB_COURSE, la cabecera, el pie y el menú de unidades
  - hub/src/content/**/*.html                                     (orden alfabético de ruta), con:
      <!--@@code:pr1/ejemplo.py@@-->     un archivo real de practicas/ (opcional #10-40: rango de líneas)
      <!--@@out:pr1/ejemplo@@-->         una salida real guardada en practicas/salidas/pr1/ejemplo.txt
      <!--@@desafio:PR1@@-->             el desafío con IA generativa de practicas/desafios_ia.json (bilingüe)
      <!--@@figura:F1.1@@-->             una figura interactiva autónoma de hub/src/figuras/ (HTML completo hecho con otra
                                         skill o herramienta —p. ej. anatomy, three.js—), aislada en un <iframe srcdoc>
      <!--@@UNIT_CARDS@@--> · <!--@@FACTS@@-->   tarjetas de las unidades y cifras de la portada (desde course.json)
      href="@@datos:materiales/unidad-1/X.zip@@"  un archivo pequeño incrustado como data URI
  - hub/src/data/*  (csv, json, txt) → window.HUB_DATA            datos reales para las animaciones
  - hub/config.json → window.HUB_CONFIG
  - KaTeX + hub/src/js/{core,components,anim}/*.js + app.js
  - bibliotecas opcionales de hub/vendor/opcional/<nombre>.js que course.json pida en "vendor": ["three"]
    (hub/tools/vendor.py las descarga una vez; después el aula sigue funcionando sin conexión)
Comprueba: etiquetas estructurales balanceadas, tantos bloques lang="es" como lang="en" por archivo (aviso de
traducción faltante), marcas [COMPLETAR] pendientes y animaciones citadas que no existen.
"""
import base64
import datetime
import hashlib
import html as htmlmod
import json
import pathlib
import re
import sys

HUB = pathlib.Path(__file__).resolve().parent
ROOT = HUB.parent
SRC = HUB / 'src'
VENDOR = HUB / 'vendor'
DIST = HUB / 'dist'
IDENT = ROOT / 'identidad-uti'
PRACTICAS = ROOT / 'practicas'
DESAFIOS = PRACTICAS / 'desafios_ia.json'
VERSION = (HUB / 'VERSION').read_text().strip() if (HUB / 'VERSION').exists() else '0.0.0'


def datauri(path: pathlib.Path, mime: str) -> str:
    return f'data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}'


def fonts_css() -> str:
    meta = json.loads((VENDOR / 'fonts' / 'fonts.json').read_text())
    faces = {}
    for f in meta:
        p = VENDOR / 'fonts' / f['file']
        key = (f['family'], f['style'], hashlib.sha1(p.read_bytes()).hexdigest())
        if key in faces:
            faces[key]['weights'].append(int(f['weight']))
            continue
        faces[key] = {**f, 'weights': [int(f['weight'])], 'uri': datauri(p, 'font/woff2')}
    out = []
    for v in faces.values():
        w = v['weights']
        weight = f'{min(w)} {max(w)}' if len(w) > 1 else str(w[0])
        out.append(f"@font-face{{font-family:'{v['family']}';font-style:{v['style']};"
                   f"font-weight:{weight};font-display:swap;src:url({v['uri']}) format('woff2');"
                   f"unicode-range:{v['range']};}}")
    return '\n'.join(out)


def katex_css() -> str:
    css = (VENDOR / 'katex' / 'katex.min.css').read_text()

    def repl(m):
        return f'src:url({datauri(VENDOR / "katex" / "fonts" / (m.group(1) + ".woff2"), "font/woff2")}) format("woff2")'
    return re.sub(r'src:url\(fonts/(KaTeX_[\w-]+)\.woff2\) format\("woff2"\)(?:,url\([^)]*\) format\("[^"]*"\))*',
                  repl, css)


def cat(folder: pathlib.Path, pattern: str) -> tuple[str, list[pathlib.Path]]:
    files = sorted(folder.glob(pattern), key=lambda f: f.name) if folder.exists() else []
    parts = [f'/* ---- {f.relative_to(HUB)} ---- */\n{f.read_text()}' for f in files]
    return '\n'.join(parts), files


def strip_noise(html: str) -> str:
    html = re.sub(r'<script\b[\s\S]*?</script>', '', html)
    return re.sub(r'<!--[\s\S]*?-->', '', html)


def check_balance(html: str) -> list[str]:
    body = strip_noise(html)
    out = []
    for tag in ('section', 'article', 'div', 'nav', 'details', 'figure', 'table', 'ul', 'ol', 'span'):
        o = len(re.findall(rf'<{tag}\b', body))
        c = len(re.findall(rf'</{tag}>', body))
        if o != c:
            out.append(f'<{tag}>: {o} abiertas / {c} cerradas')
    return out


def check_langs(files: list[pathlib.Path]) -> list[str]:
    """Por archivo: bloques en español y en inglés deben coincidir (texto sin traducir = aviso)."""
    out = []
    for f in files:
        body = strip_noise(f.read_text())
        es = len(re.findall(r'\blang="es"', body))
        en = len(re.findall(r'\blang="en"', body))
        if es != en:
            out.append(f'{f.relative_to(SRC)}: {es} bloques lang="es" / {en} lang="en"')
    return out


def esc(s: str) -> str:
    return htmlmod.escape(str(s), quote=False)


def bi(es: str, en: str, tag: str = 'span') -> str:
    """Bloque bilingüe: <span lang="es">…</span><span lang="en">…</span>."""
    return f'<{tag} lang="es">{es}</{tag}><{tag} lang="en">{en}</{tag}>'


def bid(d: dict | None, tag: str = 'span') -> str:
    """Lo mismo desde {"es": …, "en": …} de course.json (escapado; si falta el inglés se repite el español)."""
    d = d or {}
    return bi(esc(d.get('es', '')), esc(d.get('en') or d.get('es', '')), tag)


LANG_CODE = {'.c': 'c', '.h': 'c', '.py': 'python', '.sh': 'bash', '.js': 'js', '.sql': 'sql', '.r': 'r', '.java': 'java'}


def code_blocks(content: str) -> tuple[str, list[str]]:
    """Código, salidas y archivos reales: el aula nunca copia a mano lo que existe en practicas/."""
    missing = []

    def pick(lines, spec):
        keep, last = [], 0
        for part in spec.split(','):
            a, b = (int(x) for x in part.split('-'))
            keep += (['…'] if last and a > last + 1 else []) + lines[a - 1:b]
            last = b
        return keep, last

    def code(m):
        rel, rng = m.group(1), m.group(2)
        p = PRACTICAS / rel
        if not p.exists():
            missing.append(str(p.relative_to(ROOT)))
            return ''
        text = p.read_text()
        if rng:
            text = '\n'.join(pick(text.splitlines(), rng)[0])
        lang = LANG_CODE.get(p.suffix.lower(), 'text')
        return f'<pre data-file="practicas/{rel}"><code class="lang-{lang}">{esc(text)}</code></pre>'

    def out(m):
        p = PRACTICAS / 'salidas' / (m.group(1) + '.txt')
        if not p.exists():
            missing.append(str(p.relative_to(ROOT)))
            return ''
        text = p.read_text().rstrip()
        if m.group(2):
            lines = text.splitlines()
            keep, last = pick(lines, m.group(2))
            text = '\n'.join(keep + (['…'] if last < len(lines) else []))
        return f'<pre><code class="lang-out">{esc(text)}</code></pre>'

    content = re.sub(r'<!--@@code:([\w./-]+?)(?:#(\d+-\d+(?:,\d+-\d+)*))?@@-->', code, content)
    content = re.sub(r'<!--@@out:([\w./-]+?)(?:#(\d+-\d+(?:,\d+-\d+)*))?@@-->', out, content)

    def datos(m):
        f = ROOT / m.group(1)
        if not f.is_file():
            missing.append(m.group(1))
            return '#'
        mime = {'.zip': 'application/zip', '.pdf': 'application/pdf', '.csv': 'text/csv',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}.get(f.suffix, 'application/octet-stream')
        return datauri(f, mime)

    content = re.sub(r'@@datos:([\w./-]+)@@', datos, content)
    return content, missing


def figuras_html(content: str) -> tuple[str, list[str]]:
    """Figuras interactivas autónomas (hub/src/figuras/): un HTML completo, sin dependencias externas, hecho con otra
    skill o herramienta (anatomy, three.js, un simulador propio). Se incrusta en un <iframe srcdoc> para que su CSS y
    su JavaScript no choquen con los del aula. F1.1.html = una sola versión; F1.1.es.html + F1.1.en.html = bilingüe.
    Atributos opcionales en el marcador: <!--@@figura:F1.1 alto=520 titulo="Motor en corte"@@-->"""
    carpeta = SRC / 'figuras'
    faltan = []

    def frame(f: pathlib.Path, alto: str, titulo: str) -> str:
        doc = f.read_text()
        if re.search(r"""(?:src|href)=["']https?://""", doc):
            print(f'ADVERTENCIA FIGURA: {f.name} carga recursos de internet; no funcionará sin conexión', file=sys.stderr)
        return (f'<iframe class="figura__frame" loading="lazy" style="width:100%;height:{alto}px;border:0" '
                f'title="{htmlmod.escape(titulo, quote=True)}" sandbox="allow-scripts" srcdoc="{htmlmod.escape(doc, quote=True)}"></iframe>')

    def repl(m):
        fid, resto = m.group(1), m.group(2) or ''
        alto = (re.search(r'alto=(\d+)', resto) or [None, '480'])[1]
        titulo = (re.search(r'titulo="([^"]*)"', resto) or [None, fid])[1]
        uno, es, en = carpeta / f'{fid}.html', carpeta / f'{fid}.es.html', carpeta / f'{fid}.en.html'
        if es.exists() and en.exists():
            cuerpo = f'<div lang="es">{frame(es, alto, titulo)}</div><div lang="en">{frame(en, alto, titulo)}</div>'
        elif uno.exists():
            cuerpo = frame(uno, alto, titulo)
        else:
            faltan.append(fid)
            return ''
        return f'<figure class="figura" id="fig-{fid.replace(".", "-")}" data-figura="{fid}">{cuerpo}</figure>'
    return re.sub(r'<!--@@figura:([A-Za-z0-9.]+)((?:\s+[^@]*)?)@@-->', repl, content), faltan


def desafios_html(content: str) -> tuple[str, list[str]]:
    datos = json.loads(DESAFIOS.read_text(encoding='utf-8')) if DESAFIOS.exists() else {}
    faltan = []

    def both(d, tag='span'):
        return bi(esc(d['es']), esc(d['en']), tag)

    def repl(m):
        d = datos.get(m.group(1))
        if not d:
            faltan.append(m.group(1))
            return ''
        verif = ''.join(f'<li>{both({"es": a, "en": b})}</li>' for a, b in zip(d['verifica']['es'], d['verifica']['en']))
        return (
            '<details class="fold fold--ia"><summary>'
            '<span lang="es">Desafío con IA generativa · </span><span lang="en">Generative AI challenge · </span>'
            f'{both(d["titulo"])}</summary><div class="fold__body">'
            f'<p><strong><span lang="es">Objetivo.</span><span lang="en">Goal.</span></strong> {both(d["objetivo"])}</p>'
            '<p><span lang="es"><strong>Prompt inicial.</strong> Úsalo en la herramienta que prefieras (Gemini, Claude, ChatGPT, Copilot…) '
            'con el material de la práctica como contexto. Pide primero un plan y revisa cada paso antes de aceptarlo.</span>'
            '<span lang="en"><strong>Starting prompt.</strong> Use it in the tool you prefer (Gemini, Claude, ChatGPT, Copilot…) '
            'with the practice material as context. Ask for a plan first and review every step before accepting it.</span></p>'
            f'<div lang="es"><pre><code class="lang-prompt">{esc(d["prompt"]["es"])}</code></pre></div>'
            f'<div lang="en"><pre><code class="lang-prompt">{esc(d["prompt"]["en"])}</code></pre></div>'
            '<p><strong><span lang="es">Cómo verificar el resultado</span><span lang="en">How to check the result</span></strong></p>'
            f'<ul>{verif}</ul>'
            '<p><span lang="es"><strong>Declara el uso de IA:</strong> herramienta, prompts relevantes, qué verificaste tú y qué corregiste. '
            'Lo que cuenta es que puedas explicar y comprobar cada decisión.</span>'
            '<span lang="en"><strong>Declare your use of AI:</strong> tool, relevant prompts, what you checked yourself and what you fixed. '
            'What counts is that you can explain and verify every decision.</span></p></div></details>')
    return re.sub(r'<!--@@desafio:([A-Za-z0-9.]+)@@-->', repl, content), faltan


def nav_html(course: dict) -> str:
    items = []
    for u in course['units']:
        items.append(f'      <a href="#/{u["id"]}" data-nav="{u["id"]}"><span>U{u["n"]}</span>'
                     f'<small>{bid(u["short"])}</small></a>')
    return '\n'.join(items)


ICONS = {
    'resumen': '<path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2zM9 4v14M15 6v14"/>',
    'preparacion': '<circle cx="12" cy="12" r="9"/><path d="M10 8.5l5 3.5-5 3.5z"/>',
    'presentacion': '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    'animaciones': '<path d="M3 17c3 0 3-10 6-10s3 10 6 10 3-6 6-6"/>',
    'tarea': '<path d="M9 3h6v3H9zM7 4.5H5V21h14V4.5h-2M8.5 12l2 2 4-4M8.5 17h7"/>',
    'manual': '<path d="M4 19V5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM8 7h7"/>',
    'practica': '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.8 3h10.4a2 2 0 0 0 1.8-3l-5-9V3M7.5 15h9"/>',
    'laboratorio': '<path d="M8 8l-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
    'quiz': '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7M12 17h.01"/>',
    'bibliografia': '<path d="M5 4h3v16H5zM10 4h3v16h-3zM15.5 4.5l2.9-.8 3.1 15.5-2.9.8z"/>',
}
ICONS['actividad'] = ICONS['tarea']
ICONS['caso'] = ICONS['manual']


def sub_label(sub: str, u: dict, course: dict) -> tuple[str, str]:
    """Etiquetas del menú de cada unidad (es, en). «practica» toma el nombre que el curso le da a su componente
    práctico-experimental (course.json → practice: Laboratorio, Taller, Caso clínico…)."""
    n, lab = u['n'], u.get('lab') or ''
    prac = course.get('practice') or {'es': 'Práctica', 'en': 'Practice'}
    return {
        'resumen': ('Resumen y ruta', 'Overview and path'),
        'preparacion': ('Antes de clase', 'Before class'),
        'presentacion': (f'Presentación P{n}', f'Slides P{n}'),
        'animaciones': ('Animaciones', 'Animations'),
        'manual': (f'Manual M{n}', f'Manual M{n}'),
        'practica': (f'{prac["es"]} {lab}'.strip(), f'{prac.get("en") or prac["es"]} {lab}'.strip()),
        'laboratorio': (f'Laboratorio {lab}'.strip(), f'Lab {lab}'.strip()),
        'caso': ('Caso de estudio', 'Case study'),
        'actividad': ('Actividad', 'Activity'),
        'tarea': ('Tarea', 'Assignment'),
        'quiz': (f'Cuestionario Q{n}', f'Quiz Q{n}'),
        'bibliografia': ('Bibliografía', 'Bibliography'),
    }.get(sub, (sub.capitalize(), sub.capitalize()))


def default_resumen(u: dict) -> str:
    anims = ''.join(f'<li><code>{a["id"]}</code> {bi(esc(a["es"]), esc(a["en"]))}</li>' for a in u.get('anims', []))
    return f"""<article class="sub" data-sub="resumen">
  <div class="sub-head">
    <span class="eyebrow">{bi('Resumen y ruta', 'Overview and path')}</span>
    <h2>{bid(u['title'])}</h2>
    <p><span class="status status--produccion">{bi('En producción', 'In production')}</span></p>
    <p>{bi('Esta unidad todavía se está construyendo.', 'This unit is still being built.')}</p>
  </div>
  <div class="card"><h3>{bi('Animaciones planificadas', 'Planned animations')}</h3><ul>{anims}</ul></div>
</article>
"""


def default_animaciones(u: dict) -> str:
    cards = '\n'.join(f'  <div class="anim" data-anim="{a["id"]}" data-title="{esc(a["es"])}" data-title-en="{esc(a["en"])}"></div>'
                      for a in u.get('anims', []))
    return f"""<article class="sub" data-sub="animaciones">
  <div class="sub-head">
    <span class="eyebrow">{bi('Animaciones', 'Animations')}</span>
    <h2>{bi('Los conceptos de la unidad, en movimiento', 'The concepts of the unit, in motion')}</h2>
    <p>{bi('Cada animación calcula o simula de verdad lo que muestra: sigue el recorrido guiado, cambia los parámetros y compara con lo que haces en la práctica.',
           'Every animation really computes or simulates what it shows: follow the guided tour, change the parameters and compare with what you do in the practice.')}</p>
  </div>
{cards}
</article>
"""


def unit_view(u: dict, course: dict) -> tuple[str, list[pathlib.Path]]:
    folder = SRC / 'content' / u['id']
    files = sorted(folder.glob('*.html')) if folder.exists() else []
    subs = {}
    for f in files:
        m = re.match(r'(\d+)-([a-z]+)\.html$', f.name)
        if m:
            subs[m.group(2)] = (int(m.group(1)), f.read_text())
    if 'resumen' not in subs:
        subs['resumen'] = (10, default_resumen(u))
    if 'animaciones' not in subs and u.get('anims'):
        subs['animaciones'] = (40, default_animaciones(u))
    order = sorted(subs, key=lambda k: subs[k][0])
    art = (folder / 'art.svg').read_text() if (folder / 'art.svg').exists() else ''
    uid, n = u['id'], u['n']
    weeks = str(u.get('weeks', ''))
    one = '–' not in weeks and '-' not in weeks
    weeks_es, weeks_en = ('Semana ' if one else 'Semanas ') + weeks, ('Week ' if one else 'Weeks ') + weeks
    dates = u.get('dates') or {}
    when = bi(esc(weeks_es + (' · ' + dates['es'] if dates.get('es') else '')), esc(weeks_en + (' · ' + (dates.get('en') or dates['es']) if dates.get('es') else '')))
    moment = u.get('moment')
    eyebrow = bi(f'Unidad {n}' + (f' · Momento {moment}' if moment else ''), f'Unit {n}' + (f' · Moment {moment}' if moment else ''))
    na = len(u.get('anims', []))
    meta = [f'<span><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>{when}</span>']
    if u.get('lab'):
        es, en = sub_label('practica', u, course)
        meta.append(f'<span><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS["practica"]}</svg>{bi(esc(es), esc(en))}</span>')
    if na:
        meta.append(f'<span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 17c3 0 3-10 6-10s3 10 6 10 3-6 6-6"/></svg>{bi(f"{na} animaciones" if na != 1 else "1 animación", f"{na} animations" if na != 1 else "1 animation")}</span>')
    links = '\n'.join(
        f'      <a href="#/{uid}/{k}" data-sub="{k}"><svg viewBox="0 0 24 24" aria-hidden="true">{ICONS.get(k, ICONS["manual"])}</svg>'
        f'{bi(*map(esc, sub_label(k, u, course)))}</a>' for k in order)
    body = '\n'.join(f'<!-- ---- {uid}/{k} ---- -->\n{subs[k][1]}' for k in order)
    view = f"""<section class="view" data-view="{uid}" aria-labelledby="{uid}-titulo" hidden>
  <header class="week-hero">
    <div class="week-hero__inner">
      <div>
        <span class="eyebrow">{eyebrow}</span>
        <h1 class="week-hero__title" id="{uid}-titulo">{bid(u['title'])}</h1>
        <div class="week-hero__meta">
          {''.join(meta)}
        </div>
      </div>
      <div class="week-hero__art art" aria-hidden="true">{art}</div>
    </div>
  </header>
  <div class="week">
    <nav class="week-nav" data-i18n='{{"aria-label": ["Secciones de la unidad {n}", "Sections of unit {n}"]}}'>
      <p class="week-nav__label">{bi(f'Unidad {n}', f'Unit {n}')}</p>
{links}
    </nav>
    <div class="week-body">
{body}
    </div>
  </div>
</section>
"""
    return view, files


def unit_cards(course: dict) -> str:
    """Tarjetas de la portada (<!--@@UNIT_CARDS@@--> en 00-inicio.html): una por unidad, con su avance."""
    out = []
    for u in course['units']:
        uid, n = u['id'], u['n']
        weeks = str(u.get('weeks', ''))
        one = '–' not in weeks and '-' not in weeks
        folder = SRC / 'content' / uid
        art = (folder / 'art.svg').read_text() if (folder / 'art.svg').exists() else ''
        due = ''
        if u.get('lab'):
            es, en = sub_label('practica', u, course)
            due = f'<p class="week-card__due">{bi(esc(es), esc(en))}</p>'
        out.append(f"""        <a class="week-card" href="#/{uid}">
          <div class="week-card__top"><span class="week-card__n">{bi(f'Unidad {n}', f'Unit {n}')}</span><span class="week-card__dates">{bi(('Semana ' if one else 'Semanas ') + esc(weeks), ('Week ' if one else 'Weeks ') + esc(weeks))}</span></div>
          <div class="week-card__art art" aria-hidden="true">{art}</div>
          <h3>{bid(u['title'])}</h3>
          {due}
          <div class="week-card__bar" data-week-progress="{uid}"><span></span></div>
          <div class="week-card__foot"><span data-week-progress-label="{uid}">0 %</span><span>U{n}</span></div>
        </a>""")
    return '\n'.join(out)


def facts(course: dict) -> str:
    """Cifras de la portada (<!--@@FACTS@@-->): se cuentan, no se escriben a mano."""
    us = course['units']
    na = sum(len(u.get('anims', [])) for u in us)
    nl = sum(1 for u in us if u.get('lab'))
    prac = course.get('practice') or {'es': 'Práctica', 'en': 'Practice'}
    out = [f'<span><strong>{len(us)}</strong> {bi("unidades" if len(us) != 1 else "unidad", "units" if len(us) != 1 else "unit")}</span>']
    if na:
        out.append(f'<span><strong>{na}</strong> {bi("animaciones interactivas", "interactive animations")}</span>')
    if nl:
        out.append(f'<span><strong>{nl}</strong> × {bi(esc(prac["es"].lower()), esc((prac.get("en") or prac["es"]).lower()))}</span>')
    return ''.join(out)


def safe_js(js: str) -> str:
    return js.replace('</script', '<\\/script')


def main() -> int:
    tpl = (SRC / 'index.html').read_text()
    css, _ = cat(SRC / 'css', '*.css')
    tokens = (IDENT / 'tokens.css').read_text()
    course = json.loads((SRC / 'course.json').read_text())
    course = {k: v for k, v in course.items() if not k.startswith('_')}
    for k in ('key', 'title', 'units'):
        if k not in course:
            print(f'ERROR: falta «{k}» en hub/src/course.json', file=sys.stderr)
            return 1
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{2,40}', course['key']):
        print('ERROR: course.json → key debe ser corta, en minúsculas, con letras, cifras y guiones (p. ej. uti-fso-b26)', file=sys.stderr)
        return 1
    content_files = sorted((SRC / 'content').glob('*.html'))
    parts = [f.read_text() for f in content_files if f.name < '50']        # 00-inicio
    for u in course['units']:
        view, files = unit_view(u, course)
        parts.append(view)
        content_files += files
    parts += [f.read_text() for f in sorted((SRC / 'content').glob('*.html')) if f.name >= '50']   # 95-recursos
    content = '\n'.join(parts)
    content = content.replace('<!--@@UNIT_CARDS@@-->', unit_cards(course)).replace('<!--@@FACTS@@-->', facts(course))
    content, faltan = desafios_html(content)
    if faltan:
        print(f'ERROR: desafíos sin definir en practicas/desafios_ia.json: {faltan}', file=sys.stderr)
        return 1
    content, sin_figura = figuras_html(content)
    if sin_figura:
        print(f'ERROR: figuras citadas que no existen en hub/src/figuras/: {sin_figura}', file=sys.stderr)
        return 1
    content, missing = code_blocks(content)
    if missing:
        print('ERROR: archivos citados en el contenido que no existen:', file=sys.stderr)
        for m in missing:
            print('   ', m, file=sys.stderr)
        return 1
    problems = check_balance(content)
    lang_warn = check_langs(content_files)
    js_parts, js_files = [], []
    for sub in ('core', 'components', 'anim'):
        part, files = cat(SRC / 'js' / sub, '*.js')
        js_parts.append(part)
        js_files += files
    app = (SRC / 'js' / 'app.js').read_text()
    vendor_js = (VENDOR / 'katex' / 'katex.min.js').read_text() + '\n' + (VENDOR / 'katex' / 'auto-render.min.js').read_text()
    for lib in course.get('vendor', []):
        f = VENDOR / 'opcional' / f'{lib}.js'
        if not f.exists():
            print(f'ERROR: course.json pide la biblioteca «{lib}» y no está en hub/vendor/opcional/ (python3 hub/tools/vendor.py {lib})', file=sys.stderr)
            return 1
        vendor_js += f'\n/* ---- vendor/opcional/{lib}.js ---- */\n' + f.read_text()

    # Animaciones: las que el contenido cita deben estar definidas, y las definidas deberían usarse
    js_all = '\n'.join(js_parts)
    definidas = set(re.findall(r"""\bid:\s*['"](A[\w.]+)['"]""", js_all))
    citadas = set(re.findall(r'data-anim="(A[\w.]+)"', content))
    planificadas = {a['id'] for u in course['units'] for a in u.get('anims', [])}
    sin_definir = sorted(citadas - definidas)

    build = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    cfg_path = HUB / 'config.json'
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    cfg = {k: v for k, v in cfg.items() if not k.startswith('_')}
    data_dir = SRC / 'data'
    data = {str(f.relative_to(data_dir)): f.read_text() for f in sorted(data_dir.rglob('*'))
            if f.is_file() and f.suffix in ('.csv', '.json', '.txt', '.tsv')} if data_dir.exists() else {}
    model_js = 'window.HUB_DATA = ' + json.dumps(data, ensure_ascii=False) + ';\n'

    t = course['title']
    kicker = ' · '.join(x for x in ((course.get('program') or {}).get('es'), (course.get('level') or {}).get('es')) if x)
    kicker_en = ' · '.join(x for x in ((course.get('program') or {}).get('en') or (course.get('program') or {}).get('es'),
                                       (course.get('level') or {}).get('en') or (course.get('level') or {}).get('es')) if x)
    fac = course.get('faculty') or {}
    foot1 = bi(esc(' · '.join(x for x in (t['es'], fac.get('es')) if x)), esc(' · '.join(x for x in (t.get('en') or t['es'], fac.get('en') or fac.get('es')) if x)))
    term = course.get('term') or ''
    foot2 = bi(esc(' · '.join(x for x in (kicker, f'período {term}' if term else '') if x)),
               esc(' · '.join(x for x in (kicker_en, f'term {term}' if term else '') if x)))
    repl = {
        '/*@@CONFIG@@*/': json.dumps(cfg, ensure_ascii=False) + ';\nwindow.HUB_COURSE = ' + json.dumps(course, ensure_ascii=False),
        '/*@@FONTS@@*/': fonts_css(),
        '/*@@KATEX_CSS@@*/': katex_css(),
        '/*@@CSS@@*/': tokens + '\n' + css,
        '<!--@@NAV@@-->': nav_html(course),
        '<!--@@CONTENT@@-->': content,
        '<!--@@BRAND_KICKER@@-->': bi(esc(kicker), esc(kicker_en)),
        '<!--@@BRAND_TITLE@@-->': bid(t),
        '<!--@@FOOT_1@@-->': foot1,
        '<!--@@FOOT_2@@-->': foot2,
        '@@TITLE@@': esc(t['es']) + ' · UTI',
        '/*@@VENDOR_JS@@*/': safe_js(vendor_js),
        '/*@@JS@@*/': safe_js(model_js + '\n'.join(js_parts) + '\n' + app),
        '@@LOGO_COLOR@@': datauri(IDENT / 'logo-uti-horizontal-color.png', 'image/png'),
        '@@LOGO_BLANCO@@': datauri(IDENT / 'logo-uti-horizontal-blanco.png', 'image/png'),
        '@@LOGO_PIE@@': datauri(IDENT / 'logo-uti-horizontal-blanco.png', 'image/png'),
        '@@FAVICON@@': datauri(IDENT / 'favicon.png', 'image/png'),
        '@@BUILD@@': build,
        '@@VERSION@@': VERSION,
    }
    out = tpl
    for k, v in repl.items():
        if k not in out:
            print(f'ERROR: falta el marcador {k} en src/index.html', file=sys.stderr)
            return 1
        out = out.replace(k, v)
    out = out.replace('@@KEY@@', course['key'])
    left = re.findall(r'@@[A-Z_]+@@', out)
    if left:
        print(f'ERROR: marcadores sin reemplazar: {sorted(set(left))}', file=sys.stderr)
        return 1

    abiertos, cerrados = out.count('<!--docente-->'), out.count('<!--/docente-->')
    if abiertos != cerrados:
        print(f'ERROR: marcas docentes desbalanceadas ({abiertos} / {cerrados})', file=sys.stderr)
        return 1
    estudiante = re.sub(r'[ \t]*<!--docente-->[\s\S]*?<!--/docente-->', '', out)
    docente = out.replace('<html lang="es" data-lang="es">', '<html lang="es" data-lang="es" data-edicion="docente">', 1)
    problems += [f'(edición estudiante) {x}' for x in check_balance(re.sub(r'[ \t]*<!--docente-->[\s\S]*?<!--/docente-->', '', content))]

    DIST.mkdir(exist_ok=True)
    print(f'aula «{t["es"]}» · UTI v{VERSION} · {build}')
    for nombre, doc in (('index.html', estudiante), ('profesor.html', docente)):
        p = DIST / nombre
        p.write_text(doc)
        size = p.stat().st_size / 1e6
        print(f'  → {p.relative_to(ROOT)} ({size:.2f} MB)')
        if size > 15:
            print('ADVERTENCIA: supera el objetivo de 15 MB', file=sys.stderr)
    print(f'  contenido: {len(content_files)} archivos · js: {len(js_files)} + app.js · animaciones: {len(definidas)} definidas, '
          f'{len(citadas)} en uso, {len(planificadas - definidas)} planificadas sin hacer · bloques docentes: {abiertos} · datos: {len(data)}')
    pend = len(re.findall(r'\[COMPLETAR[^\]]*\]', estudiante))
    if pend:
        print(f'  pendientes: {pend} marca(s) [COMPLETAR] visibles para el estudiante')
    for a in sin_definir:
        print(f'ADVERTENCIA ANIMACIÓN: {a} se cita en el contenido y no está en hub/src/js/anim/ (se verá como «planificada»)', file=sys.stderr)
    for p in problems:
        print('ADVERTENCIA HTML:', p, file=sys.stderr)
    for w in lang_warn:
        print('ADVERTENCIA IDIOMA:', w, file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
