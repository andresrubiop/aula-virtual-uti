#!/usr/bin/env python3
"""Actualiza un curso de Canvas desde el paquete del aula mediante la API, sin importar el .imscc.

Sirve cuando el curso ya tiene la plantilla institucional y el docente no puede borrar páginas: importar el paquete
duplicaría páginas. Con la API se actualiza cada página en su lugar, se crean solo las que faltan y los enlaces
apuntan a las páginas, archivos y tareas reales del curso. Repetir la ejecución actualiza; no duplica.

    python3 canvas/canvas_api.py token                      # el DOCENTE guarda su token (entrada oculta) — una vez
    python3 canvas/canvas_api.py configurar --curso https://indoamerica.instructure.com/courses/12345
    python3 canvas/canvas_api.py comprobar                  # solo lectura: acceso, permisos e inventario del curso
    python3 canvas/canvas_api.py plan                       # solo lectura: qué se subiría, actualizaría y crearía
    python3 canvas/canvas_api.py aplicar                    # respaldo del curso y aplicación del plan
    python3 canvas/canvas_api.py verificar                  # solo lectura: enlaces, marcas pendientes y publicación
    python3 canvas/canvas_api.py inicio [--aplicar]         # solo el aula incrustada al comienzo de Inicio

Reglas: las tareas nuevas se crean sin publicar y las existentes conservan puntos y publicación; la página Inicio no
se reemplaza (solo se antepone el aula); las páginas sin uso se despublican y salen de los módulos (no se borran);
los módulos del curso que no están en el paquete no se tocan. Antes de aplicar se guarda el contenido actual del curso
en canvas/api/privado/. El token se lee de la variable CANVAS_TOKEN o de ~/.config/aula-uti/canvas-token; nunca se
imprime ni se guarda en el aula. No se leen ni registran datos de estudiantes (solo conteos).
"""
import argparse
import getpass
import html
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DIR = HERE / 'api'
CONFIG = DIR / 'config.json'
MAPA = DIR / 'mapa.json'
REGISTRO = DIR / 'operaciones.jsonl'
PRIVADO = DIR / 'privado'
TOKEN_FILE = Path.home() / '.config' / 'aula-uti' / 'canvas-token'
NS = {'c': 'http://canvas.instructure.com/xsd/cccv1p0'}
PENDIENTES = re.compile(r'\[COMPLETAR[^\]]*\]|correo@indoamerica\.edu\.ec|Agregar los RA|Copiar pegar del sílabo')
SIN_RESOLVER = re.compile(r'\$(IMS-CC-FILEBASE|WIKI_REFERENCE|CANVAS_[A-Z_]+)\$')
AULA_INICIO = re.compile(r'<!--aula-inicio-->.*?<!--/aula-inicio-->', re.S)


# ── Configuración y acceso ─────────────────────────────────────────────────────
def cfg():
    if not CONFIG.exists():
        sys.exit('Falta configurar el curso: python3 canvas/canvas_api.py configurar --curso <URL del curso>')
    return json.loads(CONFIG.read_text(encoding='utf-8'))


def token():
    t = os.environ.get('CANVAS_TOKEN', '').strip()
    if not t and TOKEN_FILE.exists():
        t = TOKEN_FILE.read_text(encoding='utf-8').strip()
    if not t:
        sys.exit('No hay token de Canvas. El docente lo crea en Canvas (Cuenta → Configuraciones → Nuevo token de acceso) '
                 'y lo guarda con: python3 canvas/canvas_api.py token')
    return t


class Canvas:
    def __init__(self, c):
        self.dominio, self.curso = c['dominio'].rstrip('/'), c['curso']
        self.api = f'{self.dominio}/api/v1/courses/{self.curso}'
        self._t = token()

    def registrar(self, entry):
        DIR.mkdir(exist_ok=True)
        with REGISTRO.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'fecha_utc': datetime.now(timezone.utc).isoformat(), **entry}, ensure_ascii=False) + '\n')

    def pedir(self, metodo, url, datos=None):
        url = url if url.startswith('http') else self.api + url
        cuerpo = json.dumps(datos).encode('utf-8') if datos is not None else None
        cab = {'Accept': 'application/json', 'Authorization': 'Bearer ' + self._t}
        if cuerpo is not None:
            cab['Content-Type'] = 'application/json'
        ruta = url.replace(self.dominio, '')
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=cuerpo, method=metodo, headers=cab), timeout=120) as r:
                txt, enlace, estado = r.read().decode('utf-8'), r.headers.get('Link', ''), r.status
        except urllib.error.HTTPError as ex:
            detalle = ex.read().decode('utf-8', 'replace')[:300]
            if metodo != 'GET':
                self.registrar({'metodo': metodo, 'ruta': ruta, 'estado': ex.code, 'error': detalle})
            if ex.code == 401:
                raise SystemExit('Canvas rechazó el token (401): puede haber caducado o sido revocado.') from None
            raise RuntimeError(f'{metodo} {ruta} → HTTP {ex.code}: {detalle}') from None
        if metodo != 'GET':
            self.registrar({'metodo': metodo, 'ruta': ruta, 'estado': estado})
        return (json.loads(txt) if txt.strip() else None), enlace

    def get(self, ruta):
        return self.pedir('GET', ruta)[0]

    def todos(self, ruta, params=None):
        url = self.api + ruta + '?' + urllib.parse.urlencode({'per_page': 100, **(params or {})}, doseq=True)
        out = []
        while url:
            data, enlace = self.pedir('GET', url)
            out += data
            m = re.search(r'<([^>]+)>;\s*rel="next"', enlace)
            url = m[1] if m else None
        return out

    def subir(self, datos, nombre, carpeta):
        """Carga de archivos de Canvas en tres pasos: aviso, envío multiparte y confirmación."""
        tipo = mimetypes.guess_type(nombre)[0] or 'application/octet-stream'
        p1, _ = self.pedir('POST', '/files', {'name': nombre, 'size': len(datos), 'content_type': tipo,
                                              'parent_folder_path': carpeta, 'on_duplicate': 'rename'})
        lim = uuid.uuid4().hex
        partes = [f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode('utf-8') for k, v in p1['upload_params'].items()]
        partes.append(f'--{lim}\r\nContent-Disposition: form-data; name="file"; filename="{urllib.parse.quote(nombre)}"\r\n'
                      f'Content-Type: {tipo}\r\n\r\n'.encode('utf-8') + datos + b'\r\n' + f'--{lim}--\r\n'.encode('utf-8'))
        req = urllib.request.Request(p1['upload_url'], data=b''.join(partes), method='POST',
                                     headers={'Content-Type': f'multipart/form-data; boundary={lim}'})

        class SinRedireccion(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        try:
            with urllib.request.build_opener(SinRedireccion).open(req, timeout=300) as r:
                txt, estado, destino = r.read().decode('utf-8'), r.status, r.headers.get('Location')
        except urllib.error.HTTPError as ex:
            if ex.code not in (301, 302, 303):
                raise RuntimeError(f'Carga de {nombre} → HTTP {ex.code}') from None
            txt, estado, destino = '', ex.code, ex.headers.get('Location')
        info = self.get(destino) if destino else json.loads(txt)
        if 'id' not in info and info.get('location'):
            info = self.get(info['location'])
        self.registrar({'metodo': 'UPLOAD', 'ruta': f'/files ({carpeta}/{nombre})', 'estado': estado, 'id': info.get('id')})
        return info


# ── Paquete ────────────────────────────────────────────────────────────────────
def paquete_por_omision():
    ps = sorted((ROOT / 'canvas' / 'salida').glob('*-aula-canvas.imscc'), key=lambda p: p.stat().st_mtime)
    if not ps:
        sys.exit('No hay paquete en canvas/salida/: python3 canvas/generar_canvas.py')
    return ps[-1]


def cuerpo(texto):
    m = re.search(r'<body[^>]*>(.*)</body>', texto, re.S | re.I)
    return m[1].strip() if m else texto


def meta(texto, nombre):
    m = re.search(rf'<meta name="{nombre}" content="([^"]*)"', texto)
    return html.unescape(m[1]) if m else None


def leer_paquete(ruta):
    z = zipfile.ZipFile(ruta)
    man = ET.fromstring(z.read('imsmanifest.xml'))
    recursos = {r.get('identifier'): {'href': r.get('href'), 'archivos': [f.get('href') for f in r if f.tag.endswith('}file')]}
                for r in man.iter() if r.tag.endswith('}resource')}
    paginas = {}
    for n in z.namelist():
        if n.startswith('wiki_content/') and n.endswith('.html'):
            t = z.read(n).decode('utf-8')
            slug = n[len('wiki_content/'):-5]
            paginas[slug] = {'identificador': meta(t, 'identifier'), 'titulo': html.unescape(re.search(r'<title>(.*?)</title>', t, re.S)[1]).strip(),
                             'publicada': (meta(t, 'workflow_state') or 'active') == 'active', 'cuerpo': cuerpo(t)}
    tareas = {}
    for ident, r in recursos.items():
        conf = next((f for f in r['archivos'] if f.endswith('assignment_settings.xml')), None)
        if not conf:
            continue
        s = ET.fromstring(z.read(conf))
        campo = lambda k: (s.find(f'c:{k}', NS).text if s.find(f'c:{k}', NS) is not None else None)
        htmlf = next(f for f in r['archivos'] if f.endswith('.html'))
        tareas[ident] = {'titulo': campo('title'), 'cuerpo': cuerpo(z.read(htmlf).decode('utf-8')), 'puntos': float(campo('points_possible') or 0),
                         'calificacion': campo('grading_type'), 'entrega': campo('submission_types'), 'omitir': campo('omit_from_final_grade') == 'true',
                         'estado': campo('workflow_state')}
    modulos = []
    for m in ET.fromstring(z.read('course_settings/module_meta.xml')).findall('c:module', NS):
        items = []
        for it in m.findall('.//c:item', NS):
            g = lambda k: (it.find(f'c:{k}', NS).text if it.find(f'c:{k}', NS) is not None else None)
            items.append({'tipo': g('content_type'), 'titulo': g('title'), 'ref': g('identifierref'), 'sangria': int(g('indent') or 0)})
        modulos.append({'titulo': m.find('c:title', NS).text, 'publicado': m.find('c:workflow_state', NS).text == 'active', 'items': items})
    archivos = {n[len('web_resources/'):]: n for n in z.namelist() if n.startswith('web_resources/') and not n.endswith('/')}
    adjuntos = {i: r['href'][len('web_resources/'):] for i, r in recursos.items() if (r['href'] or '').startswith('web_resources/')}
    quizzes = {}
    for n in z.namelist():   # el identificador del cuestionario es el nombre de su archivo QTI
        if n.startswith('non_cc_assessments/') and n.endswith('.xml.qti'):
            m = re.search(r'<assessment[^>]*title="([^"]*)"', z.read(n).decode('utf-8', 'replace'))
            if m:
                quizzes[n.split('/')[-1][:-len('.xml.qti')]] = html.unescape(m[1])
    return z, paginas, tareas, modulos, archivos, adjuntos, quizzes


def es_inicio(p):
    return p['titulo'].casefold() == 'inicio' or bool(AULA_INICIO.search(p['cuerpo']))


def reescribir(c, texto, archivos_id, urls, tareas_id, quizzes_id):
    def archivo(m):
        fid = archivos_id[urllib.parse.unquote(m['ruta'])]
        q = html.unescape(m['q'] or '')
        if 'canvas_download=1' in q:
            return f'/courses/{c.curso}/files/{fid}/download' + ('?download_frd=1' if 'download_frd' in q else '')
        return f'/courses/{c.curso}/files/{fid}' + ('?wrap=1' if 'wrap=1' in q else '/preview')
    texto = re.sub(r'\$IMS-CC-FILEBASE\$/(?P<ruta>[^"\'?#<>\s]+)(?:\?(?P<q>[^"\'#<>\s]*))?', archivo, texto)
    texto = re.sub(r'\$WIKI_REFERENCE\$/pages/([^"\'?#<>\s]+)', lambda m: f'/courses/{c.curso}/pages/{urls[m[1]]}', texto)
    texto = re.sub(r'\$CANVAS_OBJECT_REFERENCE\$/assignments/([a-z0-9]+)', lambda m: f'/courses/{c.curso}/assignments/{tareas_id[m[1]]}', texto)
    texto = re.sub(r'\$CANVAS_OBJECT_REFERENCE\$/quizzes/([a-z0-9]+)',
                   lambda m: f'/courses/{c.curso}/quizzes/{quizzes_id[m[1]]}' if m[1] in quizzes_id else f'/courses/{c.curso}/quizzes', texto)
    texto = texto.replace('$CANVAS_COURSE_REFERENCE$', f'/courses/{c.curso}')
    texto = re.sub(r'\s+data-api-(?:endpoint|returntype)="[^"]*"', '', texto)   # apuntaban al curso de la plantilla
    texto = re.sub(r'https?://[^"\'\s]*/courses/(?!' + str(c.curso) + r'\b)\d+/', f'/courses/{c.curso}/', texto)
    if SIN_RESOLVER.search(texto):
        raise RuntimeError('Quedó una referencia del paquete sin resolver: ' + SIN_RESOLVER.search(texto)[0])
    return texto


# ── Plan ───────────────────────────────────────────────────────────────────────
def base(titulo):
    return re.split(r'\s+·\s+', titulo or '')[0].strip().casefold()


def calcular(c, ruta_paquete):
    z, paginas, tareas, modulos, archivos, adjuntos, quizzes = leer_paquete(ruta_paquete)
    mapa = json.loads(MAPA.read_text(encoding='utf-8')) if MAPA.exists() else {}
    for k in ('archivos', 'paginas', 'tareas', 'modulos'):
        mapa.setdefault(k, {})
    carpetas = {f['id']: f['full_name'] for f in c.todos('/folders')}
    cfiles = c.todos('/files')
    indice = {(carpetas.get(f['folder_id'], '').removeprefix('course files').lstrip('/'), f['display_name'], f['size']): f['id'] for f in cfiles}
    ids_archivos = {f['id'] for f in cfiles}
    cpaginas = {p['url']: p for p in c.todos('/pages')}
    por_titulo = {}
    for p in cpaginas.values():
        por_titulo.setdefault(p['title'].casefold(), p['url'])
    ctareas = c.todos('/assignments')
    cquizzes = {q['title']: q['id'] for q in c.todos('/quizzes')}
    portada = next((p['url'] for p in cpaginas.values() if p.get('front_page')), None)

    plan_archivos = []
    for rel, miembro in sorted(archivos.items()):
        if mapa['archivos'].get(rel) in ids_archivos:
            continue
        carpeta, nombre = rel.rsplit('/', 1) if '/' in rel else ('', rel)
        fid = indice.get((carpeta, nombre, z.getinfo(miembro).file_size))
        if fid:
            mapa['archivos'][rel] = fid
        else:
            plan_archivos.append((rel, carpeta, nombre))

    en_modulos = {it['ref'] for m in modulos for it in m['items'] if it['tipo'] == 'WikiPage'}
    enlazadas = set(re.findall(r'\$WIKI_REFERENCE\$/pages/([^"\'?#<>\s]+)', ' '.join(p['cuerpo'] for p in list(paginas.values()) + list(tareas.values()))))
    usar, retirar, actualizar, crear, inicio = [], [], {}, [], None
    for s, p in paginas.items():
        if es_inicio(p):
            inicio = s
            continue
        usada = p['identificador'] in en_modulos or p['identificador'] in enlazadas or s in enlazadas
        if not p['publicada'] and not usada:
            retirar.append(s)
            continue
        usar.append(s)
        destino = mapa['paginas'].get(s) if mapa['paginas'].get(s) in cpaginas else None
        destino = destino or (s if s in cpaginas else None) or por_titulo.get(p['titulo'].casefold())
        if destino:
            actualizar[s] = destino
        else:
            crear.append(s)
    retirar_curso = sorted({mapa['paginas'].get(s, s) for s in retirar} & {u for u, p in cpaginas.items() if p.get('published')})

    existentes_t = {}
    for t in ctareas:
        existentes_t.setdefault(base(t['name']), t)
    tareas_plan = []
    for ident, t in tareas.items():
        previa = mapa['tareas'].get(ident)
        if previa and any(x['id'] == previa for x in ctareas):
            tareas_plan.append((ident, 'actualizar', previa))
        elif base(t['titulo']) in existentes_t:
            tareas_plan.append((ident, 'actualizar', existentes_t[base(t['titulo'])]['id']))
        else:
            tareas_plan.append((ident, 'crear', None))
    quizzes_id = {i: cquizzes[t] for i, t in quizzes.items() if t in cquizzes}
    faltan_quizzes = sorted({t for i, t in quizzes.items() if i not in quizzes_id})

    textos = [(f'página «{paginas[s]["titulo"]}»', paginas[s]['cuerpo']) for s in usar if paginas[s]['publicada']]
    textos += [(f'tarea «{t["titulo"]}»', t['cuerpo']) for t in tareas.values()]
    if inicio:
        bloque = AULA_INICIO.search(paginas[inicio]['cuerpo'])
        textos.append(('Inicio (aula)', bloque[0] if bloque else ''))
    pendientes = sorted({f'{d}: {m[0]}' for d, t in textos for m in [PENDIENTES.search(t)] if m})

    plan = {'curso': f'{c.dominio}/courses/{c.curso}', 'paquete': ruta_paquete.name,
            'archivos_a_subir': [r for r, _, _ in plan_archivos], 'archivos_reutilizados': len(archivos) - len(plan_archivos),
            'paginas_a_actualizar': {s: actualizar[s] for s in sorted(actualizar)}, 'paginas_a_crear': crear,
            'paginas_a_despublicar': retirar_curso,
            'inicio': ('anteponer el aula en «' + portada + '»') if inicio and portada and AULA_INICIO.search(paginas[inicio]['cuerpo']) else 'sin cambios',
            'tareas': [{'titulo': tareas[i]['titulo'], 'accion': a} for i, a, _ in tareas_plan],
            'modulos': [m['titulo'] for m in modulos], 'cuestionarios_no_encontrados': faltan_quizzes,
            'marcas_pendientes_visibles': pendientes}
    datos = dict(z=z, paginas=paginas, tareas=tareas, modulos=modulos, archivos=archivos, adjuntos=adjuntos, mapa=mapa,
                 plan_archivos=plan_archivos, usar=usar, actualizar=actualizar, crear=crear, retirar_curso=retirar_curso,
                 tareas_plan=tareas_plan, quizzes_id=quizzes_id, inicio=inicio, portada=portada, cpaginas=cpaginas,
                 ctareas=ctareas, cfiles=cfiles)
    return plan, datos


def guardar_mapa(mapa):
    DIR.mkdir(exist_ok=True)
    MAPA.write_text(json.dumps(mapa, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def respaldar(c, d):
    PRIVADO.mkdir(parents=True, exist_ok=True)
    os.chmod(PRIVADO, 0o700)
    marca = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    datos = {'curso': c.curso, 'fecha_utc': marca,
             'paginas': {u: c.get(f'/pages/{u}') for u in d['cpaginas']}, 'tareas': d['ctareas'],
             'modulos': c.todos('/modules', {'include[]': 'items'}),
             'archivos': [{k: f.get(k) for k in ('id', 'display_name', 'size', 'folder_id')} for f in d['cfiles']]}
    f = PRIVADO / f'respaldo-{marca}.json'
    f.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding='utf-8')
    os.chmod(f, 0o600)
    return f


def bloque_inicio(c, d, archivos_id, urls):
    m = AULA_INICIO.search(d['paginas'][d['inicio']]['cuerpo']) if d['inicio'] else None
    return reescribir(c, m[0], archivos_id, urls, {}, {}) if m else None


def con_aula(cuerpo_actual, bloque):
    sin = re.sub(r'^\s*(<!--aula-inicio-->)?<div id="aula-interactiva-inicio".*?</iframe>.*?</p>\s*</div>(<!--/aula-inicio-->)?\s*', '',
                 cuerpo_actual or '', count=1, flags=re.S)
    return bloque + '\n' + sin


def aplicar(c, d):
    mapa, paginas, tareas = d['mapa'], d['paginas'], d['tareas']
    copia = respaldar(c, d)
    print('Respaldo del curso:', copia.relative_to(ROOT))
    for rel, carpeta, nombre in d['plan_archivos']:
        mapa['archivos'][rel] = c.subir(d['z'].read(d['archivos'][rel]), nombre, carpeta)['id']
        guardar_mapa(mapa)
    archivos_id = dict(mapa['archivos'])

    # Páginas, fase A: título (Canvas puede asignar una URL nueva al cambiarlo) y creación sin publicar
    for s, destino in d['actualizar'].items():
        r, _ = c.pedir('PUT', f'/pages/{destino}', {'wiki_page': {'title': paginas[s]['titulo']}})
        mapa['paginas'][s] = r['url']; guardar_mapa(mapa)
    for s in d['crear']:
        r, _ = c.pedir('POST', '/pages', {'wiki_page': {'title': paginas[s]['titulo'], 'body': '', 'published': False}})
        mapa['paginas'][s] = r['url']; guardar_mapa(mapa)
    urls = {}
    for s, p in paginas.items():
        destino = mapa['paginas'].get(s, d['portada'] if s == d['inicio'] else s)
        urls[s] = destino
        if p['identificador']:
            urls[p['identificador']] = destino

    # Tareas, fase A: las nuevas se crean sin publicar
    tareas_id = {}
    for ident, accion, cid in d['tareas_plan']:
        t = tareas[ident]
        if accion == 'crear':
            r, _ = c.pedir('POST', '/assignments', {'assignment': {
                'name': t['titulo'], 'published': False, 'submission_types': (t['entrega'] or 'online_upload').split(','),
                'grading_type': t['calificacion'] or 'not_graded', 'points_possible': t['puntos'], 'omit_from_final_grade': t['omitir']}})
            cid = r['id']
        tareas_id[ident] = cid
        mapa['tareas'][ident] = cid; guardar_mapa(mapa)
    publicada_antes = {x['id']: bool(x.get('published')) for x in d['ctareas']}

    # Contenido con los enlaces resueltos
    for ident, _, _ in d['tareas_plan']:
        t = tareas[ident]
        c.pedir('PUT', f'/assignments/{tareas_id[ident]}', {'assignment': {
            'name': t['titulo'], 'description': reescribir(c, t['cuerpo'], archivos_id, urls, tareas_id, d['quizzes_id'])}})
    for s in d['usar']:
        p = paginas[s]
        c.pedir('PUT', f'/pages/{mapa["paginas"][s]}', {'wiki_page': {
            'title': p['titulo'], 'body': reescribir(c, p['cuerpo'], archivos_id, urls, tareas_id, d['quizzes_id']), 'published': p['publicada']}})
    bloque = bloque_inicio(c, d, archivos_id, urls)
    if bloque and d['portada']:
        actual = c.get(f'/pages/{d["portada"]}')
        c.pedir('PUT', f'/pages/{d["portada"]}', {'wiki_page': {'body': con_aula(actual.get('body'), bloque)}})

    # Módulos: se emparejan por mapa, título o «Momento N»; primero se retiran sus elementos, porque publicar un
    # módulo publica lo que contiene
    cmods = c.todos('/modules', {'include[]': 'items'})
    por_nombre = {m['name']: m for m in cmods}
    for pos, m in enumerate(d['modulos'], 1):
        cm = next((x for x in cmods if x['id'] == mapa['modulos'].get(m['titulo'])), None) or por_nombre.get(m['titulo'])
        corto = re.match(r'(Momento \d+)\b', m['titulo'])
        cm = cm or (por_nombre.get(corto[1]) if corto else None)
        if cm is None:
            cm, _ = c.pedir('POST', '/modules', {'module': {'name': m['titulo'], 'position': pos}})
        mapa['modulos'][m['titulo']] = cm['id']; guardar_mapa(mapa)
        for it in c.todos(f'/modules/{cm["id"]}/items'):
            c.pedir('DELETE', f'/modules/{cm["id"]}/items/{it["id"]}')
        c.pedir('PUT', f'/modules/{cm["id"]}', {'module': {'name': m['titulo'], 'position': pos, 'published': m['publicado']}})
        for n, it in enumerate(m['items'], 1):
            item = {'title': it['titulo'], 'position': n, 'indent': it['sangria']}
            if it['tipo'] == 'WikiPage':
                item.update(type='Page', page_url=urls[it['ref']])
            elif it['tipo'] == 'Assignment':
                item.update(type='Assignment', content_id=tareas_id[it['ref']])
            elif it['tipo'] == 'Attachment':
                item.update(type='File', content_id=archivos_id[d['adjuntos'][it['ref']]])
            elif it['tipo'] == 'Quizzes::Quiz' and it['ref'] in d['quizzes_id']:
                item.update(type='Quiz', content_id=d['quizzes_id'][it['ref']])
            else:
                print(f'  aviso: elemento «{it["titulo"]}» ({it["tipo"]}) sin equivalente en el curso; se omite')
                continue
            c.pedir('POST', f'/modules/{cm["id"]}/items', {'module_item': item})

    # Publicación: cada tarea queda como estaba (las nuevas, sin publicar); las páginas, como en el paquete
    for ident, cid in tareas_id.items():
        if c.get(f'/assignments/{cid}').get('published') and not publicada_antes.get(cid, False):
            c.pedir('PUT', f'/assignments/{cid}', {'assignment': {'published': False}})
    for s in d['usar']:
        if bool(c.get(f'/pages/{mapa["paginas"][s]}').get('published')) != paginas[s]['publicada']:
            c.pedir('PUT', f'/pages/{mapa["paginas"][s]}', {'wiki_page': {'published': paginas[s]['publicada']}})
    for u in d['retirar_curso']:
        c.pedir('PUT', f'/pages/{u}', {'wiki_page': {'published': False}})
    guardar_mapa(mapa)
    return copia


# ── Verificación (solo lectura) ────────────────────────────────────────────────
def verificar(c):
    mapa = json.loads(MAPA.read_text(encoding='utf-8')) if MAPA.exists() else {'paginas': {}, 'tareas': {}}
    pags = {p['url']: p for p in c.todos('/pages')}
    archivos = {f['id'] for f in c.todos('/files')}
    tareas = {a['id']: a for a in c.todos('/assignments')}
    quizzes = {q['id'] for q in c.todos('/quizzes')}
    modulos = c.todos('/modules', {'include[]': 'items'})
    problemas, enlaces = [], 0

    def revisar(nombre, texto, publicado):
        nonlocal enlaces
        for rx, que in ((SIN_RESOLVER, 'referencia sin resolver'), (PENDIENTES, 'marca pendiente visible')):
            if m := rx.search(texto or ''):
                problemas.append(f'{nombre}: {que} «{m[0]}»')
        for tipo, ref in re.findall(rf'/courses/{c.curso}/(pages|files|assignments|quizzes)/([^"\'?#/<>\s]+)', texto or ''):
            enlaces += 1
            if tipo == 'pages' and ref not in pags:
                problemas.append(f'{nombre}: enlace a página inexistente {ref}')
            elif tipo == 'pages' and publicado and not pags[ref]['published']:
                problemas.append(f'{nombre}: enlaza la página sin publicar {ref}')
            elif tipo == 'files' and ref.isdigit() and int(ref) not in archivos:
                problemas.append(f'{nombre}: archivo inexistente {ref}')
            elif tipo == 'assignments' and ref.isdigit() and int(ref) not in tareas:
                problemas.append(f'{nombre}: tarea inexistente {ref}')
            elif tipo == 'quizzes' and ref.isdigit() and int(ref) not in quizzes:
                problemas.append(f'{nombre}: cuestionario inexistente {ref}')

    revisadas = set(mapa['paginas'].values()) | {u for u, p in pags.items() if p.get('front_page')}
    for u in sorted(revisadas & set(pags)):
        p = c.get(f'/pages/{u}')
        revisar('página ' + u, p.get('body'), p['published'])
    for tid in mapa['tareas'].values():
        if tid in tareas:
            revisar('tarea ' + tareas[tid]['name'][:50], tareas[tid].get('description'), tareas[tid].get('published'))
    portada = next((p for p in pags.values() if p.get('front_page')), None)
    aula_en_inicio = bool(portada and 'aula-interactiva-inicio' in (c.get(f'/pages/{portada["url"]}').get('body') or ''))
    return {'fecha_utc': datetime.now(timezone.utc).isoformat(), 'operaciones': 'solo lectura',
            'modulos': [{'nombre': m['name'], 'publicado': m['published'], 'elementos': len(m.get('items') or [])} for m in modulos],
            'tareas': [{'nombre': a['name'][:70], 'publicada': a['published'], 'puntos': a['points_possible']} for a in tareas.values()],
            'aula_en_inicio': aula_en_inicio, 'enlaces_revisados': enlaces, 'problemas': problemas,
            'resultado': 'sin_problemas' if not problemas else 'con_problemas'}


# ── Órdenes ────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='orden', required=True)
    sub.add_parser('token', help='guardar el token del docente (entrada oculta)')
    s = sub.add_parser('configurar', help='curso de destino')
    s.add_argument('--curso', required=True, help='URL del curso: https://<institución>.instructure.com/courses/<número>')
    sub.add_parser('comprobar', help='acceso, permisos e inventario (solo lectura)')
    for n in ('plan', 'aplicar', 'inicio'):
        s = sub.add_parser(n)
        s.add_argument('--paquete', type=Path)
        if n == 'aplicar':
            s.add_argument('--permitir-pendientes', action='store_true', help='aplicar aunque queden marcas pendientes visibles')
        if n == 'inicio':
            s.add_argument('--aplicar', action='store_true')
    sub.add_parser('verificar', help='enlaces, marcas y publicación (solo lectura)')
    a = ap.parse_args()

    if a.orden == 'token':
        t = getpass.getpass('Pega tu token de Canvas (no se mostrará): ').strip()
        if not re.fullmatch(r'[\w~.\-]{20,}', t):
            sys.exit('Eso no parece un token de Canvas. No se guardó nada.')
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(TOKEN_FILE.parent, 0o700)
        TOKEN_FILE.write_text(t + '\n', encoding='utf-8')
        os.chmod(TOKEN_FILE, 0o600)
        print(f'Guardado en {TOKEN_FILE} (solo tu usuario puede leerlo). Revócalo en Canvas cuando ya no se use.')
        return 0
    if a.orden == 'configurar':
        u = urllib.parse.urlparse(a.curso)
        m = re.search(r'/courses/(\d+)', u.path)
        local = u.hostname in ('127.0.0.1', 'localhost')
        if not m or not u.hostname or (u.scheme != 'https' and not local):
            sys.exit('Indica la URL completa del curso, con https: https://indoamerica.instructure.com/courses/12345')
        DIR.mkdir(exist_ok=True)
        CONFIG.write_text(json.dumps({'dominio': f'{u.scheme}://{u.netloc}', 'curso': int(m[1])}, indent=2) + '\n', encoding='utf-8')
        print(f'Curso de destino: {u.scheme}://{u.netloc}/courses/{m[1]} → {CONFIG.relative_to(ROOT)}')
        return 0

    c = Canvas(cfg())
    if a.orden == 'comprobar':
        curso = c.get('')
        perm = c.get('/permissions') or {}
        inscritos = {}
        for e in c.todos('/enrollments', {'state[]': ['active', 'invited']}):
            inscritos[e.get('type')] = inscritos.get(e.get('type'), 0) + 1          # solo conteos
        inv = {'fecha_utc': datetime.now(timezone.utc).isoformat(), 'operaciones': 'solo lectura',
               'curso': {k: curso.get(k) for k in ('id', 'name', 'course_code', 'workflow_state', 'default_view')},
               'permisos': {k: v for k, v in perm.items() if re.search(r'manage|create|delete|update', k)},
               'inscripciones_por_tipo': inscritos,
               'paginas': [{'titulo': p['title'], 'url': p['url'], 'publicada': p.get('published'), 'portada': p.get('front_page')} for p in c.todos('/pages')],
               'tareas': [{'titulo': t['name'], 'publicada': t.get('published'), 'puntos': t.get('points_possible'),
                           'con_entregas': t.get('has_submitted_submissions')} for t in c.todos('/assignments')],
               'modulos': [{'nombre': m['name'], 'publicado': m.get('published')} for m in c.todos('/modules')],
               'archivos': len(c.todos('/files'))}
        DIR.mkdir(exist_ok=True)
        (DIR / 'inventario.json').write_text(json.dumps(inv, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: inv[k] for k in ('curso', 'permisos', 'inscripciones_por_tipo')}, ensure_ascii=False, indent=2))
        print(f'{len(inv["paginas"])} páginas, {len(inv["tareas"])} tareas, {len(inv["modulos"])} módulos, {inv["archivos"]} archivos → canvas/api/inventario.json')
        return 0
    if a.orden == 'verificar':
        r = verificar(c)
        DIR.mkdir(exist_ok=True)
        (DIR / 'verificacion.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: r[k] for k in ('aula_en_inicio', 'enlaces_revisados', 'resultado')}, ensure_ascii=False))
        for p in r['problemas'][:40]:
            print('  -', p)
        return 0 if not r['problemas'] else 1

    plan, d = calcular(c, a.paquete or paquete_por_omision())
    if a.orden == 'inicio':
        print(json.dumps({'curso': plan['curso'], 'inicio': plan['inicio']}, ensure_ascii=False))
        if not a.aplicar:
            print('Vista previa: no se escribió nada. Añade --aplicar.')
            return 0
        try:
            bloque = bloque_inicio(c, d, d['mapa']['archivos'], {**{s: d['mapa']['paginas'].get(s, s) for s in d['paginas']},
                                                                 **{p['identificador']: d['mapa']['paginas'].get(s, s) for s, p in d['paginas'].items() if p['identificador']}})
        except KeyError:
            sys.exit('El aula todavía no está en los archivos del curso: ejecuta primero «aplicar» (sube el aula y lo demás).')
        if not bloque or not d['portada']:
            sys.exit('El paquete no trae el aula para Inicio o el curso no tiene página de inicio.')
        respaldar(c, d)
        actual = c.get(f'/pages/{d["portada"]}')
        c.pedir('PUT', f'/pages/{d["portada"]}', {'wiki_page': {'body': con_aula(actual.get('body'), bloque)}})
        print('Aula incrustada al comienzo de Inicio.')
        return 0
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    (DIR).mkdir(exist_ok=True)
    (DIR / 'plan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if a.orden == 'plan':
        print('\nVista previa: no se escribió nada en Canvas. Para aplicar: python3 canvas/canvas_api.py aplicar')
        return 0
    if plan['marcas_pendientes_visibles'] and not a.permitir_pendientes:
        sys.exit('Hay marcas pendientes que verían los estudiantes (arriba). Complétalas en canvas/silabo.json o el aula, '
                 'regenera el paquete y repite; o usa --permitir-pendientes con el acuerdo del docente.')
    aplicar(c, d)
    r = verificar(c)
    (DIR / 'verificacion.json').write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\nAplicado. Verificación: {r["resultado"]} ({r["enlaces_revisados"]} enlaces). Mapa: canvas/api/mapa.json')
    for p in r['problemas'][:40]:
        print('  -', p)
    return 0 if not r['problemas'] else 1


if __name__ == '__main__':
    sys.exit(main())
