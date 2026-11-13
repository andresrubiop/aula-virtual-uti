#!/usr/bin/env python3
"""Inventario de los documentos del docente y su texto, para trabajar sin releer archivos pesados.

    python3 fuentes.py [CARPETA_DEL_AULA]

Recorre fuentes/ (menos fuentes/privado/, que nunca se lee) y escribe:
  fuentes/_texto/<misma ruta>.txt   el texto de cada PDF, DOCX, PPTX (una sección por diapositiva, con sus notas),
                                    XLSX, TXT o MD. Los .doc/.ppt antiguos se convierten con LibreOffice si está.
  fuentes/INVENTARIO.md             tabla: archivo, tipo, páginas o diapositivas, palabras, de qué parece tratar,
                                    y avisos (PDF escaneado sin texto, archivo vacío, formato no soportado).
Solo usa la biblioteca estándar; para PDF necesita pdftotext (poppler). No modifica los originales.
"""
import html
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


def xml_text(x: str, par=r'</(?:w:p|a:p)>') -> str:
    x = re.sub(par, '\n', x)
    x = re.sub(r'<w:tab/>|</w:tc>', '\t', x)
    return html.unescape(re.sub(r'<[^>]+>', '', x))


def docx(f: Path):
    with zipfile.ZipFile(f) as z:
        t = xml_text(z.read('word/document.xml').decode('utf-8', 'ignore'))
    return t, 'páginas: —'


def pptx(f: Path):
    out = []
    with zipfile.ZipFile(f) as z:
        slides = sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)), key=lambda n: int(re.findall(r'\d+', n)[-1]))
        for i, n in enumerate(slides, 1):
            body = xml_text(z.read(n).decode('utf-8', 'ignore')).strip()
            nota = f'ppt/notesSlides/notesSlide{re.findall(r"\d+", n)[-1]}.xml'
            notas = xml_text(z.read(nota).decode('utf-8', 'ignore')).strip() if nota in z.namelist() else ''
            out.append(f'=== Diapositiva {i} ===\n{body}' + (f'\n--- notas ---\n{notas}' if notas else ''))
    return '\n\n'.join(out), f'{len(slides)} diapositivas'


def xlsx(f: Path):
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    with zipfile.ZipFile(f) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        sheets = sorted(n for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n))
        out = []
        for name in sheets:
            out.append(f'=== {name} ===')
            for row in ET.fromstring(z.read(name)).findall('.//s:sheetData/s:row', ns):
                cells = []
                for cell in row.findall('s:c', ns):
                    value = cell.findtext('s:v', default='', namespaces=ns)
                    kind = cell.get('t')
                    if kind == 's' and value:
                        value = shared[int(value)]
                    elif kind == 'inlineStr':
                        value = ''.join(t.text or '' for t in cell.findall('.//s:t', ns))
                    formula = cell.findtext('s:f', namespaces=ns)
                    if formula and not value:
                        value = f'={formula} [sin resultado guardado]'
                    cells.append(f'{cell.get("r", "?")}: {value}')
                out.append('\t'.join(cells))
    return '\n'.join(out), f'{len(sheets)} hoja(s); valores guardados, sin recalcular fórmulas'


def pdf(f: Path):
    if not shutil.which('pdftotext'):
        return '', 'falta pdftotext'
    t = subprocess.run(['pdftotext', '-layout', str(f), '-'], capture_output=True, text=True).stdout
    n = len(t.split('\f')) - 1 if t else 0
    return t, f'{n} páginas'


def antiguo(f: Path):
    so = shutil.which('soffice') or shutil.which('libreoffice')
    if not so:
        return '', 'formato antiguo: instala LibreOffice o guárdalo como .docx/.pptx'
    with tempfile.TemporaryDirectory() as tmp:
        ext = 'docx' if f.suffix.lower() == '.doc' else 'pptx'
        subprocess.run([so, '--headless', '--convert-to', ext, '--outdir', tmp, str(f)], capture_output=True, timeout=180)
        conv = next(Path(tmp).glob(f'*.{ext}'), None)
        if not conv:
            return '', 'no se pudo convertir'
        return (docx if ext == 'docx' else pptx)(conv)


LECTORES = {'.pdf': pdf, '.docx': docx, '.pptx': pptx, '.xlsx': xlsx, '.doc': antiguo, '.ppt': antiguo,
            '.txt': lambda f: (f.read_text(errors='ignore'), 'texto'), '.md': lambda f: (f.read_text(errors='ignore'), 'texto')}


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
    src = root / 'fuentes'
    if not src.is_dir():
        sys.exit(f'No existe {src}. Ejecuta esto en la carpeta del aula (la que tiene fuentes/ y hub/).')
    out = src / '_texto'
    filas, total = [], 0
    for f in sorted(src.rglob('*')):
        rel = f.relative_to(src)
        if (rel.parts[0] in ('_texto', 'privado') or f.name in ('LEEME.txt', 'INVENTARIO.md')
                or f.is_symlink() or not f.is_file()):
            continue
        lector = LECTORES.get(f.suffix.lower())
        if not lector:
            filas.append((rel, f.suffix or '—', '—', 0, '', 'formato no leído (imagen, video u otro): descríbeselo al agente si importa'))
            continue
        try:
            texto, info = lector(f)
        except Exception as ex:                          # noqa: BLE001
            filas.append((rel, f.suffix, '—', 0, '', f'no se pudo leer: {ex}'))
            continue
        texto = re.sub(r'[ \t]+\n', '\n', texto).strip()
        palabras = len(texto.split())
        aviso = ''
        if palabras < 30:
            aviso = 'casi sin texto: ¿es un documento escaneado? Hace falta una versión con texto o transcribirlo'
        dst = out / (str(rel) + '.txt')
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(texto + '\n', encoding='utf-8')
        primera = next((l.strip() for l in texto.splitlines() if len(l.strip()) > 12 and not l.startswith('===')), '')[:70]
        filas.append((rel, f.suffix.lower(), info, palabras, primera, aviso))
        total += palabras
    por = {}
    for r in filas:
        por.setdefault(r[0].parts[0] if len(r[0].parts) > 1 else '(raíz)', []).append(r)
    md = ['# Inventario de los documentos del docente', '',
          f'{len(filas)} archivo(s), {total:,} palabras de texto extraído en `fuentes/_texto/`. `fuentes/privado/` no se lee.'.replace(',', '.'), '']
    for carpeta, rs in por.items():
        md += [f'## {carpeta}', '', '| Archivo | Tipo | Tamaño | Palabras | Empieza así | Aviso |', '|---|---|---|---|---|---|']
        md += [f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4].replace("|", "/")} | {r[5]} |' for r in rs] + ['']
    vacias = [c for c in ('silabo', 'silabos-anteriores', 'presentaciones', 'guias-practicas', 'lecturas') if c not in por]
    if vacias:
        md += ['## Carpetas sin documentos', '', ', '.join(vacias) + '.', '']
    (src / 'INVENTARIO.md').write_text('\n'.join(md), encoding='utf-8')
    print('\n'.join(md))
    return 0


if __name__ == '__main__':
    sys.exit(main())
