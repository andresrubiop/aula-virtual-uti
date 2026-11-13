#!/usr/bin/env python3
"""Regenera videos/videos.js a partir de los archivos de la carpeta videos/ (videos bilingües).

Uso:  python3 hub/tools/videos.py

Convención de nombres (en cualquier subcarpeta de videos/, p. ej. videos/unidad-2/):
    V2.1.es.mp4 / V2.1.en.mp4        → video en español / en inglés (también .webm o .mov)
    V2.1.es.vtt / V2.1.en.vtt        → subtítulos de cada idioma (opcional)
    V2.1.en.fr.vtt                   → subtítulos en francés del video en inglés (varios idiomas: hub/tools/subtitulos.py)
    V2.1.en.subs.js                  → todos esos subtítulos en un script, el que usa el reproductor del aula
    V2.1.es.jpg / V2.1.en.png        → póster (opcional)
    V2.1.mp4                         → sin idioma en el nombre = español
El aula muestra el video del idioma activo; si falta uno, muestra el otro con una nota.
Las entradas escritas a mano con "url" (YouTube, Drive u otro servidor) se conservan:
    "V2.1": {"es": {"url": "https://…"}, "en": {"url": "https://…"}}
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
VIDEOS = ROOT / 'videos'
OUT = VIDEOS / 'videos.js'
PAT = re.compile(r'^(V\d+\.\d+)(?:\.(es|en))?\b.*\.(mp4|webm|mov)$', re.I)


def existing():
    if not OUT.exists():
        return {}
    txt = OUT.read_text(encoding='utf-8')
    try:
        return json.loads(txt[txt.index('{'): txt.rindex('}') + 1])
    except ValueError:
        return {}


def side(f: pathlib.Path, vid: str, lang: str, exts) -> str | None:
    for pattern in (f'{vid}.{lang}*', f'{vid}*') if lang == 'es' else (f'{vid}.{lang}*',):
        for ext in exts:
            hit = next(iter(sorted(f.parent.glob(f'{pattern}.{ext}'))), None)
            if hit and (lang != 'es' or '.en.' not in hit.name):
                return hit.relative_to(VIDEOS).as_posix()
    return None


def main():
    old = existing()
    found: dict = {}
    for f in sorted(VIDEOS.rglob('*')):
        m = PAT.match(f.name)
        if not m or not f.is_file() or {'bruto', 'muestra'} & set(f.relative_to(VIDEOS).parts):
            continue                               # bruto/: descargas sin portada (o descartadas); muestra/: prueba
        vid, lang = m.group(1).upper(), (m.group(2) or 'es').lower()
        entry = {'src': f.relative_to(VIDEOS).as_posix()}
        # Subtítulos en varios idiomas: V2.1.en.es.vtt = video en inglés, subtítulos en español (hub/tools/subtitulos.py)
        subs = {m2.group(1): s.relative_to(VIDEOS).as_posix() for s in sorted(f.parent.glob(f'{vid}.{lang}.*.vtt'))
                if (m2 := re.match(re.escape(f'{vid}.{lang}.') + r'(\w\w)\.vtt$', s.name))}
        if subs:
            entry['subtitulos'] = subs
            js = f.parent / f'{vid}.{lang}.subs.js'       # las mismas frases como script (funciona también en file:// y entre orígenes)
            if js.exists():
                entry['subtitulos_js'] = js.relative_to(VIDEOS).as_posix()
        else:
            sub = side(f, vid, lang, ('vtt',))
            if sub:
                entry['subtitulos'] = sub
        pos = side(f, vid, lang, ('jpg', 'png'))
        if pos:
            entry['poster'] = pos
        found.setdefault(vid, {})[lang] = entry
    for vid, e in old.items():                     # conservar enlaces externos escritos a mano
        if not isinstance(e, dict):
            continue
        for lang in ('es', 'en'):
            x = e.get(lang) if lang in e else (e if lang == 'es' and e.get('url') else None)
            if isinstance(x, dict) and x.get('url') and lang not in found.get(vid, {}):
                found.setdefault(vid, {})[lang] = x
    body = json.dumps(dict(sorted(found.items(), key=lambda kv: [int(x) for x in kv[0][1:].split('.')])), ensure_ascii=False, indent=2)
    OUT.write_text(
        '/* Configuración de videos del aula · UTI (bilingüe).\n'
        '   Generado por hub/tools/videos.py; también puede editarse a mano.\n'
        '   "V2.1": {"es": {"src": "unidad-2/V2.1.es.mp4", "subtitulos": "unidad-2/V2.1.es.vtt"}, "en": {"url": "https://…"}} */\n'
        f'window.HUB_VIDEOS = {body};\n', encoding='utf-8')
    print(f'{len(found)} video(s) configurados → {OUT.relative_to(ROOT)}')
    for vid, e in found.items():
        print(f'  {vid}: ' + ', '.join(f'{k} = {v.get("src") or v.get("url")}' for k, v in e.items()))


if __name__ == '__main__':
    main()
