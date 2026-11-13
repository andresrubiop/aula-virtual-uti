#!/usr/bin/env python3
"""Genera HTML paginado desde GUIA_DE_USO.md. Requiere markdown2.
Uso: python tools/generar_guia.py [salida.html]
Después: node tools/imprimir_guia.mjs salida.html GUIA_DE_USO.pdf
"""
from pathlib import Path
import base64
import html
import re
import sys
import markdown2

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'GUIA_DE_USO.md'
TEXT = SOURCE.read_text(encoding='utf-8')
BASE = 'https://github.com/andresrubiop/aula-virtual-uti/blob/main/'
ASSETS = ROOT / 'aula-virtual-uti/assets/plantilla-aula'

def uri(path, mime):
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()

def between(start, end=None):
    a = TEXT.index(start) + len(start)
    b = TEXT.index(end, a) if end else len(TEXT)
    return TEXT[a:b].strip()

def render(md):
    result = markdown2.markdown(md, extras=['tables', 'fenced-code-blocks'])
    result = re.sub(r'href="(?!https?://|#|mailto:)([^"]+)"', lambda m: 'href="' + BASE + m[1] + '"', result)
    return result

h = [None] + [re.search(r'^## '+str(i)+r'\. .+$', TEXT, re.M)[0] for i in range(1,10)]
pages = [
 ('01 · PREPARAR', 'Una carpeta, todos los insumos', 'Organiza tus documentos antes de pedir que se construya el aula.', between(h[1], h[2]), '¿Está identificado el sílabo vigente? ¿Las guías y lecturas están separadas? ¿La carpeta aula/ aún no existe o está vacía?'),
 ('02 · ELEGIR ASISTENTE', 'Instalar Claude Code', 'Sigue esta página si trabajarás con Claude. Para Codex, pasa a la siguiente.', between(h[2], '### Opción B: Codex'), 'Abre una terminal nueva y comprueba claude --version. Debes poder iniciar sesión con tu cuenta.'),
 ('02 · ELEGIR ASISTENTE', 'Instalar Codex y revisar el equipo', 'Elige Codex si prefieres trabajar con tu acceso de ChatGPT.', between('### Opción B: Codex', h[3]), 'Comprueba codex --version. Pide al asistente verificar Python, Node y el navegador antes de construir.'),
 ('03 · CARGAR LA SKILL', 'Instalar la carpeta completa', 'La skill aporta las instrucciones, las herramientas y la plantilla del aula.', between(h[3], h[4]), 'La ruta debe terminar en aula-virtual-uti/SKILL.md una sola vez. No copies únicamente ese archivo.'),
 ('04 · PRIMERA SESIÓN', 'Tu primer pedido al asistente', 'Abre MiAula-B26 y pega el mensaje dentro de Claude Code o Codex.', between(h[4], h[5]), 'Al terminar esta sesión debes tener un inventario, dudas concretas y un estado guardado; no necesitas un curso completo todavía.'),
 ('05 · PLAN DE TRABAJO', 'Avanzar por fases', 'Cada fase puede ocupar una o varias sesiones. Revisa antes de extender el piloto.', between(h[5], '**`aula/ESTADO.md` es el registro principal.**'), 'Elige un objetivo para hoy. Una fase pendiente de revisión docente sigue pendiente, aunque el archivo ya exista.'),
 ('05 · CONTINUIDAD', 'Cerrar hoy. Retomar mañana.', 'El estado vive en los archivos del aula y permite cambiar de asistente.', '**`aula/ESTADO.md` es el registro principal.**\n\n' + between('**`aula/ESTADO.md` es el registro principal.**', h[6]), 'Antes de cerrar: guarda los archivos, actualiza ESTADO.md y comprueba que la siguiente acción esté escrita.'),
 ('06 · GOOGLE Y VIDEOS', 'NotebookLM: camino guiado', 'Tú controlas el acceso a Google y los documentos que se enviarán.', between(h[6], '### Automatización opcional con el asistente'), 'Comprueba el perfil de Google y las fuentes elegidas. Revisa el video completo antes de incorporarlo.'),
 ('06 · VIDEOS OPCIONALES', 'Automatizar cuando sea posible', 'Usa una integración compatible solo cuando la sesión y la operación estén autorizadas.', between('### Automatización opcional con el asistente', h[7]), 'Si la herramienta o la cuota fallan, continúa con el aula y conserva los guiones. No repitas una generación sin comprobar su estado.'),
 ('07 · REVISAR LA ENTREGA', 'Qué abrir y qué compartir', 'El asistente debe darte enlaces concretos a tus archivos finales.', between(h[7], h[8]), 'La edición del profesor puede contener material reservado. Entrega la edición estudiantil y revisa los pendientes.'),
 ('08 · CANVAS INDOAMÉRICA', 'Importar en el curso correcto', 'Usa primero un curso de ensayo y confirma el período antes de importar.', between(h[8], '### Revisar antes de publicar'), 'Selecciona un archivo .imscc. La skill .skill y el aula .html cumplen funciones diferentes.'),
 ('08 · REVISIÓN FINAL', 'Comprobar antes de publicar', 'La importación solo está terminada cuando revisaste lo que ve el estudiante.', between('### Revisar antes de publicar', h[9]), 'Registra en ESTADO.md el curso, la fecha, el paquete utilizado y el resultado real de la revisión.'),
 ('09 · AYUDA Y REFERENCIA', 'Si algo no funciona', 'Conserva el mensaje de error y el estado; pide corregir el punto concreto.', between(h[9]), 'Para pedir ayuda: indica sistema operativo, fase actual, archivo o paso y mensaje exacto. Nunca envíes contraseñas.'),
]

font = uri(ASSETS/'hub/vendor/fonts/Poppins-400.woff2', 'font/woff2')
bold = uri(ASSETS/'hub/vendor/fonts/Poppins-700.woff2', 'font/woff2')
mono = uri(ASSETS/'hub/vendor/fonts/JetBrainsMono-400.woff2', 'font/woff2')
logo = uri(ASSETS/'identidad-uti/logo-uti-horizontal-color.png', 'image/png')
css = '''
@page { size: A4; margin: 0; }
* {box-sizing:border-box} html,body{margin:0;padding:0}
body{font-family:Poppins,Arial,sans-serif;color:#282334;background:#e9e6ec;font-size:10pt;line-height:1.56}
.sheet{width:210mm;height:297mm;background:white;position:relative;page-break-after:always;padding:18mm 18mm 19mm;overflow:visible}
.sheet:last-child{page-break-after:auto}
.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e5ddeb;padding-bottom:4mm;margin-bottom:6mm;color:#6b5b7c;font-size:8pt;letter-spacing:.035em}
.top img{width:42mm}.body{height:239mm}
.eyebrow{color:#be4e08;font-weight:700;letter-spacing:.1em;font-size:8.5pt;text-transform:uppercase;margin:0 0 3mm}
h1{color:#3c235f;font-size:25pt;line-height:1.13;letter-spacing:-.035em;margin:0 0 4mm;font-weight:700}
.lead{color:#665674;font-size:11pt;margin:0 0 5mm;line-height:1.5}
h2{font-size:18pt;color:#3c235f;line-height:1.3;margin:6mm 0 3mm}h3{font-size:12pt;color:#3c235f;margin:4mm 0 2mm}
p{margin:0 0 3mm}li{margin:0 0 2mm}ol,ul{padding-left:5mm;margin:2mm 0 4mm}
a{color:#613691;text-decoration:underline;text-underline-offset:2px;overflow-wrap:anywhere}
strong{font-weight:700;color:#3c235f}
code{font-family:Mono,monospace;font-size:.88em;color:#402358;background:#f1edf6;border-radius:3px;padding:.3mm 1mm;overflow-wrap:anywhere}
pre{background:#f3f0f7;border:1px solid #dfd5eb;border-left:3px solid #3c235f;padding:3mm 4mm;border-radius:4px;font-size:9pt;line-height:1.45;white-space:pre-wrap;overflow-wrap:anywhere;margin:3mm 0 4mm}pre code{padding:0;background:transparent}
blockquote{border-left:3px solid #ea600a;background:#fff5ec;border-radius:0 5px 5px 0;margin:3mm 0 4mm;padding:4mm 5mm;font-size:10pt}blockquote p:last-child{margin:0}
table{width:100%;border-collapse:collapse;table-layout:auto;margin:3mm 0 4mm;font-size:8.9pt;line-height:1.45}th{text-align:left;background:#3c235f;color:white;padding:2.7mm}td{border-bottom:1px solid #e5ddeb;padding:2.5mm;vertical-align:top;overflow-wrap:anywhere}tr:nth-child(even) td{background:#f7f4fa}td code{font-size:8pt}th,td{max-width:95mm}
.check{margin-top:5mm;padding:4mm 5mm;border:1px solid #b9d6cb;border-left:4px solid #27725c;border-radius:5px;background:#f2faf6;font-size:9pt}.check b{display:block;letter-spacing:.05em;font-size:8pt;color:#23604e;margin-bottom:1mm}
footer{position:absolute;bottom:10mm;left:18mm;right:18mm;display:flex;justify-content:space-between;border-top:1px solid #e5ddeb;padding-top:3mm;font-size:8pt;color:#786b82}
.cover{background:linear-gradient(145deg,#fff 55%,#f1ebf8);padding-top:24mm}.cover .brand{width:64mm;margin-bottom:24mm}.cover h1{font-size:43pt;max-width:155mm;line-height:1.1}.cover .subtitle{font-size:19pt;color:#685377;max-width:150mm;margin-top:8mm}.rule{height:3mm;width:27mm;background:#ea600a;margin:9mm 0}.tag{display:inline-block;background:#3c235f;color:white;padding:2mm 4mm;border-radius:99px;font-size:9pt;margin:1mm 1mm 1mm 0}.cover .note{margin-top:16mm;border-top:1px solid #d8cde3;padding-top:7mm;font-size:11pt}.author{margin-top:9mm;color:#3c235f;font-weight:700}
.map{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm;margin:5mm 0}.tile{padding:4mm;background:#f4f0f8;border:1px solid #e3d9ed;border-radius:6px}.tile b{display:block;color:#3c235f;margin-bottom:1mm}.tile p{font-size:9pt;margin:0}
.index{display:grid;grid-template-columns:1fr 1fr;gap:1mm 6mm}.index a{display:flex;justify-content:space-between;gap:4mm;padding:2.5mm 0;border-bottom:1px solid #e6deec;text-decoration:none;font-size:9pt}.index span{font-weight:700;color:#be4e08}
.flow{display:flex;gap:2mm;align-items:center;justify-content:space-between;margin:6mm 0;padding:4mm;border-radius:6px;background:#3c235f;color:white;font-size:9pt}.flow b{color:#ffb17d}
.ticklist{list-style:none;padding:0}.ticklist li{padding-left:6mm;position:relative}.ticklist li:before{content:"";position:absolute;left:0;top:1.3mm;width:3mm;height:3mm;border:1px solid #71548a;border-radius:2px}.glossary{grid-template-columns:1fr 1fr}.compact{font-size:9.4pt;line-height:1.48}.compact h3{font-size:11.4pt}.compact li{margin-bottom:1.5mm}.compact table{font-size:8.5pt}.compact p{margin-bottom:2.5mm}
@media screen{.sheet{margin:8mm auto;box-shadow:0 2px 14px #0002}}@media print{body{background:white}*{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
'''
css = '@font-face{font-family:Poppins;src:url('+font+')}@font-face{font-family:Poppins;src:url('+bold+');font-weight:700}@font-face{font-family:Mono;src:url('+mono+')}' + css

def footer(n):
    return f'<footer><span>AULA VIRTUAL UTI · GUÍA DEL PROFESOR</span><span>{n:02} / 15</span></footer>'

cover=f'''<section class="sheet cover" id="p1"><img class="brand" src="{logo}" alt="Universidad Tecnológica Indoamérica"><p class="eyebrow">APRENDE HACIENDO · PASO A PASO</p><h1>Del sílabo<br>al aula virtual</h1><p class="subtitle">Tu guía para trabajar con<br>Claude Code o Codex</p><div class="rule"></div><p><span class="tag">Linux</span><span class="tag">macOS</span><span class="tag">Windows</span></p><p class="note">Organiza tus documentos, crea un aula HTML bilingüe,<br>prepara videos y entrega el curso en Canvas.<br><strong>Una fase a la vez, con el avance siempre guardado.</strong></p><p class="author">Andrès Rubio Proaño</p><p>Edición docente · 13 de noviembre de 2026</p><p><a href="{BASE}GUIA_DE_USO.md">Abrir la guía en GitHub</a></p>{footer(1)}</section>'''
index=''.join(f'<a href="#p{i}">{html.escape(title)}<span>{i:02}</span></a>' for i,(_,title,_,_,_) in enumerate(pages,3))
intro=f'''<section class="sheet" id="p2"><header class="top"><img src="{logo}" alt="UTI"><span>ORIENTACIÓN</span></header><main class="body"><p class="eyebrow">ANTES DE COMENZAR</p><h1>Un recorrido que puedes retomar</h1><p class="lead">No necesitas terminar en un día ni saber programar. Elige un asistente y trabaja por etapas.</p><div class="map"><div class="tile"><b>Tú decides</b><p>Documentos, objetivos, criterios académicos y aprobación del aula.</p></div><div class="tile"><b>El asistente construye</b><p>Organiza fuentes, crea archivos y ejecuta las comprobaciones.</p></div><div class="tile"><b>ESTADO.md recuerda</b><p>Qué está listo, qué falta y el próximo paso para mañana.</p></div></div><div class="flow">Documentos <b>→</b> Piloto <b>→</b> Aula revisada <b>→</b> Canvas</div><h3>Encuentra tu siguiente paso</h3><nav class="index">{index}</nav><div class="check"><b>CÓMO USAR ESTA GUÍA</b>Lee una página, realiza la tarea y comprueba el recuadro verde. Las cajas naranjas contienen mensajes para el asistente; las grises, comandos o rutas. Los enlaces son pulsables.</div><p style="margin-top:5mm;font-size:9pt">Las presentaciones son HTML embebido en el aula, con estructura y stack FSO. Los PDF son exportaciones. El contenido académico procede del sílabo vigente de tu materia.</p></main>{footer(2)}</section>'''
extras = {
 11: '<h3>Decide el siguiente paso</h3><div class="map"><div class="tile"><b>Hay herramienta y acceso</b><p>Autoriza la operación concreta y verifica el resultado.</p></div><div class="tile"><b>Hay cuenta, sin herramienta</b><p>Genera tú en el navegador con el guion preparado.</p></div><div class="tile"><b>No hay acceso o cuota</b><p>Continúa con el aula y deja videos como pendientes.</p></div></div>',
 14: '<h3>Lista de revisión del profesor</h3><ul class="ticklist"><li>Curso y período correctos.</li><li>Presentaciones, PDF y enlaces accesibles.</li><li>Contenidos en español e inglés revisados.</li><li>Tareas, fechas, puntajes y publicación comprobados.</li><li>Vista del estudiante recorrida.</li><li>Resultado y pendientes guardados en ESTADO.md.</li></ul>',
 15: '<h3>Cuatro palabras que usarás</h3><p><strong>Skill:</strong> instrucciones y herramientas del asistente. <strong>Terminal:</strong> ventana de comandos. <strong>Markdown (.md):</strong> texto que guarda decisiones y avance. <strong>.imscc:</strong> paquete que importas en Canvas.</p>'
}
output=[cover,intro]
for n,(tag,title,lead,md,check) in enumerate(pages,3):
    compact=' compact' if n in (5,6,7,13,15) else ''
    output.append(f'<section class="sheet" id="p{n}"><header class="top"><img src="{logo}" alt="UTI"><span>CLAUDE CODE / CODEX</span></header><main class="body{compact}"><p class="eyebrow">{html.escape(tag)}</p><h1>{html.escape(title)}</h1><p class="lead">{html.escape(lead)}</p><div class="content">{render(md)}{extras.get(n, "")}</div><aside class="check"><b>ANTES DE SEGUIR</b>{html.escape(check)}</aside></main>{footer(n)}</section>')
file=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'GUIA_DE_USO.html'
file.write_text('<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Guía del profesor · Aula Virtual UTI</title><style>'+css+'</style></head><body>'+''.join(output)+'</body></html>',encoding='utf8')
print(f'{file}: {len(output)} páginas diseñadas')
