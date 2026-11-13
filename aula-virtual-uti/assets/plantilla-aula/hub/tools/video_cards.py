#!/usr/bin/env python3
"""Prepara un video generado con IA (NotebookLM / Gemini) para el aula: portada y cierre UTI, póster y registro en videos/videos.js.

Uso (desde la carpeta del curso):
    python3 hub/tools/video_cards.py videos/bruto/V1.1.en.mp4 [más archivos…]
    python3 hub/tools/video_cards.py --muestra        # genera una prueba sintética en videos/muestra/ (no se registra)

Entrada: el MP4 tal como se descarga de NotebookLM, con nombre V#.#.<idioma>.mp4 (es o en).
Salida:  videos/unidad-N/V#.#.<idioma>.mp4  = portada (3 s) + video + cierre (4 s), en H.264 + AAC, a la misma
         resolución y cadencia que el original; videos/unidad-N/V#.#.<idioma>.jpg (póster, un fotograma del video).
         Después ejecuta hub/tools/videos.py (videos.js) para que el aula lo muestre.
Portada: fondo morado UTI, logo blanco, el nombre del curso (course.json), "Unidad N" y el título del video (sale de la
         página "Antes de clase" de la unidad, hub/src/content/uN/20-preparacion.html).
Cierre:  logo y la leyenda de video generado con IA y revisado por el docente, en el idioma del video.
Requiere ffmpeg y ffprobe (Ubuntu: sudo apt install ffmpeg). Solo stdlib.
"""
import html
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
VIDEOS = ROOT / 'videos'
LOGO = ROOT / 'identidad-uti' / 'logo-uti-horizontal-blanco.png'
PURPLE, ORANGE = '0x3C235F', '0xEA600A'
FONTS = [ROOT / 'hub' / 'vendor' / 'fonts' / 'Poppins-600.woff2', pathlib.Path('/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf')]
FONTS_REG = [ROOT / 'hub' / 'vendor' / 'fonts' / 'Poppins-400.woff2', pathlib.Path('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf')]

_C = json.loads((ROOT / 'hub' / 'src' / 'course.json').read_text(encoding='utf-8'))
COURSE = {'es': _C['title']['es'], 'en': _C['title'].get('en') or _C['title']['es']}
UNIT = {'es': 'Unidad', 'en': 'Unit'}
LEGEND = {
    'es': ['Video generado con IA a partir de los materiales del curso', 'y revisado por el docente.'],
    'en': ['AI-generated video based on the course materials', 'and reviewed by the instructor.'],
}
NAME = re.compile(r'^(V(\d+)\.\d+)\.(es|en)\.(mp4|mov|webm)$', re.I)


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        sys.exit(f'Falló: {" ".join(map(str, cmd[:6]))}…\n{r.stderr[-1500:]}')
    return r.stdout


def font(lang: str, bold: bool = True) -> pathlib.Path:
    for f in (FONTS if bold else FONTS_REG):
        if f.exists():
            return f
    sys.exit('No hay fuente para los rótulos (Poppins en hub/vendor/fonts o Noto Sans del sistema).')


def title_of(vid: str, unit: int, lang: str) -> str:
    """Título del video en el idioma pedido: <span lang="…"> de la tarjeta en la página Antes de clase."""
    f = ROOT / 'hub' / 'src' / 'content' / f'u{unit}' / '20-preparacion.html'
    m = re.search(rf'data-video="{re.escape(vid)}"[\s\S]*?class="video-poster__title">([\s\S]*?)</span></div>', f.read_text()) if f.exists() else None
    if not m:
        return vid
    spans = dict(re.findall(r'<span lang="(\w+)">([\s\S]*?)</span>', m.group(1)))
    t = spans.get(lang)
    t = t or spans.get('en') or spans.get('es') or vid
    return html.unescape(re.sub(r'<[^>]+>', '', t)).strip()


def probe(src: pathlib.Path) -> dict:
    info = json.loads(run(['ffprobe', '-v', 'error', '-print_format', 'json', '-show_streams', '-show_format', str(src)]))
    v = next(s for s in info['streams'] if s['codec_type'] == 'video')
    a = next((s for s in info['streams'] if s['codec_type'] == 'audio'), None)
    num, den = (int(x) for x in v.get('avg_frame_rate', '25/1').split('/'))
    return {'w': int(v['width']), 'h': int(v['height']), 'fps': round(num / den, 3) if den else 25,
            'rate': int(a['sample_rate']) if a else 48000, 'audio': a is not None,
            'dur': float(info['format'].get('duration', 0))}


def card(path: pathlib.Path, p: dict, secs: float, lines: list[tuple[str, int, str, bool]], lang: str, tmp: pathlib.Path):
    """Rótulo: fondo morado, logo arriba, líneas de texto centradas (texto, tamaño relativo a la altura, color, negrita)."""
    W, H = p['w'], p['h']
    logo_w = int(W * 0.26)
    filters = [f'[1:v]scale={logo_w}:-1[logo]', f'[0:v][logo]overlay=(W-w)/2:H*0.18[b0]']
    y = 0.50
    for k, (text, size, colour, bold) in enumerate(lines):
        tf = tmp / f'{path.stem}-{k}.txt'
        tf.write_text(text)
        fs = max(14, int(H * size / 1000))
        # que quepa en el 90 % del ancho (≈ 0,55 em por carácter latino, 1 em por carácter japonés)
        em = sum(1.0 if ord(ch) > 0x2e80 else 0.55 for ch in text) or 1
        fs = max(14, min(fs, int(W * 0.9 / em)))
        filters.append(f"[b{k}]drawtext=fontfile='{font(lang, bold)}':textfile='{tf}':fontsize={fs}:fontcolor={colour}:"
                       f'x=(w-text_w)/2:y=h*{y:.3f}[b{k + 1}]')
        y += size / 1000 * 1.55
    last = f'b{len(lines)}'
    filters.append(f'[{last}]fade=t=in:st=0:d=0.5,fade=t=out:st={secs - 0.5}:d=0.5,format=yuv420p[v]')
    run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=c={PURPLE}:s={W}x{H}:r={p["fps"]}:d={secs}',
         '-i', str(LOGO), '-f', 'lavfi', '-i', f'anullsrc=r={p["rate"]}:cl=stereo',
         '-filter_complex', ';'.join(filters), '-map', '[v]', '-map', '2:a', '-t', str(secs),
         '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '160k', str(path)])


def process(src: pathlib.Path, register: bool = True) -> pathlib.Path:
    m = NAME.match(src.name)
    if not m:
        sys.exit(f'{src.name}: el nombre debe ser V#.#.<idioma>.mp4 (por ejemplo V1.1.en.mp4)')
    vid, unit, lang = m.group(1).upper(), int(m.group(2)), m.group(3).lower()
    p = probe(src)
    title = title_of(vid, unit, lang)
    out_dir = VIDEOS / f'unidad-{unit}' if register else VIDEOS / 'muestra'
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'{vid}.{lang}.mp4'
    with tempfile.TemporaryDirectory() as t:
        tmp = pathlib.Path(t)
        intro, outro = tmp / 'intro.mp4', tmp / 'outro.mp4'
        card(intro, p, 3.0, [(f'{COURSE[lang]} · {UNIT[lang]} {unit}', 30, 'white@0.85', False),
                             (title, 58, 'white', True), (vid, 30, ORANGE, True)], lang, tmp)
        card(outro, p, 4.0, [(LEGEND[lang][0], 26, 'white', False), (LEGEND[lang][1], 26, 'white', False),
                             ('Universidad Tecnológica Indoamérica', 24, 'white@0.7', False)], lang, tmp)
        # el video original, normalizado (mismo tamaño y cadencia; audio silencioso si no trae)
        body = tmp / 'body.mp4'
        if p['audio']:
            inputs = ['-i', str(src), '-map', '0:v:0', '-map', '0:a:0']
        else:
            inputs = ['-i', str(src), '-f', 'lavfi', '-i', f'anullsrc=r={p["rate"]}:cl=stereo', '-map', '0:v:0', '-map', '1:a', '-shortest']
        run(['ffmpeg', '-y', '-v', 'error', *inputs, '-vf', f'fps={p["fps"]},format=yuv420p', '-ar', str(p['rate']), '-ac', '2',
             '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '160k', str(body)])
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(intro), '-i', str(body), '-i', str(outro), '-filter_complex',
             '[0:v][0:a][1:v][1:a][2:v][2:a]concat=n=3:v=1:a=1[v][a]', '-map', '[v]', '-map', '[a]',
             '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(out)])
    # póster: un fotograma del video original (a un tercio), sin la portada
    run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{3 + p["dur"] / 3:.2f}', '-i', str(out), '-frames:v', '1', '-q:v', '3',
         str(out.with_suffix('.jpg'))])
    total = probe(out)['dur']
    print(f'{src} → {out.relative_to(ROOT)} ({total:.1f} s · {p["w"]}×{p["h"]} · «{title}») + póster')
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    if argv == ['--muestra']:
        # prueba sintética: 6 s de barras de color con un tono, como si fuera un video descargado de NotebookLM
        (VIDEOS / 'muestra').mkdir(parents=True, exist_ok=True)
        src = VIDEOS / 'muestra' / 'bruto' / 'V1.1.en.mp4'
        src.parent.mkdir(parents=True, exist_ok=True)
        run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=1280x720:r=24:d=6', '-f', 'lavfi',
             '-i', 'sine=f=440:r=44100:d=6', '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(src)])
        process(src, register=False)
        return 0
    for a in argv:
        src = pathlib.Path(a).resolve()
        if not src.exists():
            sys.exit(f'No existe {a}')
        process(src)
    subprocess.run([sys.executable, str(ROOT / 'hub' / 'tools' / 'videos.py')], check=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
