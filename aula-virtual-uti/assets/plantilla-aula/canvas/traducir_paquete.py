#!/usr/bin/env python3
"""Integra traducciones revisadas en un paquete Canvas, sin servicios externos.

python3 canvas/traducir_paquete.py salida/curso-canvas.imscc --inventario
python3 canvas/traducir_paquete.py salida/curso-canvas.imscc
Rutas relativas del paquete: desde cwd. Traducciones: canvas/traducciones.en.json.
El inventario conserva traducciones previas; si cambia la fuente exige revisarlas.
"""
import argparse
import hashlib
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def local(tag):
    return tag.rsplit('}', 1)[-1]

def child(el, name):
    return next((x for x in el if local(x.tag) == name), None)

def title(text):
    m = re.search(r'<title>(.*?)</title>', text, re.S)
    return html.unescape(m[1]) if m else ''

def body(text):
    m = re.search(r'<body\b[^>]*>(.*?)</body>', text, re.S | re.I)
    if not m:
        raise ValueError('HTML sin body')
    return m[1]

def scan(data):
    result = {'pages': {}, 'assignments': {}, 'modules': {}}
    for name, content in data.items():
        if name.startswith('wiki_content/') and name.endswith('.html'):
            text = content.decode('utf-8')
            if re.search(r'name=[\"\']workflow_state[\"\']\s+content=[\"\'](?:unpublished|deleted)', text):
                continue
            result['pages'][Path(name).stem] = {'path': name, 'source_sha256': sha(content), 'source_title': title(text), 'source_html': body(text)}
        if name.endswith('/assignment_settings.xml'):
            node = ET.fromstring(content)
            state = child(node, 'workflow_state')
            if state is not None and state.text == 'deleted':
                continue
            folder = str(Path(name).parent)
            pages = [n for n in data if str(Path(n).parent) == folder and n.endswith('.html')]
            if len(pages) != 1:
                raise ValueError(f'Tarea {folder}: se esperaba un único HTML')
            page = pages[0]
            text = data[page].decode('utf-8')
            result['assignments'][folder] = {'path': page, 'settings': name, 'source_sha256': sha(data[page]), 'source_title': child(node, 'title').text or '', 'source_html': body(text)}
    mm = ET.fromstring(data['course_settings/module_meta.xml'])
    for node in mm:
        if local(node.tag) != 'module':
            continue
        state = child(node, 'workflow_state')
        if state is not None and state.text != 'active':
            continue
        result['modules'][node.attrib['identifier']] = {'source_sha256': sha(ET.tostring(node)), 'source_title': child(node, 'title').text or ''}
    return result

def references(text):
    return set(re.findall(r'(?:\$WIKI_REFERENCE\$|\$IMS-CC-FILEBASE\$|\$CANVAS_OBJECT_REFERENCE\$)[^\s\"<>]+', html.unescape(text)))

def run(args):
    if args.paquete.stem.endswith('-bilingue'):
        raise ValueError('Usa el paquete base, no uno ya bilingüe.')
    with zipfile.ZipFile(args.paquete) as z:
        infos = z.infolist()
        if len({i.filename for i in infos}) != len(infos):
            raise ValueError('El ZIP tiene rutas duplicadas.')
        data = {i.filename: z.read(i) for i in infos}
    current = scan(data)
    translations = json.loads(args.traducciones.read_text()) if args.traducciones.exists() else {}
    if args.inventario:
        for group, entries in current.items():
            dest = translations.setdefault(group, {})
            for key, source in entries.items():
                if key not in dest:
                    dest[key] = {**source, 'title': '', **({'html': ''} if group != 'modules' else {})}
                elif dest[key].get('source_sha256') != source['source_sha256']:
                    print(f'REVISAR {group}/{key}: cambió la fuente; se conserva traducción previa y hash antiguo.')
                    dest[key]['current_source'] = source
        args.traducciones.parent.mkdir(parents=True, exist_ok=True)
        args.traducciones.write_text(json.dumps(translations, ensure_ascii=False, indent=2) + '\n')
        print(f'Inventario: {args.traducciones}; completa title/html en inglés. No es traducción automática.')
        return
    errors = []
    for group, entries in current.items():
        for key, source in entries.items():
            tr = translations.get(group, {}).get(key, {})
            label = f'{group}/{key}'
            if tr.get('source_sha256') != source['source_sha256']:
                errors.append(f'{label}: traducción ausente o fuente modificada')
            if not isinstance(tr.get('title'), str) or not tr['title'].strip():
                errors.append(f'{label}: falta título inglés')
            if group != 'modules':
                content = tr.get('html', '')
                if not isinstance(content, str) or not re.sub('<[^>]*>', '', content).strip():
                    errors.append(f'{label}: falta HTML inglés')
                elif re.search(r'<(?:script|html|body)\b|\bon\w+\s*=', content, re.I):
                    errors.append(f'{label}: usa solo fragmentos HTML sin scripts ni manejadores')
                elif references(content) != references(source['source_html']):
                    errors.append(f'{label}: cambian las referencias a páginas, archivos o tareas')
    if errors:
        raise ValueError('\n'.join(errors))
    titles = {}
    for group in ('pages', 'assignments'):
        for key, source in current[group].items():
            tr = translations[group][key]
            joined = source['source_title'] + ' / ' + tr['title'].strip()
            text = data[source['path']].decode('utf-8')
            english = tr['html']
            # El prefijo evita IDs duplicados dentro de una misma página bilingüe.
            english = re.sub(r'\bid=([\"\'])([^\"\']+)\1', lambda m: f'id={m[1]}en-{m[2]}{m[1]}', english)
            english = re.sub(r'href=([\"\'])#([^\"\']+)\1', lambda m: f'href={m[1]}#en-{m[2]}{m[1]}', english)
            bilingual = '<section lang="es"><h2>Español</h2>' + source['source_html'] + '</section>\n<section lang="en"><h2>English</h2>' + english + '</section>'
            text = re.sub(r'(<body\b[^>]*>).*?(</body>)', lambda m: m[1] + bilingual + m[2], text, flags=re.S | re.I)
            text = re.sub(r'<title>.*?</title>', lambda m: '<title>' + html.escape(joined) + '</title>', text, count=1, flags=re.S)
            data[source['path']] = text.encode()
            if group == 'pages':
                match = re.search(r'name="identifier" content="([^"]+)"', text)
                if match:
                    titles[match[1]] = joined
            else:
                titles[key] = joined
                node = ET.fromstring(data[source['settings']])
                child(node, 'title').text = joined
                data[source['settings']] = ET.tostring(node, encoding='utf-8', xml_declaration=True)
    for name in ('course_settings/module_meta.xml', 'imsmanifest.xml'):
        root = ET.fromstring(data[name])
        for node in root.iter():
            ident = node.get('identifier')
            if ident in current['modules']:
                t = child(node, 'title')
                if t is not None:
                    t.text = current['modules'][ident]['source_title'] + ' / ' + translations['modules'][ident]['title']
            ref = node.get('identifierref')
            refnode = child(node, 'identifierref')
            if refnode is not None:
                ref = refnode.text
            if ref in titles:
                t = child(node, 'title')
                if t is not None:
                    t.text = titles[ref]
        data[name] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    output = args.paquete.with_name(args.paquete.stem + '-bilingue.imscc')
    staged = output.with_suffix('.tmp')
    with zipfile.ZipFile(staged, 'w', zipfile.ZIP_DEFLATED) as z:
        for info in infos:
            z.writestr(info, data[info.filename])
    staged.replace(output)
    print(f'{output}: {sum(map(len, current.values()))} traducciones integradas; original conservado.')

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('paquete', type=Path)
    ap.add_argument('--inventario', action='store_true')
    ap.add_argument('--traducciones', type=Path, default=HERE / 'traducciones.en.json')
    args = ap.parse_args()
    try:
        run(args)
    except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as ex:
        print(f'ERROR: {ex}', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
