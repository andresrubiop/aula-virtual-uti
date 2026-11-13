#!/usr/bin/env python3
"""Genera los videos del aula con NotebookLM (cuenta institucional de Google/Gemini del docente) y los descarga.

    python3 videos/generar_videos.py --lista            qué videos hay, en qué idioma y su estado
    python3 videos/generar_videos.py --manual V1.1      instrucciones paso a paso para hacerlo en la web (sin instalar nada)
    python3 videos/generar_videos.py V1.1 [V1.2 …]      modo automático con la herramienta «nlm» (todos si no se indica)
        --idiomas es,en    idiomas a generar (por omisión los dos)
        --perfil uti       perfil de nlm con la cuenta institucional (nlm login --profile uti)
        --una-vez          un solo ciclo (lanza o descarga lo que toque) en lugar de esperar a que terminen

Cada video sale de videos/guiones/V#.#.md (título y enfoque en español e inglés). Fuentes del cuaderno: la guía
de producción (videos/guiones/guia.md) y los PDF de la unidad en ese idioma (manual y práctica, materiales/unidad-N/).
Descarga: videos/bruto/V#.#.<idioma>.mp4. Después: python3 hub/tools/video_cards.py videos/bruto/V1.1.es.mp4
(portada y cierre UTI, póster y registro en el aula) y python3 hub/build.py.
El estado se guarda en videos/estado.json: se puede interrumpir y reanudar. NotebookLM limita los videos por día:
el script comprueba la cuota y espera; nunca lanza dos a la vez (cada reintento a ciegas crea otro video).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault('NOTEBOOKLM_RATE_LIMIT_MAX_RETRIES', '0')
AQUI = Path(__file__).resolve().parent
ROOT = AQUI.parent
GUIONES = AQUI / 'guiones'
STATE = AQUI / 'estado.json'
COURSE = json.loads((ROOT / 'hub/src/course.json').read_text(encoding='utf-8'))
ARGS = sys.argv[1:]
PERFIL = ARGS[ARGS.index('--perfil') + 1] if '--perfil' in ARGS else ''
IDIOMAS = (ARGS[ARGS.index('--idiomas') + 1] if '--idiomas' in ARGS else 'es,en').split(',')
# Estilo visual único para toda la serie: colores de la UTI, sin personas ni marcas
ESTILO = ('Clean, modern academic explainer. Flat vector diagrams and simple charts on a white or very light background. '
          'Deep purple #3C235F for titles and main shapes, orange #EA600A only for highlights, soft grey for secondary elements. '
          'Rounded sans-serif type, large and legible, generous white space, one idea per slide. Use only purple, orange, white '
          'and light grey. Tables have at most four rows; prefer a simple diagram to a table. Consistent look on every slide. '
          'No photographs, no people, no logos, no clip art, no handwriting, no decorative textures.')


def log(*a):
    print(time.strftime('%d/%m %H:%M'), *a, flush=True)


def guion(v: str) -> dict:
    f = GUIONES / f'{v}.md'
    if not f.exists():
        sys.exit(f'No existe {f.relative_to(ROOT)}. Los guiones se escriben a partir del manual de la unidad (ver videos/README.md).')
    t = f.read_text(encoding='utf-8')
    m = re.search(r'^#\s*' + re.escape(v) + r'\s*·\s*(.+?)\s*\|\s*(.+?)\s*$', t, re.M)
    out = {'es': {'titulo': m.group(1) if m else v}, 'en': {'titulo': m.group(2) if m else v}}
    for lang in ('es', 'en'):
        p = re.search(r'^##\s*prompt\s+' + lang + r'\s*\n(.*?)(?=^##\s|\Z)', t, re.S | re.M)
        out[lang]['prompt'] = p.group(1).strip() if p else ''
    return out


def fuentes(v: str, lang: str) -> list[Path]:
    n = int(v[1:].split('.')[0])
    u = next((u for u in COURSE['units'] if u['n'] == n), None)
    if not u:
        sys.exit(f'{v}: no hay unidad {n} en hub/src/course.json')
    sfx = '' if lang == 'es' else f'.{lang}'
    d = ROOT / 'materiales' / f'unidad-{n}'
    fs = [d / f'M{n}_manual{sfx}.pdf', d / f'{u.get("lab") or f"PR{n}"}_practica{sfx}.pdf']
    hay = [f for f in fs if f.exists()]
    if not hay:
        sys.exit(f'{v}: faltan los PDF de la unidad {n} en {lang} (python3 hub/build.py && python3 hub/tools/pdfs.py {n})')
    return hay


def todos() -> list[str]:
    return sorted((f.stem for f in GUIONES.glob('V*.md')), key=lambda s: [int(x) for x in s[1:].split('.')])


def salida(v, lang) -> Path:
    return AQUI / 'bruto' / f'{v}.{lang}.mp4'


def lista():
    for v in todos():
        g = guion(v)
        n = v[1:].split('.')[0]
        est = []
        for lang in ('es', 'en'):
            listo = (AQUI / f'unidad-{n}' / f'{v}.{lang}.mp4').exists()
            est.append(f'{lang}: ' + ('en el aula' if listo else 'descargado' if salida(v, lang).exists() else 'sin guion' if not g[lang]['prompt'] else 'pendiente'))
        print(f'{v} · {g["es"]["titulo"]} · ' + ' · '.join(est))


def manual(v: str):
    g = guion(v)
    for lang in IDIOMAS:
        fs = fuentes(v, lang)
        print(f'''
════ {v} · {g[lang]["titulo"]} · {"español" if lang == "es" else "inglés"} ════
1. Abre https://notebooklm.google.com con tu cuenta institucional (@indoamerica.edu.ec).
2. Crea un cuaderno nuevo: «{COURSE["title"]["es"]} · Unidad {v[1:].split(".")[0]} · Videos».
3. Agrega estas fuentes (botón «Agregar fuente» → subir archivo):
     - {(GUIONES / "guia.md").relative_to(ROOT)}
''' + ''.join(f'     - {f.relative_to(ROOT)}\n' for f in fs) + f'''4. En «Studio» → «Resumen en video» → el lápiz (personalizar):
     - Formato: Explicativo · Idioma: {"Español" if lang == "es" else "English"}
     - Estilo visual: Personalizado, y pega este texto:
       {ESTILO}
     - En «¿En qué debe centrarse?» pega el enfoque:
----------------------------------------------------------------
{g[lang]["prompt"]}
----------------------------------------------------------------
5. Pulsa «Generar» (puede tardar más de 30 minutos). Míralo completo y comprueba cifras y nombres contra el manual.
6. Descárgalo y guárdalo como:  {salida(v, lang).relative_to(ROOT)}
7. Avísale a tu asistente (Claude o Codex): «ya descargué el video {v}».''')


def nlm(*args, timeout=900):
    cmd = ['nlm', *args] + (['--profile', PERFIL] if PERFIL else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        sys.exit('La herramienta nlm falló. Revisa autenticación y cuota con el docente; no se reintenta automáticamente.')
    out = r.stdout.strip()
    try:
        i = min(x for x in (out.find('{'), out.find('[')) if x >= 0)
        return json.loads(out[i:])
    except (ValueError, json.JSONDecodeError):
        sys.exit('nlm devolvió una respuesta no reconocida. Revisa el cuaderno antes de repetir una generación.')


def videos(nb):
    d = nlm('video', 'list', nb, '--json', timeout=180)
    return d if isinstance(d, list) else []


def hay_sitio():
    d = nlm('usage', '--json', timeout=180)
    w = next((x for x in d.get('windows', []) if x.get('window') == 'rolling'), None) if isinstance(d, dict) else None
    return not w or w.get('percent_remaining', 100) >= 25


def guardar(s):
    STATE.write_text(json.dumps(s, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def lanzar(s, v, lang):
    n = v[1:].split('.')[0]
    c = s.setdefault(f'{n}.{lang}', {'src': {}})
    if 'nb' not in c:
        d = nlm('notebook', 'create', f'{COURSE["title"]["es"]} · U{n} · Videos {lang.upper()}', '--json')
        if 'notebook_id' not in d:
            sys.exit(f'No se pudo crear el cuaderno: {d}')
        c['nb'] = d['notebook_id']
        guardar(s)
    ids = []
    for f in [GUIONES / 'guia.md', *fuentes(v, lang)]:
        if f.name not in c['src']:
            extra = ['--text', f.read_text(encoding='utf-8'), '--title', 'Video production guide'] if f.suffix == '.md' else ['--file', str(f)]
            d = nlm('source', 'add', c['nb'], *extra, '--wait', '--json')
            if 'source_id' not in d:
                sys.exit(f'No se pudo subir {f.name}: {d}')
            c['src'][f.name] = d['source_id']
            guardar(s)
        ids.append(c['src'][f.name])
    antes = {a['id'] for a in videos(c['nb'])}
    d = nlm('video', 'create', c['nb'], '--format', 'explainer', '--style', 'custom', '--style-prompt', ESTILO, '--language', lang,
            '--focus', guion(v)[lang]['prompt'], '--source-ids', ','.join(ids), '-y', '--json')
    log(f'{v} ({lang}): pedido · {str(d.get("error") or d.get("status") or d)[:120]}')
    for _ in range(8):                      # lo que cuenta es que el video aparezca en el cuaderno, no la respuesta
        nuevos = [a for a in videos(c['nb']) if a['id'] not in antes]
        if nuevos:
            c[v] = nuevos[0]['id']
            guardar(s)
            return
        time.sleep(15)
    sys.exit(f'{v} ({lang}): estado incierto. Revisa el cuaderno antes de volver a solicitar el video.')


def automatico(pedidos):
    if not shutil.which('nlm'):
        sys.exit('No está instalada la herramienta «nlm». Usa el modo manual (--manual V1.1) o instálala: ver videos/README.md.')
    s = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    intentos, una_vez = {}, '--una-vez' in ARGS
    while True:
        pend = [(v, l) for v in pedidos for l in IDIOMAS if guion(v)[l]['prompt'] and not salida(v, l).exists() and intentos.get((v, l), 0) <= 2]
        if not pend:
            break
        en_curso = False
        for v, lang in pend:
            c = s.get(f'{v[1:].split(".")[0]}.{lang}', {})
            if v not in c:
                if not en_curso and hay_sitio():
                    lanzar(s, v, lang)
                    en_curso = True
                continue
            en_curso = True
            st = next((a.get('status') for a in videos(c['nb']) if a['id'] == c[v]), 'missing')
            if st == 'completed':
                salida(v, lang).parent.mkdir(parents=True, exist_ok=True)
                nlm('download', 'video', c['nb'], '--id', c[v], '-o', str(salida(v, lang)), '--no-progress', timeout=900)
                if salida(v, lang).exists():
                    log(f'{v} ({lang}): descargado → {salida(v, lang).relative_to(ROOT)}')
            elif st == 'missing':
                sys.exit(f'{v} ({lang}): no se encuentra el video registrado; revisa el cuaderno antes de reintentar.')
            elif st == 'failed':
                intentos[(v, lang)] = intentos.get((v, lang), 0) + 1
                log(f'{v} ({lang}): {st} (intento {intentos[(v, lang)]})')
                c.pop(v, None)
                guardar(s)
        if una_vez:
            break
        time.sleep(90)
    falta = [f'{v}.{l}' for v in pedidos for l in IDIOMAS if guion(v)[l]['prompt'] and not salida(v, l).exists()]
    log('fin · sin terminar: ' + (', '.join(falta) or 'ninguno'))


def main() -> int:
    if not ARGS or '--help' in ARGS or '-h' in ARGS:
        print(__doc__)
        return 0
    if any(lang not in ('es', 'en') for lang in IDIOMAS):
        sys.exit('Idiomas admitidos: es,en')
    ids = [a for a in ARGS if re.fullmatch(r'V\d+\.\d+', a)]
    if '--lista' in ARGS:
        lista()
    elif '--manual' in ARGS:
        for v in ids or todos():
            manual(v)
    else:
        automatico(ids or todos())
    return 0


if __name__ == '__main__':
    sys.exit(main())
