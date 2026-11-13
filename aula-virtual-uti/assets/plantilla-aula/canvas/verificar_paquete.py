#!/usr/bin/env python3
"""Valida XML, recursos, referencias y avisos de un paquete Canvas local."""
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent

def local(tag):
    return tag.rsplit('}', 1)[-1]

def main():
    files = [Path(sys.argv[1])] if len(sys.argv) > 1 else sorted((HERE / 'salida').glob('*.imscc'))
    if not files:
        print('ERROR: no hay paquete; ejecuta generar_canvas.py.')
        return 1
    pkg = files[-1]
    errors, warnings, roots = [], [], {}
    try:
        with zipfile.ZipFile(pkg) as z:
            names = set(z.namelist())
            if len(names) != len(z.namelist()):
                errors.append('Rutas duplicadas en ZIP')
            if z.testzip():
                errors.append('ZIP dañado')
            for name in sorted(n for n in names if n.endswith('.xml')):
                try:
                    roots[name] = ET.fromstring(z.read(name))
                except ET.ParseError as ex:
                    errors.append(f'{name}: XML inválido: {ex}')
            man = roots.get('imsmanifest.xml')
            mods = roots.get('course_settings/module_meta.xml')
            if man is None or mods is None:
                errors.append('Falta manifiesto o metadatos de módulos válidos')
            else:
                resources = [n for n in man.iter() if local(n.tag) == 'resource']
                ids = [n.get('identifier') for n in resources]
                if len(set(ids)) != len(ids):
                    errors.append('Identificadores de recurso duplicados')
                for node in man.iter():
                    if local(node.tag) == 'file' and node.get('href') not in names:
                        errors.append(f'Archivo ausente: {node.get("href")}')
                for node in mods.iter():
                    if local(node.tag) == 'identifierref' and node.text not in ids:
                        errors.append(f'Módulo apunta a recurso ausente: {node.text}')
                for name in sorted(n for n in names if n.endswith('.html')):
                    text = z.read(name).decode('utf-8', 'replace')
                    for ref in re.findall(r'\$IMS-CC-FILEBASE\$/([^"?<>\s]*)', text):
                        if 'web_resources/' + unquote(ref) not in names:
                            errors.append(f'{name}: archivo enlazado ausente {ref}')
                    for ref in re.findall(r'\$WIKI_REFERENCE\$/pages/([^"?<>\s]*)', text):
                        if ref not in ids:
                            errors.append(f'{name}: página enlazada ausente {ref}')
                    if '[COMPLETAR' in text:
                        warnings.append(f'{name}: contiene marcas COMPLETAR')
                    if name.startswith('wiki_content/') and not re.search(r'content="unpublished"', text):
                        if any(t in text for t in ('Copiar pegar del sílabo', 'TÍTULO DEL MOMENTO', 'Título de sesión')):
                            warnings.append(f'{name}: texto institucional de relleno')
    except (OSError, zipfile.BadZipFile) as ex:
        errors.append(str(ex))
    if pkg.exists() and pkg.stat().st_size > 480_000_000:
        warnings.append('Más de 480 MB: comprueba cuota real del curso')
    for text in errors:
        print('ERROR', text)
    for text in warnings:
        print('AVISO', text)
    print(f'{pkg.name}: {len(errors)} error(es), {len(warnings)} aviso(s). Revisión local; no acredita importación real.')
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
