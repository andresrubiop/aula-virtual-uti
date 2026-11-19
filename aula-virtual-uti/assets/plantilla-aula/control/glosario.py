#!/usr/bin/env python3
"""Glosario ES/EN del curso: propone términos y revisa que cada uno se traduzca igual en todo el material.

    python3 control/glosario.py                # verificar → control/GLOSARIO.md y control/glosario.json
    python3 control/glosario.py proponer       # además, términos candidatos sacados de las negritas bilingües
    python3 control/glosario.py --json

La fuente única es el glosario del aula: hub/src/content/95-recursos.html, vista «Glosario», un término por
<div class="gloss__item"><dt>término · <em>term</em></dt><dd>…definición ES/EN…</dd></div>.
Variantes aceptadas en inglés: <em>term / other term</em>.

Revisa en cada par español–inglés (frases <span lang="es">…</span><span lang="en">…</span> del aula, cuestionarios,
títulos de course.json, traducciones de Canvas en canvas/traducciones.en.json y subtítulos de videos/subtitulos/)
que, si aparece el término en español, su par en inglés use la traducción del glosario. Lo que no coincide se
informa para revisarlo: a veces una paráfrasis es correcta, por eso son avisos y no errores. Error (código 1): el
mismo término con dos traducciones distintas en el glosario.
Propuestas: nunca se añaden solas; el asistente redacta la definición, el docente la revisa y se agrega al HTML.
"""
import argparse
import html
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / 'hub' / 'src' / 'content'
RECURSOS = CONTENT / '95-recursos.html'
ITEM = re.compile(r'<div class="gloss__item">\s*<dt>(.*?)\s*·\s*<em>(.*?)</em>.*?</dt>', re.S)
PAR = re.compile(r'<span lang="es">((?:(?!<span lang=).)*?)</span>\s*<span lang="en">((?:(?!<span lang=).)*?)</span>', re.S)


def limpio(h):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h or ''))).strip()


def norm(t):
    t = unicodedata.normalize('NFC', t).casefold()
    return t


def patron(termino, lengua):
    plural = r'(?:s|es)?' if lengua == 'es' else r'(?:s|es)?'
    partes = [re.escape(p) for p in norm(termino).split()]
    return re.compile(r'(?<!\w)' + r'\s+'.join(partes[:-1] + [partes[-1] + plural]) + r'(?!\w)')


def glosario():
    t = RECURSOS.read_text(encoding='utf-8') if RECURSOS.exists() else ''
    out = []
    for m in ITEM.finditer(t):
        es, en = limpio(m[1]), limpio(m[2])
        if es and en:
            out.append({'es': es, 'en': [x.strip() for x in en.split('/') if x.strip()]})
    return out


def pares():
    """(dónde, texto ES, texto EN) de todo el material bilingüe."""
    out = []
    for f in sorted(CONTENT.rglob('*.html')):
        rel = f.relative_to(ROOT).as_posix()
        t = f.read_text(encoding='utf-8')
        if f == RECURSOS:
            t = re.sub(r'<dl class="gloss__list">.*?</dl>', '', t, flags=re.S)       # el glosario no se compara consigo mismo
        for m in PAR.finditer(t):
            out.append((rel, limpio(m[1]), limpio(m[2])))
        for q in re.findall(r'<script type="application/json">(.*?)</script>', t, re.S):
            try:
                datos = json.loads(q)
            except ValueError:
                continue
            def recorrer(x):
                if isinstance(x, dict):
                    if isinstance(x.get('es'), str) and isinstance(x.get('en'), str):
                        out.append((rel + ' (cuestionario)', x['es'], x['en']))
                    for v in x.values():
                        recorrer(v)
                elif isinstance(x, list):
                    for v in x:
                        recorrer(v)
            recorrer(datos)
    course = ROOT / 'hub/src/course.json'
    if course.exists():
        def rec(x):
            if isinstance(x, dict):
                if isinstance(x.get('es'), str) and isinstance(x.get('en'), str):
                    out.append(('hub/src/course.json', x['es'], x['en']))
                for v in x.values():
                    rec(v)
            elif isinstance(x, list):
                for v in x:
                    rec(v)
        rec(json.loads(course.read_text(encoding='utf-8')))
    tr = ROOT / 'canvas/traducciones.en.json'
    if tr.exists():
        datos = json.loads(tr.read_text(encoding='utf-8'))
        for grupo in ('pages', 'assignments'):
            for k, v in (datos.get(grupo) or {}).items():
                if v.get('html') and v.get('source_html'):
                    out.append((f'canvas/traducciones.en.json ({grupo}/{k})', limpio(v['source_html']), limpio(v['html'])))
    sub = ROOT / 'videos/subtitulos'
    for j in sorted(sub.glob('V*.json')) if sub.is_dir() else []:
        es = j.with_name(j.stem + '.es.txt')
        if es.exists():
            frases_en = [c[2] for c in json.loads(j.read_text(encoding='utf-8'))]
            tr_es = {int(n): x for n, _, x in (l.partition('|') for l in es.read_text(encoding='utf-8').splitlines() if '|' in l) if n.strip().isdigit()}
            for i, en in enumerate(frases_en, 1):
                if i in tr_es:
                    out.append((f'videos/subtitulos/{j.stem} (frase {i})', tr_es[i], en))
    return out


def proponer(terminos, lista):
    conocidos = {norm(t['es']) for t in terminos}
    cand = {}
    for f in sorted(CONTENT.rglob('*.html')):
        for m in PAR.finditer(f.read_text(encoding='utf-8')):
            # una negrita seguida de «:» o «.» es un rótulo («Entrega:»), no un término
            rotulo = r'<(?:strong|dfn|b)>(.*?)</(?:strong|dfn|b)>(?!\s*[:.])(?<![:.]</strong>)(?<![:.]</b>)(?<![:.]</dfn>)'
            es = re.findall(rotulo, m[1], re.S)
            en = re.findall(rotulo, m[2], re.S)
            if not es or len(es) != len(en):
                continue
            for a, b in zip(es, en):
                a, b = limpio(a).strip(' .:;,'), limpio(b).strip(' .:;,')
                if not a or not b or len(a.split()) > 5 or len(b.split()) > 5 or norm(a) in conocidos or a.lower() == b.lower() or re.search(r'\d', a):
                    continue
                c = cand.setdefault((norm(a), norm(b)), {'es': a, 'en': b, 'veces': 0, 'fuentes': set()})
                c['veces'] += 1
                c['fuentes'].add(f.relative_to(ROOT).as_posix())
    # cuántas veces aparece el término ES en todo el material
    texto_es = ' '.join(norm(es) for _, es, _ in lista)
    out = []
    for c in cand.values():
        c['apariciones'] = len(patron(c['es'], 'es').findall(texto_es))
        out.append({**c, 'fuentes': sorted(c['fuentes'])})
    return sorted(out, key=lambda c: (-c['apariciones'], c['es']))[:60]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('orden', nargs='?', default='verificar', choices=['verificar', 'proponer'])
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    terminos = glosario()
    lista = pares()
    errores, avisos, usos = [], [], {}
    vistos = {}
    for t in terminos:
        k = norm(t['es'])
        if k in vistos and set(map(norm, vistos[k])) != set(map(norm, t['en'])):
            errores.append(f'«{t["es"]}» tiene dos traducciones en el glosario: {" / ".join(vistos[k])} y {" / ".join(t["en"])}')
        vistos[k] = t['en']
    for t in terminos:
        pes = patron(t['es'], 'es')
        pens = [patron(x, 'en') for x in t['en']]
        n = 0
        for donde, es, en in lista:
            if pes.search(norm(es)):
                n += 1
                if not any(p.search(norm(en)) for p in pens):
                    avisos.append({'termino': t['es'], 'esperado': ' / '.join(t['en']), 'donde': donde,
                                   'es': es[:140], 'en': en[:140]})
        usos[t['es']] = n
    resultado = {'fecha': datetime.now(timezone.utc).isoformat(), 'terminos': len(terminos), 'pares_revisados': len(lista),
                 'usos': usos, 'errores': errores, 'avisos': avisos, 'resultado': 'con_errores' if errores else 'sin_errores'}
    if a.orden == 'proponer':
        resultado['propuestos'] = proponer(terminos, lista)
    (ROOT / 'control').mkdir(exist_ok=True)
    (ROOT / 'control/glosario.json').write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    md = ['# Glosario ES/EN', '',
          f'Revisión del {resultado["fecha"][:10]}: {len(terminos)} término(s) del glosario del aula (Recursos → Glosario) '
          f'comparados en {len(lista)} pares español–inglés del aula, cuestionarios, course.json, traducciones de Canvas y subtítulos.', '']
    if not terminos:
        md += ['**El aula todavía no tiene glosario.** Ejecuta `python3 control/glosario.py proponer`, elige con el docente los términos '
               'y agrégalos en `hub/src/content/95-recursos.html` (vista Glosario) con su definición en los dos idiomas.', '']
    if errores:
        md += ['## Por corregir', ''] + [f'- {e}' for e in errores] + ['']
    md += ['## Uso de cada término', '', '| Término | Inglés | Pares donde aparece | Traducción distinta |', '|---|---|---|---|']
    md += [f'| {t["es"]} | {" / ".join(t["en"])} | {usos[t["es"]]} | {sum(1 for x in avisos if x["termino"] == t["es"])} |' for t in terminos]
    if avisos:
        md += ['', '## Para revisar', '', 'El término aparece en español, pero el inglés no usa la traducción del glosario. Corrige el inglés, '
               'añade la variante al glosario (`<em>term / variante</em>`) si es correcta, o déjalo si es una paráfrasis válida.', '',
               '| Término | Esperado | Dónde | Español | Inglés |', '|---|---|---|---|---|']
        md += [f'| {x["termino"]} | {x["esperado"]} | {x["donde"]} | {x["es"].replace("|", "/")} | {x["en"].replace("|", "/")} |' for x in avisos[:200]]
    if a.orden == 'proponer' and not resultado.get('propuestos'):
        md += ['', '## Términos propuestos', '', 'No hay términos en negrita con par en el otro idioma. El asistente propone los términos '
               'técnicos del manual y del sílabo con su traducción y definición, y el docente decide cuáles van al glosario.']
    if resultado.get('propuestos'):
        md += ['', '## Términos propuestos', '', 'Sacados de las negritas que tienen par en el otro idioma. No se agregan solos: '
               'el asistente redacta la definición a partir del manual y el docente decide.', '',
               '| Español | Inglés | Apariciones | Dónde |', '|---|---|---|---|']
        md += [f'| {c["es"]} | {c["en"]} | {c["apariciones"]} | {", ".join(c["fuentes"][:3])} |' for c in resultado['propuestos']]
    (ROOT / 'control/GLOSARIO.md').write_text('\n'.join(md) + '\n', encoding='utf-8', newline='\n')
    if a.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=1))
    else:
        print(f'{len(terminos)} término(s) · {len(lista)} pares ES/EN revisados · {len(errores)} error(es) · {len(avisos)} para revisar'
              + (f' · {len(resultado["propuestos"])} propuesto(s)' if a.orden == 'proponer' else '') + ' → control/GLOSARIO.md')
        for e in errores:
            print('  error:', e)
    return 1 if errores else 0


if __name__ == '__main__':
    sys.exit(main())
