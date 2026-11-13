#!/usr/bin/env python3
"""Revisa canvas/silabo.json antes de generar el paquete de Canvas: estructura, fechas, horas, rúbricas y
correspondencia con las unidades del aula (hub/src/course.json). Explica cada problema en lenguaje llano.

    python3 canvas/validar_silabo.py            → ERRORES (impiden generar) y AVISOS (conviene revisar)

El esquema está en canvas/LEEME.md. Código de salida 1 si hay errores.
"""
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NIVELES = ['Receptivo', 'Resolutivo', 'Reflexivo', 'Crítico', 'Cocreativo']
METACOMPETENCIAS = [
    'Pensamiento sociocrítico y sistémico para la toma de decisiones estratégicas',
    'Gobernanza ética de tecnologías digitales e IA',
    'Innovación y emprendimiento sostenible con impacto territorial',
    'Metacognición estratégica y proyecto ético de vida',
    'Liderazgo colaborativo e intercultural para la transformación territorial',
]
errores, avisos = [], []


def fecha(s, donde):
    try:
        return datetime.datetime.strptime(s, '%d/%m/%Y').date()
    except (ValueError, TypeError):
        errores.append(f'{donde}: la fecha «{s}» debe tener el formato dd/mm/aaaa.')
        return None


def texto(d, k, donde, obligatorio=True):
    v = d.get(k)
    if not v or (isinstance(v, str) and ('[COMPLETAR' in v or not v.strip())):
        (errores if obligatorio else avisos).append(f'{donde}: falta «{k}».')
        return False
    return True


def rubrica(rows, donde):
    if not rows:
        avisos.append(f'{donde}: no tiene rúbrica. El modelo educativo pide evaluar cada evidencia con un instrumento que el estudiante conoce desde el inicio.')
        return
    for i, r in enumerate(rows, 1):
        if len(r) != 6:
            errores.append(f'{donde}, indicador {i}: debe tener 6 textos (indicador + {", ".join(NIVELES)}); tiene {len(r)}.')


def main() -> int:
    f = HERE / 'silabo.json'
    if not f.exists():
        print('No existe canvas/silabo.json. Cópialo de canvas/silabo.ejemplo.json y llénalo con el sílabo vigente.')
        return 1
    try:
        D = json.loads(f.read_text(encoding='utf-8'))
    except json.JSONDecodeError as ex:
        print(f'canvas/silabo.json no es un JSON válido: {ex}')
        return 1
    course = json.loads((ROOT / 'hub/src/course.json').read_text(encoding='utf-8'))
    unidades = {u['n'] for u in course['units']}

    c = D.get('curso') or {}
    for k in ('nombre', 'periodo', 'inicio', 'fin'):
        texto(c, k, 'curso')
    ini, fin = fecha(c.get('inicio'), 'curso.inicio'), fecha(c.get('fin'), 'curso.fin')
    if not c.get('canvas_id'):
        avisos.append('curso.canvas_id: sin el número del curso en Canvas (el de la dirección …/courses/NÚMERO) los archivos de «pegar» llevan enlaces incompletos.')
    doc = D.get('docente') or {}
    texto(doc, 'nombre', 'docente')
    texto(doc, 'email', 'docente', False)
    for k in ('competencia_perfil', 'competencia_pf', 'metacompetencia', 'contribucion', 'problema', 'reto', 'producto_final'):
        texto(D, k, 'sílabo')
    if D.get('metacompetencia') and D['metacompetencia'].strip().lower() not in [m.lower() for m in METACOMPETENCIAS]:
        avisos.append('metacompetencia: no coincide con ninguna de las cinco de la plantilla institucional:\n      - ' + '\n      - '.join(METACOMPETENCIAS))
    ras = D.get('ra') or []
    if not ras:
        errores.append('ra: no hay resultados de aprendizaje.')
    for r in ras:
        if len(r) < 3 or not r[2]:
            avisos.append(f'{r[0] if r else "RA"}: falta la evidencia de desempeño con que se demuestra.')
    nombres_ra = {r[0].replace(' ', '') for r in ras if r}
    if not D.get('metodologias'):
        errores.append('metodologias: falta la metodología activa (la primera de la lista es la principal).')
    rubrica(D.get('rubrica_final'), 'rubrica_final (producto final)')
    if not D.get('bibliografia'):
        avisos.append('bibliografia: vacía. La plantilla pide bibliografía básica en APA 7, de preferencia de la Biblioteca Virtual.')
    if not D.get('pis'):
        avisos.append('pis: el sílabo no declara Proyecto Interdisciplinario Socioformativo; las tareas PIS de la plantilla quedan como están.')

    ms = D.get('momentos') or []
    if not ms:
        errores.append('momentos: el sílabo debe tener al menos un momento.')
    if [M.get('n') for M in ms] != list(range(1, len(ms) + 1)):
        errores.append('momentos: deben numerarse 1, 2, 3… en orden.')
    usadas, previa, suma = set(), None, dict(docente=0, practico=0, autonomo=0)
    for M in ms:
        dm = f'Momento {M.get("n")}'
        for k in ('titulo', 'fechas', 'evidencia'):
            texto(M, k, dm)
        if M.get('fechas') and ' al ' not in M['fechas']:
            errores.append(f'{dm}: «fechas» debe ser «dd/mm/aaaa al dd/mm/aaaa».')
        for r in M.get('ra') or []:
            if r.replace(' ', '') not in nombres_ra:
                errores.append(f'{dm}: el resultado «{r}» no está en la lista «ra».')
        rubrica(M.get('rubrica'), f'{dm}, rúbrica')
        texto(M, 'ia', dm + ' (política de IA del momento)', False)
        ss = M.get('sesiones') or []
        if not ss:
            errores.append(f'{dm}: no tiene sesiones.')
        if [s.get('n') for s in ss] != list(range(1, len(ss) + 1)):
            errores.append(f'{dm}: las sesiones deben numerarse 1, 2, 3… en orden.')
        for s in ss:
            ds = f'{dm}, sesión {s.get("n")}'
            a, b = fecha(s.get('desde'), ds + ' (desde)'), fecha(s.get('hasta'), ds + ' (hasta)')
            if a and b and a > b:
                errores.append(f'{ds}: «desde» es posterior a «hasta».')
            if a and previa and a <= previa:
                errores.append(f'{ds}: empieza antes de que termine la sesión anterior.')
            previa = b or previa
            if a and ini and a < ini or b and fin and b > fin:
                avisos.append(f'{ds}: queda fuera de las fechas del curso ({c.get("inicio")}–{c.get("fin")}).')
            texto(s, 'tema', ds, False)
            for k in ('docente', 'practico', 'autonomo', 'contenidos'):
                texto(s, k, ds, False)
            for k in suma:
                suma[k] += (s.get('horas') or {}).get(k, 0) or 0
            aula = s.get('aula') or {}
            us = aula.get('unidad')
            us = [us] if isinstance(us, int) else list(us or [])
            if not us and not aula.get('repaso'):
                us = [u['n'] for u in course['units'] if u.get('moment') == M.get('n') and s.get('n') in (u.get('sessions') or [])]
            for n in us + list(aula.get('repaso') or []):
                if n not in unidades:
                    errores.append(f'{ds}: remite a la unidad {n}, que no existe en hub/src/course.json.')
            usadas.update(us)
            if not us and not aula.get('repaso'):
                avisos.append(f'{ds}: no tiene unidad del aula asociada (ni «repaso»): su página no enlazará recursos del aula.')
    for n in sorted(unidades - usadas):
        avisos.append(f'Unidad {n} del aula: ninguna sesión del sílabo la usa.')
    h = c.get('horas') or {}
    for k, nombre in (('docente', 'contacto con el docente'), ('practico', 'práctico-experimentales'), ('autonomo', 'trabajo autónomo')):
        if h.get(k) and suma[k] and h[k] != suma[k]:
            avisos.append(f'Horas de {nombre}: las sesiones suman {suma[k]} y el curso declara {h[k]}.')

    ids = set()
    for g in D.get('practicas') or []:
        dg = f'Práctica {g.get("id")}'
        if not g.get('id') or g['id'] in ids:
            errores.append(f'{dg}: cada práctica necesita un «id» único (PR1, PR2…).')
        ids.add(g.get('id'))
        texto(g, 'titulo', dg)
        M = next((M for M in ms if M.get('n') == g.get('momento')), None)
        if not M or not any(s.get('n') == g.get('sesion') for s in M.get('sesiones') or []):
            errores.append(f'{dg}: «momento» y «sesion» deben existir en el sílabo.')
        if g.get('unidad') and g['unidad'] not in unidades:
            errores.append(f'{dg}: la unidad {g["unidad"]} no existe en el aula.')
        if g.get('archivo') and not (ROOT / g['archivo']).exists():
            errores.append(f'{dg}: no existe el archivo {g["archivo"]}.')
        texto(g, 'entregable', dg, False)
    raw = f.read_text(encoding='utf-8')
    pend = len(re.findall(r'\[COMPLETAR', raw))
    if pend:
        avisos.append(f'Quedan {pend} marca(s) [COMPLETAR] en silabo.json.')
    tel = re.findall(r'(?<!\d)(?:\+593[\s-]?|0)9\d{8}(?!\d)', re.sub(r'"no_publicar".*?\]', '', raw, flags=re.S))
    if tel:
        errores.append(f'Parece haber un número de teléfono ({tel[0][:4]}…) en el sílabo: quítalo o ponlo solo en «no_publicar».')

    for x in errores:
        print('ERROR ', x)
    for x in avisos:
        print('AVISO ', x)
    n_s = sum(len(M.get('sesiones') or []) for M in ms)
    print(f'\nsilabo.json: {len(ms)} momento(s), {n_s} sesiones, {len(ras)} RA, {len(D.get("practicas") or [])} práctica(s) · '
          f'{len(errores)} error(es), {len(avisos)} aviso(s).')
    return 1 if errores else 0


if __name__ == '__main__':
    sys.exit(main())
