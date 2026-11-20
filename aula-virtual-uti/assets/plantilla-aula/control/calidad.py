#!/usr/bin/env python3
"""Revisión de calidad pedagógica por unidad, según el modelo socioformativo de la skill.

    python3 control/calidad.py                 # todas las unidades → control/CALIDAD.md y control/calidad.json
    python3 control/calidad.py --unidad u1     # una unidad
    python3 control/calidad.py --json          # resultado para el asistente

Comprueba en el contenido de cada unidad (hub/src/content/uN/) lo que un docente revisaría primero:
  · ruta: resultados de aprendizaje (RA) y evidencia o producto declarados en el resumen;
  · ejemplos y errores frecuentes en el manual (callout--concepto/practica y callout--error);
  · práctica con pasos, entrega, rúbrica con los cinco niveles y desafío con IA;
  · cuestionario con al menos 5 preguntas, retroalimentación para CADA opción («por qué») y enlace a la teoría;
  · presentación con nota para el docente en cada diapositiva;
  · OBLIGATORIO: cada temática (sesión) con al menos una animación planificada, hecha y usada en la presentación;
  · animaciones con escenas explicadas, «Qué observar», enlaces teoría ↔ práctica y al menos 2 controles;
  · marcas [COMPLETAR] pendientes.
Es una revisión de presencia y estructura: NO juzga si los ejemplos son buenos ni si el nivel es el adecuado.
Eso lo decide el docente con la lista de CALIDAD.md; su conformidad se registra con control/estado.py registrar.
Código 1 si alguna comprobación obligatoria falla.
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'hub' / 'src' / 'content'
NIVELES = ('Receptivo', 'Resolutivo', 'Reflexivo', 'Crítico', 'Cocreativo')
REVISION_DOCENTE = [
    'Los RA y la evidencia de la unidad son los del sílabo vigente y se entienden desde el resumen.',
    'Los ejemplos son pertinentes para la carrera y el contexto de los estudiantes.',
    'La práctica conduce a la evidencia y su rúbrica valora lo que pide el RA.',
    'Las preguntas evalúan comprensión (no solo memoria) y la retroalimentación ayuda a corregir.',
    'El nivel, la extensión y el tiempo estimado son realistas para la semana.',
]


def leer(u, nombre):
    fs = sorted((CONTENT / u).glob(f'*-{nombre}.html')) if (CONTENT / u).is_dir() else []
    return fs[0].read_text(encoding='utf-8') if fs else None


def texto(h):
    return html.unescape(re.sub(r'<[^>]+>', ' ', h or ''))


def archivo_anim(ident):
    return next(iter(sorted((ROOT / 'hub/src/js/anim').glob(ident.lower().replace('.', '-') + '-*.js'))), None)


def temas_unidad(unidad):
    """[(sesión, tema)] de la unidad: course.json → sessions, con el tema de canvas/silabo.json si existe."""
    temas = {}
    s = ROOT / 'canvas' / 'silabo.json'
    if s.exists():
        d = json.loads(s.read_text(encoding='utf-8'))
        mom = next((m for m in d.get('momentos') or [] if m.get('n') == unidad.get('moment')), None)
        temas = {x.get('n'): x.get('tema', '') for x in (mom or {}).get('sesiones') or []}
    return [(n, temas.get(n, '')) for n in unidad.get('sessions') or []]


def animaciones_unidad(unidad, pres=None):
    """Obligatorio: cada temática (sesión) de la unidad tiene al menos una animación planificada en course.json
    («sesion»), hecha en hub/src/js/anim/ y usada en la presentación de la unidad (data-anim). La vista Animaciones
    las muestra todas a partir de course.json."""
    if pres is None:
        fs = sorted((CONTENT / unidad['id']).glob('*-presentacion.html')) if (CONTENT / unidad['id']).is_dir() else []
        pres = fs[0].read_text(encoding='utf-8') if fs else ''
    anims = unidad.get('anims') or []
    en_pres = set(re.findall(r'data-anim="([^"]+)"', pres or ''))
    out = []
    sesiones = temas_unidad(unidad) or [(None, '')]
    for n, tema in sesiones:
        suyas = [a for a in anims if n is None or a.get('sesion') == n or n in (a.get('sesiones') or [])]
        etiqueta = f'Sesión {n}' + (f' · {tema}' if tema else '') if n is not None else 'Unidad'
        if not suyas:
            out.append({'que': f'{etiqueta}: animación planificada', 'ok': False,
                        'detalle': 'ninguna animación de course.json tiene «sesion»: ' + str(n) if n is not None else 'la unidad no tiene animaciones'})
            continue
        for a in suyas:
            hecha, usada = archivo_anim(a['id']) is not None, a['id'] in en_pres
            falta = [x for x, ok in (('archivo en hub/src/js/anim/', hecha), ('en la presentación (data-anim)', usada)) if not ok]
            out.append({'que': f'{etiqueta}: {a["id"]} hecha y en la presentación', 'ok': not falta,
                        'detalle': ('falta: ' + ', '.join(falta)) if falta else 'en Animaciones y en la presentación'})
    return out


def animaciones_pendientes():
    """Para generar_canvas.py y el panel: lista de temáticas sin animación completa en todo el curso."""
    course = json.loads((ROOT / 'hub/src/course.json').read_text(encoding='utf-8'))
    return [f'{u["id"].upper()} · {x["que"]} ({x["detalle"]})' for u in course['units'] for x in animaciones_unidad(u) if not x['ok']]


def revisar_unidad(u, anims, unidad=None):
    filas = []

    def chk(area, que, ok, detalle='', obligatorio=True):
        filas.append({'area': area, 'que': que, 'estado': 'ok' if ok else ('falta' if obligatorio else 'aviso'), 'detalle': detalle})

    res = leer(u, 'resumen')
    chk('Ruta', 'Resumen de la unidad', res is not None)
    if res:
        ras = sorted(set(re.findall(r'\bRA\s?\d+\b', texto(res))))
        chk('Ruta', 'Resultados de aprendizaje (RA) visibles', bool(ras), ', '.join(ras) or 'el resumen no nombra ningún RA')
        chk('Ruta', 'Evidencia o producto de la unidad', bool(re.search(r'evidencia|producto|entrega|evidence|deliverable', texto(res), re.I)),
            '' if re.search(r'evidencia|producto|entrega', texto(res), re.I) else 'no se menciona qué se entrega')
    man = leer(u, 'manual')
    chk('Manual', 'Manual de la unidad', man is not None)
    if man:
        ej = len(re.findall(r'callout--(?:concepto|practica)', man)) + len(re.findall(r'\bEjemplo\b', texto(man)))
        chk('Manual', 'Ejemplos', ej > 0, f'{ej} ejemplo(s) o casos')
        er = len(re.findall(r'callout--error', man))
        chk('Manual', 'Errores frecuentes', er > 0, f'{er} recuadro(s) de error frecuente', obligatorio=False)
    pra = leer(u, 'practica')
    chk('Práctica', 'Guía de práctica', pra is not None)
    if pra:
        t = texto(pra)
        pasos = '<ol' in pra or len(re.findall(r'<li\b', pra)) >= 3 or len(re.findall(r'\bPaso \d', t)) >= 3
        chk('Práctica', 'Pasos de trabajo', pasos, '' if pasos else 'no hay una lista de pasos')
        chk('Práctica', 'Qué entregar (evidencia)', bool(re.search(r'entreg|evidencia', t, re.I)))
        faltan = [n for n in NIVELES if n.casefold() not in t.casefold()]
        chk('Práctica', 'Rúbrica con los cinco niveles', not faltan, 'faltan: ' + ', '.join(faltan) if faltan else 'Receptivo → Cocreativo')
        chk('Práctica', 'Desafío con IA declarado', bool(re.search(r'@@desafio:|callout--ia', pra)))
    quiz = leer(u, 'quiz')
    chk('Evaluación', 'Cuestionario de autoevaluación', quiz is not None)
    if quiz:
        m = re.search(r'<script type="application/json">(.*?)</script>', quiz, re.S)
        try:
            qs = json.loads(m[1])['questions'] if m else []
        except (ValueError, KeyError):
            qs = None
        if qs is None:
            chk('Evaluación', 'Preguntas legibles', False, 'el JSON del cuestionario no se puede leer')
        else:
            chk('Evaluación', 'Al menos 5 preguntas', len(qs) >= 5, f'{len(qs)} pregunta(s)', obligatorio=False)
            sin_por_que = [i + 1 for i, q in enumerate(qs) if len(q.get('why') or []) != len(q.get('opts') or []) or not all(
                isinstance(w, dict) and w.get('es') and w.get('en') for w in q.get('why') or [])]
            chk('Evaluación', 'Retroalimentación en cada opción (ES y EN)', not sin_por_que,
                f'preguntas sin «por qué» completo: {sin_por_que}' if sin_por_que else f'{len(qs)} pregunta(s) con retroalimentación')
            sin_ref = [i + 1 for i, q in enumerate(qs) if not q.get('ref')]
            chk('Evaluación', 'Cada pregunta remite a la teoría', not sin_ref, f'sin enlace: {sin_ref}' if sin_ref else '', obligatorio=False)
            mal = [i + 1 for i, q in enumerate(qs) if not isinstance(q.get('ans'), int) or not 0 <= q['ans'] < len(q.get('opts') or [])]
            chk('Evaluación', 'Respuesta correcta válida', not mal, f'preguntas: {mal}' if mal else '')
    pres = leer(u, 'presentacion')
    unidad = unidad or {'id': u, 'anims': anims}
    if pres:
        n = len(re.findall(r'<section class="slide', pres))
        notas = len(re.findall(r'<aside class="notes"', pres))
        chk('Presentación', 'Nota para el docente en cada diapositiva', n > 0 and notas >= n, f'{notas} nota(s) para {n} diapositiva(s)', obligatorio=False)
    for x in animaciones_unidad(unidad, pres):              # obligatorio: cada temática con su animación
        chk('Animaciones', x['que'], x['ok'], x['detalle'])
    for a in anims:
        archivo = archivo_anim(a['id'])
        if not archivo:
            continue                                         # ya informado arriba como falta
        js = archivo.read_text(encoding='utf-8')
        escenas = len(re.findall(r'\bdur\s*:', js))
        controles = len(re.findall(r"type\s*:\s*'(?:range|select|toggle|button|number)'", js))
        faltan = [x for x, ok in (('escenas 4–8', 4 <= escenas <= 8), ('«Qué observar»', 'observe' in js),
                                   ('teoría y práctica', 'theory' in js and 'practice' in js), ('≥ 2 controles', controles >= 2)) if not ok]
        chk('Animaciones', f'{a["id"]} cumple la vara de calidad', not faltan,
            f'{escenas} escena(s), {controles} control(es)' + (' · falta: ' + ', '.join(faltan) if faltan else ''), obligatorio=False)
    pend = sum(len(re.findall(r'\[COMPLETAR', f.read_text(encoding='utf-8'))) for f in (CONTENT / u).glob('*.html')) if (CONTENT / u).is_dir() else 0
    chk('General', 'Sin marcas [COMPLETAR]', pend == 0, f'{pend} marca(s) por completar' if pend else '')
    return filas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--unidad')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    course = json.loads((ROOT / 'hub/src/course.json').read_text(encoding='utf-8'))
    unidades = [u for u in course['units'] if not a.unidad or u['id'] == a.unidad]
    if not unidades:
        sys.exit(f'No existe la unidad {a.unidad} en hub/src/course.json')
    resultado = {'fecha': datetime.now(timezone.utc).isoformat(), 'unidades': []}
    for u in unidades:
        filas = revisar_unidad(u['id'], u.get('anims') or [], u)
        titulo = (u.get('title') or {}).get('es', u['id'])
        resultado['unidades'].append({'id': u['id'], 'titulo': titulo, 'comprobaciones': filas,
                                      'faltan': sum(f['estado'] == 'falta' for f in filas), 'avisos': sum(f['estado'] == 'aviso' for f in filas)})
    resultado['resultado'] = 'con_faltas' if any(u['faltan'] for u in resultado['unidades']) else 'sin_faltas'
    (ROOT / 'control').mkdir(exist_ok=True)
    (ROOT / 'control/calidad.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    icono = {'ok': '✅', 'falta': '❌', 'aviso': '⚠️'}
    md = ['# Calidad pedagógica por unidad', '',
          f'Revisión automática del {resultado["fecha"][:10]}: comprueba que cada unidad tenga las piezas del modelo socioformativo. '
          'No juzga la calidad de los ejemplos ni el nivel: eso lo decide el docente con la lista de cada unidad. '
          'La accesibilidad se revisa aparte (`node hub/tools/accesibilidad.mjs` → `control/ACCESIBILIDAD.md`).', '']
    for u in resultado['unidades']:
        md += [f'## {u["id"].upper()} · {u["titulo"]}', '',
               f'**{u["faltan"]} falta(s) · {u["avisos"]} aviso(s)**', '', '| Área | Comprobación | Estado | Detalle |', '|---|---|---|---|']
        md += [f'| {f["area"]} | {f["que"]} | {icono[f["estado"]]} | {f["detalle"].replace("|", "/")} |' for f in u['comprobaciones']]
        md += ['', '**Revisión del docente** (marca cuando lo hayas comprobado; el asistente registra tu conformidad en ESTADO.md):', '']
        md += [f'- [ ] {x}' for x in REVISION_DOCENTE] + ['']
    (ROOT / 'control/CALIDAD.md').write_text('\n'.join(md), encoding='utf-8', newline='\n')
    if a.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=1))
    else:
        for u in resultado['unidades']:
            print(f'{"✗" if u["faltan"] else "✓"} {u["id"]} · {u["titulo"]}: {u["faltan"]} falta(s), {u["avisos"]} aviso(s)')
            for f in u['comprobaciones']:
                if f['estado'] != 'ok':
                    print(f'    {"falta" if f["estado"] == "falta" else "aviso"}: {f["area"]} · {f["que"]}' + (f' ({f["detalle"]})' if f['detalle'] else ''))
        print('→ control/CALIDAD.md')
    return 1 if resultado['resultado'] == 'con_faltas' else 0


if __name__ == '__main__':
    sys.exit(main())
