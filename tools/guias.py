#!/usr/bin/env python3
"""Una sola fuente para la guía de uso: aula-virtual-uti/GUIA_DE_USO.md (la que viaja en la skill).

    python3 tools/guias.py generar      # escribe GUIA_DE_USO.md de la raíz del repositorio desde la de la skill
    python3 tools/guias.py comprobar    # código 1 si la raíz no coincide o el PDF no corresponde a la guía actual
    python3 tools/guias.py pdf          # tras regenerar el PDF: anota la huella de la guía y del PDF en tools/guia-pdf.json

La guía de la raíz es la misma con dos diferencias: el enlace al PDF bajo el título y los enlaces relativos a la
skill con el prefijo aula-virtual-uti/. No edites la guía de la raíz: edita la de la skill y ejecuta «generar».
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FUENTE = ROOT / 'aula-virtual-uti' / 'GUIA_DE_USO.md'
RAIZ = ROOT / 'GUIA_DE_USO.md'
PDF = ROOT / 'GUIA_DE_USO.pdf'
REGISTRO = ROOT / 'tools' / 'guia-pdf.json'
ENLACE_PDF = '**[Descargar la guía didáctica en PDF](GUIA_DE_USO.pdf)** · 15 páginas con pasos, mensajes para copiar y listas de comprobación.'


def raiz_desde_fuente(texto):
    titulo, resto = texto.split('\n', 1)
    resto = resto.lstrip('\n')
    cuerpo = re.sub(r'\]\((?!https?://|#|mailto:|GUIA_DE_USO\.pdf)([^)\s]+)\)', r'](aula-virtual-uti/\1)', resto)
    return f'{titulo}\n\n{ENLACE_PDF}\n\n{cuerpo}'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    orden = sys.argv[1] if len(sys.argv) > 1 else 'comprobar'
    esperado = raiz_desde_fuente(FUENTE.read_text(encoding='utf-8'))
    if orden == 'generar':
        RAIZ.write_text(esperado, encoding='utf-8', newline='\n')
        print(f'{RAIZ.name} generada desde aula-virtual-uti/GUIA_DE_USO.md')
        return 0
    if orden == 'pdf':
        REGISTRO.write_text(json.dumps({'guia_sha256': sha(RAIZ), 'pdf_sha256': sha(PDF)}, indent=1) + '\n', encoding='utf-8', newline='\n')
        print(f'Registrado: guía {sha(RAIZ)[:12]}… · PDF {sha(PDF)[:12]}…')
        return 0
    problemas = []
    if RAIZ.read_text(encoding='utf-8') != esperado:
        problemas.append('GUIA_DE_USO.md de la raíz no coincide con la de la skill: ejecuta python3 tools/guias.py generar')
    reg = json.loads(REGISTRO.read_text(encoding='utf-8')) if REGISTRO.exists() else {}
    if reg.get('guia_sha256') != sha(RAIZ):
        problemas.append('El PDF se generó con otra versión de la guía: regenera el PDF (tools/README.md) y ejecuta python3 tools/guias.py pdf')
    elif reg.get('pdf_sha256') != sha(PDF):
        problemas.append('GUIA_DE_USO.pdf cambió después de registrarlo: regenéralo y ejecuta python3 tools/guias.py pdf')
    for p in problemas:
        print('✗', p)
    if not problemas:
        print('✓ Guía de la raíz, guía de la skill y PDF coinciden.')
    return 1 if problemas else 0


if __name__ == '__main__':
    sys.exit(main())
