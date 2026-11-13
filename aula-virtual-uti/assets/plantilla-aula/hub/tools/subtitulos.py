#!/usr/bin/env python3
"""Subtítulos de los videos Cinematic (audio en inglés) en los cinco idiomas del aula.

Fuentes (videos/subtitulos/, versionadas):
  V#.#.json          frases del video con sus tiempos sobre el MP4 FINAL (portada UTI de 3 s incluida) y el texto
                     inglés corregido: [[inicio, fin, "texto"], …]
  V#.#.<idioma>.txt  la traducción, una línea por frase: «N|texto» (N = número de frase, desde 1); es, fr, ca, ja
Salida: videos/unidad-N/V#.#.en.<idioma>.vtt (WebVTT, el formato estándar) y V#.#.en.subs.js (las mismas frases en un
script: el reproductor del aula lo carga con <script>, que funciona también abriendo el aula como archivo, file://, y desde
otro origen, como la plantilla de GitHub Classroom; Chrome no carga <track> en esos casos). hub/tools/videos.py los
registra en videos/videos.js y el reproductor ofrece todos los idiomas (por omisión, el del idioma activo del aula).

  python3 hub/tools/subtitulos.py frases V3.1 palabras.json [--silencio 210.4-212.5,…]
        crea V3.1.json a partir de la transcripción con tiempos por palabra (faster-whisper, sobre el MP4 de
        videos/bruto/, sin portada): suma los 3 s de la portada y descarta lo que cae en los tramos silenciados
  python3 hub/tools/subtitulos.py vtt [V3.1 …]     escribe los .vtt (todos los idiomas que tengan traducción completa)
  python3 hub/tools/subtitulos.py ver V3.1         lista las frases «N|texto» (para traducir)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUB = ROOT / 'videos' / 'subtitulos'
PORTADA = 3.0                       # hub/tools/video_cards.py: portada de 3 s antes del video
LANGS = ('en', 'es', 'fr', 'ca', 'ja')
MAX = 84                            # caracteres por frase (dos líneas de ~42)


def frases(video: str, palabras: str, silencio: str = '') -> None:
    mudos = [tuple(map(float, x.split('-'))) for x in silencio.split(',') if x]
    words = [(a, b, w.strip()) for a, b, w in json.load(open(palabras))
             if w.strip() and not any(x <= a <= y for x, y in mudos)]
    cues, cur = [], []

    def cerrar():
        if cur:
            cues.append([round(cur[0][0] + PORTADA, 2), round(cur[-1][1] + PORTADA, 2), ' '.join(w for _, _, w in cur)])
            cur.clear()

    for i, (a, b, w) in enumerate(words):
        if cur and (a - cur[-1][1] > 1.2 or len(' '.join(x for _, _, x in cur)) + len(w) + 1 > MAX or b - cur[0][0] > 7):
            cerrar()
        cur.append((a, b, w))
        txt = ' '.join(x for _, _, x in cur)
        if re.search(r'[.?!]["”]?$', w) and len(txt) > 25:
            cerrar()
    cerrar()
    for i in range(len(cues) - 1):            # que cada frase dure un poco más, sin pisar la siguiente
        cues[i][1] = round(min(cues[i][1] + 0.4, cues[i + 1][0] - 0.05), 2)
    cues[-1][1] = round(cues[-1][1] + 0.6, 2)
    SUB.mkdir(parents=True, exist_ok=True)
    (SUB / f'{video}.json').write_text(json.dumps(cues, ensure_ascii=False, indent=0) + '\n')
    print(f'  → videos/subtitulos/{video}.json ({len(cues)} frases)')


def tiempo(s: float) -> str:
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f'{int(h):02d}:{int(m):02d}:{s:06.3f}'


def lineas(t: str) -> str:
    """Dos líneas equilibradas si la frase es larga (el japonés, que no lleva espacios, la parte el navegador)."""
    if len(t) <= 42 or ' ' not in t or re.search(r'[\u3040-\u30ff\u4e00-\u9fff]', t):
        return t
    mid = len(t) // 2
    cortes = [i for i, c in enumerate(t) if c == ' ']
    i = min(cortes, key=lambda k: abs(k - mid))
    return t[:i] + '\n' + t[i + 1:]


def textos(video: str, lang: str):
    cues = json.loads((SUB / f'{video}.json').read_text())
    if lang == 'en':
        return cues, [c[2] for c in cues]
    f = SUB / f'{video}.{lang}.txt'
    if not f.exists():
        return cues, None
    tr = {}
    for line in f.read_text().splitlines():
        if line.strip():
            n, _, t = line.partition('|')
            tr[int(n)] = t.strip()
    falta = [i for i in range(1, len(cues) + 1) if not tr.get(i)]
    if falta:
        sys.exit(f'{f.name}: faltan las frases {falta[:10]}… ({len(falta)})')
    sobra = sorted(set(tr) - set(range(1, len(cues) + 1)))
    if sobra:
        sys.exit(f'{f.name}: sobran las frases {sobra[:10]}')
    return cues, [tr[i] for i in range(1, len(cues) + 1)]


def vtt(videos) -> None:
    hechos = 0
    for video in videos:
        unidad = ROOT / 'videos' / f'unidad-{video[1]}'
        todos = {}
        for lang in LANGS:
            cues, txt = textos(video, lang)
            if txt is None:
                continue
            out = ['WEBVTT', '']
            for k, ((a, b, _), t) in enumerate(zip(cues, txt), 1):
                out += [str(k), f'{tiempo(a)} --> {tiempo(b)}', lineas(t), '']
            (unidad / f'{video}.en.{lang}.vtt').write_text('\n'.join(out))
            todos[lang] = [[a, b, lineas(t)] for (a, b, _), t in zip(cues, txt)]
            hechos += 1
        (unidad / f'{video}.en.subs.js').write_text(
            '/* Subtítulos del video (hub/tools/subtitulos.py): {idioma: [[inicio, fin, texto], …]} */\n'
            f'(window.HUB_SUBS = window.HUB_SUBS || {{}})[{json.dumps(video + ".en")}] = '
            + json.dumps(todos, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(f'  → {hechos} archivos .vtt y {len(videos)} .subs.js')


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == 'frases':
        sil = sys.argv[sys.argv.index('--silencio') + 1] if '--silencio' in sys.argv else ''
        frases(sys.argv[2], sys.argv[3], sil)
    elif cmd == 'vtt':
        vids = sys.argv[2:] or sorted(p.stem for p in SUB.glob('V*.json'))
        vtt(vids)
    elif cmd == 'ver':
        for k, c in enumerate(json.loads((SUB / f'{sys.argv[2]}.json').read_text()), 1):
            print(f'{k}|{c[2]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
