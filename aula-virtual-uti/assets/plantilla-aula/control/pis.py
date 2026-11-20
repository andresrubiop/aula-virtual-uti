#!/usr/bin/env python3
"""Proyecto Interdisciplinario Socioformativo (PIS): datos, verificación y módulo compartible entre aulas.

    python3 control/pis.py verificar                     # según canvas/silabo.json → pis_rol
    python3 control/pis.py exportar [--con-documentos]   # paquete para el docente de otro proyecto formativo → pis/compartir/
    python3 control/pis.py importar <paquete.zip|pis.json>   # en el aula de un proyecto formativo que aporta al PIS
    python3 control/pis.py --json …

Rol del aula (canvas/silabo.json → "pis_rol", lo responde el docente al inicio):
  · "articulador": este proyecto formativo integra el PIS. Son OBLIGATORIOS el documento del PIS en fuentes/pis/ y
    los datos en canvas/pis.json (los transcribe el asistente del documento, en español e inglés). Sin ellos no se
    genera el paquete de Canvas.
  · "aportante": otro proyecto formativo integra el PIS. Se pide al docente articulador que comparta su paquete
    (exportar en su aula) y aquí se importa. Mientras falte queda pendiente, sin bloquear el resto del aula.
  · "no_aplica": el período no tiene PIS.
Con canvas/pis.json, hub/build.py agrega la vista «PIS» al aula y canvas/generar_canvas.py el módulo «PIS» del
curso (proyecto, momentos, rúbrica y evidencia integradora) con las tareas PIS de la plantilla, sin publicar.
Para llevar solo ese módulo a un curso: python3 canvas/canvas_api.py plan|aplicar --modulo PIS.
"""
import argparse
import hashlib
import html
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
DATOS = ROOT / 'canvas' / 'pis.json'
FUENTES = ROOT / 'fuentes' / 'pis'
ROLES = ('articulador', 'aportante', 'no_aplica')
TEXTO = ('titulo', 'pf_articulador', 'reto', 'ra')
NIVELES = 5


# ───────────── datos ─────────────
def rol(root=ROOT):
    s = Path(root) / 'canvas' / 'silabo.json'
    if not s.exists():
        return None
    return json.loads(s.read_text(encoding='utf-8')).get('pis_rol')


def documentos(root=ROOT):
    f = Path(root) / 'fuentes' / 'pis'
    return sorted(p for p in f.glob('*') if p.is_file() and not p.name.startswith('.') and p.name.upper() != 'LEEME.TXT') if f.is_dir() else []


def errores_datos(d):
    """Lista de problemas de estructura: los dos idiomas deben tener las mismas piezas."""
    out = []
    if not isinstance(d, dict) or d.get('version') != 1:
        return ['canvas/pis.json: falta "version": 1.']
    for lang in ('es', 'en'):
        b = d.get(lang)
        if not isinstance(b, dict):
            out.append(f'falta el bloque "{lang}"'); continue
        for k in TEXTO:
            if not isinstance(b.get(k), str) or not b[k].strip():
                out.append(f'{lang}.{k}: texto obligatorio')
        pfs = b.get('proyectos') or []
        if not pfs or any(not (isinstance(p, dict) and p.get('nombre') and p.get('ra') and p.get('aporte')) for p in pfs):
            out.append(f'{lang}.proyectos: cada proyecto formativo necesita nombre, ra y aporte')
        ms = b.get('momentos') or []
        if not ms:
            out.append(f'{lang}.momentos: al menos un momento')
        for i, m in enumerate(ms, 1):
            for k in ('nombre', 'fechas', 'proposito', 'evidencia'):
                if not isinstance(m.get(k), str) or not m[k].strip():
                    out.append(f'{lang}.momentos[{i}].{k}: obligatorio')
            if not isinstance(m.get('actividades'), list) or not m['actividades']:
                out.append(f'{lang}.momentos[{i}].actividades: lista no vacía')
        ev = b.get('evidencia') or {}
        if not (isinstance(ev, dict) and ev.get('titulo') and ev.get('descripcion')):
            out.append(f'{lang}.evidencia: titulo y descripcion')
        rb = b.get('rubrica') or {}
        if len(rb.get('niveles') or []) != NIVELES:
            out.append(f'{lang}.rubrica.niveles: deben ser los cinco niveles (Receptivo → Cocreativo)')
        inds = rb.get('indicadores') or []
        if not inds or any(len(x.get('descriptores') or []) != NIVELES or not x.get('nombre') for x in inds):
            out.append(f'{lang}.rubrica.indicadores: cada indicador con nombre y cinco descriptores')
    if not out:
        es, en = d['es'], d['en']
        pares = [('proyectos', len(es['proyectos']), len(en['proyectos'])), ('momentos', len(es['momentos']), len(en['momentos'])),
                 ('rubrica.indicadores', len(es['rubrica']['indicadores']), len(en['rubrica']['indicadores'])),
                 ('evidencia.trabajos', len(es['evidencia'].get('trabajos') or []), len(en['evidencia'].get('trabajos') or [])),
                 ('evidencia.componentes', len(es['evidencia'].get('componentes') or []), len(en['evidencia'].get('componentes') or []))]
        pares += [(f'momentos[{i}].actividades', len(a['actividades']), len(b['actividades'])) for i, (a, b) in enumerate(zip(es['momentos'], en['momentos']), 1)]
        out += [f'{k}: {a} en español y {b} en inglés' for k, a, b in pares if a != b]
    return out


def cargar(root=ROOT):
    datos = Path(root) / 'canvas' / 'pis.json'
    if not datos.exists():
        return None, ['falta canvas/pis.json']
    try:
        d = json.loads(datos.read_text(encoding='utf-8'))
    except ValueError as ex:
        return None, [f'canvas/pis.json no es JSON válido: {ex}']
    return d, errores_datos(d)


def verificar(root=ROOT):
    root = Path(root)
    datos = root / 'canvas' / 'pis.json'
    r = rol(root)
    d, errs = cargar(root) if datos.exists() else (None, [])
    res = {'rol': r, 'documentos': [p.relative_to(root).as_posix() for p in documentos(root)], 'datos': datos.exists(),
           'origen': (d or {}).get('origen', {}), 'errores': [], 'pendientes': []}
    if r not in ROLES:
        res['errores'].append('canvas/silabo.json → pis_rol sin responder: pregunta al docente si su proyecto formativo es el '
                              'articulador del PIS («articulador»), si aporta a un PIS de otro proyecto formativo («aportante») '
                              'o si el período no tiene PIS («no_aplica»).')
    elif r == 'articulador':
        if not res['documentos']:
            res['errores'].append('Falta el documento del PIS en fuentes/pis/ (obligatorio para el proyecto formativo articulador).')
        if not datos.exists():
            res['errores'].append('Falta canvas/pis.json: transcribe el documento del PIS en español e inglés (ver la referencia PIS de la skill).')
        res['errores'] += [f'canvas/pis.json: {e}' for e in errs if datos.exists()]
    elif r == 'aportante':
        if not datos.exists():
            res['pendientes'].append('Pide al docente del proyecto formativo articulador que comparta su PIS (en su aula: '
                                     'python3 control/pis.py exportar) y luego impórtalo aquí con python3 control/pis.py importar <paquete>.')
        else:
            res['errores'] += [f'canvas/pis.json: {e}' for e in errs]
    res['estado'] = 'con_errores' if res['errores'] else 'pendiente' if res['pendientes'] else ('listo' if r in ('articulador', 'aportante') else 'no_aplica')
    return res


# ───────────── vista del aula ─────────────
def e(t):
    return html.escape(str(t or ''))


def bi(es, en, tag='span'):
    return f'<{tag} lang="es">{e(es)}</{tag}><{tag} lang="en">{e(en)}</{tag}>'


def vista_html(d):
    """Vista «PIS» del aula (#/pis): proyecto, momentos, rúbrica y evidencia integradora, en español e inglés."""
    es, en = d['es'], d['en']
    compartido = d.get('origen', {}).get('rol') == 'compartido'
    nav = [('proyecto', 'El proyecto', 'The project'), ('momentos', 'Momentos', 'Stages'), ('rubrica', 'Rúbrica', 'Rubric'),
           ('evidencia', 'Evidencia integradora', 'Integrating evidence')]
    navs = ''.join(f'<a href="#/pis/{k}" data-sub="{k}"><span lang="es">{a}</span><span lang="en">{b}</span></a>' for k, a, b in nav)
    filas_pf = ''.join(f'<tr><td><strong>{bi(a["nombre"], b["nombre"])}</strong>' + ('<br><small><span lang="es">articulador</span><span lang="en">articulating</span></small>' if a.get('articulador') else '')
                       + f'</td><td>{bi(a["ra"], b["ra"])}</td><td>{bi(a["aporte"], b["aporte"])}</td></tr>' for a, b in zip(es['proyectos'], en['proyectos']))
    origen = ('<p class="muted"><span lang="es">Compartido por el proyecto formativo articulador: ' + e(es['pf_articulador']) + '.</span>'
              '<span lang="en">Shared by the articulating course: ' + e(en['pf_articulador']) + '.</span></p>') if compartido else ''
    proyecto = (f'<article class="sub" data-sub="proyecto"><div class="sub-head"><span class="eyebrow"><span lang="es">PIS</span><span lang="en">PIS</span></span>'
                f'<h2>{bi(es["titulo"], en["titulo"])}</h2>{origen}</div>'
                f'<div class="card"><h3><span lang="es">Necesidad o reto</span><span lang="en">Need or challenge</span></h3><p>{bi(es["reto"], en["reto"])}</p>'
                + (f'<h3><span lang="es">Propósito</span><span lang="en">Purpose</span></h3><p>{bi(es["proposito"], en["proposito"])}</p>' if es.get('proposito') else '')
                + f'<h3><span lang="es">Resultado de aprendizaje del PIS</span><span lang="en">PIS learning outcome</span></h3><p><strong>{bi(es["ra"], en["ra"])}</strong></p></div>'
                f'<div class="card"><h3><span lang="es">Proyectos formativos que lo integran</span><span lang="en">Courses that take part</span></h3>'
                f'<div class="table-wrap"><table class="table"><thead><tr><th><span lang="es">Proyecto formativo</span><span lang="en">Course</span></th>'
                f'<th><span lang="es">Resultado de aprendizaje</span><span lang="en">Learning outcome</span></th><th><span lang="es">Aporte</span><span lang="en">Contribution</span></th></tr></thead>'
                f'<tbody>{filas_pf}</tbody></table></div></div>'
                + (f'<div class="card"><h3><span lang="es">Competencias del perfil de egreso</span><span lang="en">Graduate profile competences</span></h3><ul>'
                   + ''.join(f'<li>{bi(a, b)}</li>' for a, b in zip(es['competencias'], en.get('competencias') or [])) + '</ul></div>' if es.get('competencias') else '')
                + '</article>')
    mom = ''
    for a, b in zip(es['momentos'], en['momentos']):
        hito = f'<p class="callout callout--practica"><strong>{bi(a["hito"], b.get("hito", ""))}</strong></p>' if a.get('hito') else ''
        mom += (f'<details class="fold" open><summary>{bi(a["nombre"], b["nombre"])} · {e(a["fechas"])}</summary><div class="fold__body">'
                f'<p>{bi(a["proposito"], b["proposito"])}</p>{hito}'
                f'<h4><span lang="es">Actividades</span><span lang="en">Activities</span></h4><ol>'
                + ''.join(f'<li>{bi(x, y)}</li>' for x, y in zip(a['actividades'], b['actividades']))
                + f'</ol><h4><span lang="es">Evidencia parcial</span><span lang="en">Partial evidence</span></h4><p>{bi(a["evidencia"], b["evidencia"])}</p></div></details>')
    momentos = (f'<article class="sub" data-sub="momentos"><div class="sub-head"><h2><span lang="es">Momentos del PIS</span><span lang="en">PIS stages</span></h2></div>{mom}</article>')
    rb_es, rb_en = es['rubrica'], en['rubrica']
    cab = ''.join(f'<th>{bi(x, y)}</th>' for x, y in zip(rb_es['niveles'], rb_en['niveles']))
    filas = ''.join(f'<tr><th scope="row">{bi(a["nombre"], b["nombre"])}</th>' + ''.join(f'<td>{bi(x, y)}</td>' for x, y in zip(a['descriptores'], b['descriptores'])) + '</tr>'
                    for a, b in zip(rb_es['indicadores'], rb_en['indicadores']))
    reglas = ''.join(f'<li>{bi(x, y)}</li>' for x, y in zip(rb_es.get('reglas') or [], rb_en.get('reglas') or []))
    rubrica = (f'<article class="sub" data-sub="rubrica"><div class="sub-head"><h2><span lang="es">Rúbrica analítica del PIS</span><span lang="en">PIS analytic rubric</span></h2></div>'
               f'<div class="table-wrap"><table class="table"><thead><tr><th><span lang="es">Indicador</span><span lang="en">Indicator</span></th>{cab}</tr></thead><tbody>{filas}</tbody></table></div>'
               + (f'<div class="card"><h3><span lang="es">Reglas de valoración</span><span lang="en">Grading rules</span></h3><ul>{reglas}</ul></div>' if reglas else '') + '</article>')
    ev_es, ev_en = es['evidencia'], en['evidencia']
    trabajos = ''.join(f'<li>{bi(x, y)}</li>' for x, y in zip(ev_es.get('trabajos') or [], ev_en.get('trabajos') or []))
    comps = ''.join(f'<li>{bi(x, y)}</li>' for x, y in zip(ev_es.get('componentes') or [], ev_en.get('componentes') or []))
    evidencia = (f'<article class="sub" data-sub="evidencia"><div class="sub-head"><h2>{bi(ev_es["titulo"], ev_en["titulo"])}</h2>'
                 f'<p>{bi(ev_es["descripcion"], ev_en["descripcion"])}</p></div>'
                 + (f'<div class="card"><h3><span lang="es">Trabajos que integra</span><span lang="en">Projects it brings together</span></h3><ol>{trabajos}</ol></div>' if trabajos else '')
                 + (f'<div class="card"><h3><span lang="es">Componentes verificables</span><span lang="en">Verifiable components</span></h3><ul>{comps}</ul></div>' if comps else '')
                 + '</article>')
    return ('<section class="view" data-view="pis" aria-labelledby="pis-titulo" hidden>\n'
            '  <header class="week-hero"><div class="week-hero__inner"><div>'
            '<span class="eyebrow"><span lang="es">Proyecto Interdisciplinario Socioformativo</span><span lang="en">Interdisciplinary Socio-formative Project</span></span>'
            f'<h1 class="week-hero__title" id="pis-titulo">{bi(es["titulo"], en["titulo"])}</h1>'
            f'<p>{bi(es["pf_articulador"], en["pf_articulador"])}</p></div></div></header>\n'
            '  <div class="week"><nav class="week-nav" data-i18n=\'{"aria-label": ["Secciones del PIS", "PIS sections"]}\'>'
            f'<p class="week-nav__label">PIS</p>{navs}</nav><div class="week-body">\n'
            f'{proyecto}\n{momentos}\n{rubrica}\n{evidencia}\n  </div></div>\n</section>\n')


# ───────────── compartir ─────────────
def exportar(con_documentos=False):
    d, errs = cargar()
    if errs:
        sys.exit('No se puede exportar: ' + '; '.join(errs))
    if rol() != 'articulador':
        sys.exit('Solo el aula del proyecto formativo articulador exporta el PIS (canvas/silabo.json → pis_rol).')
    clave = json.loads((ROOT / 'hub/src/course.json').read_text(encoding='utf-8')).get('key', 'aula')
    marca = datetime.now(timezone.utc).strftime('%Y%m%d')
    destino = ROOT / 'pis' / 'compartir' / f'PIS-{clave}-{marca}.zip'
    destino.parent.mkdir(parents=True, exist_ok=True)
    datos = dict(d, origen={**d.get('origen', {}), 'rol': 'articulador', 'aula': clave,
                           'exportado': datetime.now(timezone.utc).isoformat(timespec='seconds')})
    cuerpo = json.dumps(datos, ensure_ascii=False, indent=1) + '\n'
    with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('pis.json', cuerpo)
        z.writestr('LEEME.txt', 'PIS compartido por el proyecto formativo articulador.\n'
                   'En el aula del proyecto formativo que aporta, el asistente lo importa con:\n'
                   '    python3 control/pis.py importar <este archivo>\n'
                   'Así esa aula y su curso de Canvas muestran el mismo PIS (vista «PIS» y módulo «PIS»).\n'
                   f'Huella de pis.json: {hashlib.sha256(cuerpo.encode()).hexdigest()}\n')
        if con_documentos:
            for p in documentos():
                z.write(p, f'documentos/{p.name}')
    return destino


def importar(origen: Path):
    if rol() == 'articulador':
        sys.exit('Esta aula es la articuladora del PIS: sus datos se transcriben del documento, no se importan.')
    if origen.suffix.lower() == '.zip':
        with zipfile.ZipFile(origen) as z:
            d = json.loads(z.read('pis.json').decode('utf-8'))
    else:
        d = json.loads(origen.read_text(encoding='utf-8'))
    errs = errores_datos(d)
    if errs:
        sys.exit('El PIS recibido no es válido: ' + '; '.join(errs))
    previo = DATOS.read_bytes() if DATOS.exists() else None
    d['origen'] = {**d.get('origen', {}), 'rol': 'compartido', 'importado': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                   'archivo': origen.name}
    DATOS.parent.mkdir(parents=True, exist_ok=True)
    if previo:
        (DATOS.with_suffix('.anterior.json')).write_bytes(previo)
    DATOS.write_text(json.dumps(d, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('orden', nargs='?', default='verificar', choices=['verificar', 'exportar', 'importar'])
    ap.add_argument('archivo', nargs='?', type=Path)
    ap.add_argument('--con-documentos', action='store_true', help='incluir los documentos de fuentes/pis/ al exportar')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    if a.orden == 'exportar':
        p = exportar(a.con_documentos)
        print(json.dumps({'paquete': p.relative_to(ROOT).as_posix()}) if a.json else
              f'PIS listo para compartir: {p.relative_to(ROOT)}\nEnvíalo al docente de cada proyecto formativo que aporta; su asistente lo importa con control/pis.py importar.')
        return 0
    if a.orden == 'importar':
        if not a.archivo:
            sys.exit('Indica el paquete recibido: python3 control/pis.py importar PIS-….zip')
        d = importar(a.archivo)
        print(json.dumps({'importado': True, 'titulo': d['es']['titulo']}, ensure_ascii=False) if a.json else
              f'PIS importado: «{d["es"]["titulo"]}». Recompila (python3 hub/build.py) y genera Canvas para ver la vista y el módulo PIS.')
        return 0
    r = verificar()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
    else:
        print(f'PIS · rol: {r["rol"] or "sin responder"} · estado: {r["estado"]}')
        for x in r['documentos']:
            print('   documento:', x)
        for x in r['errores']:
            print('   ✗', x)
        for x in r['pendientes']:
            print('   ·', x)
    return 1 if r['errores'] else 0


if __name__ == '__main__':
    sys.exit(main())
