"""Servidor Canvas ficticio en memoria para probar canvas/canvas_api.py sin red ni cuentas.

Reproduce lo que importa del Canvas real: URL de página derivada del título (cambia al renombrar), carga de archivos
en tres pasos, módulos cuyo publicado publica también sus elementos, y paginación omitida (todo en una página).
"""
import html
import json
import re
import threading
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse

NS = {'c': 'http://canvas.instructure.com/xsd/cccv1p0'}
TOKEN = 'token-ficticio-de-pruebas-0123456789'


def slug(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


class Curso:
    def __init__(self, cid=1):
        self.id, self.n = cid, 1000
        self.pages, self.alias, self.assignments, self.modules, self.quizzes = {}, {}, {}, {}, {}
        self.files, self.folders, self.uploads, self.log = {}, {1: 'course files'}, {}, []

    def nid(self):
        self.n += 1
        return self.n

    def page(self, title, body='', published=True, front=False, url=None):
        u = url or slug(title)
        while u in self.pages:
            u += '-2'
        self.pages[u] = {'url': u, 'title': title, 'body': body, 'published': published, 'front_page': front, 'page_id': self.nid()}
        return self.pages[u]

    def resolve(self, u):
        u = unquote(u)
        return self.pages.get(u) or self.pages.get(self.alias.get(u, ''))

    def sembrar_desde_plantilla(self, imscc):
        """Curso con la plantilla institucional ya cargada: páginas, tareas, módulos y cuestionarios del paquete base."""
        z = zipfile.ZipFile(imscc)
        por_ident, cuerpos = {}, {}
        for n in z.namelist():
            if n.startswith('wiki_content/') and n.endswith('.html'):
                t = z.read(n).decode()
                title = html.unescape(re.search(r'<title>(.*?)</title>', t, re.S)[1]).strip()
                ident = (re.search(r'name="identifier" content="([^"]+)"', t) or [None, None])[1]
                p = self.page(title, '', 'content="active"' in t, front=title.lower() == 'inicio', url=n[13:-5])
                por_ident[ident] = ('Page', p['url'])
                cuerpos[p['url']] = re.search(r'<body[^>]*>(.*)</body>', t, re.S)[1]
        for u, b in cuerpos.items():          # como quedaría tras importar la plantilla: enlaces ya resueltos
            b = re.sub(r'\$WIKI_REFERENCE\$/pages/(\w+)', lambda m: f'/courses/{self.id}/pages/' + por_ident.get(m[1], ('', m[1]))[1], b)
            b = b.replace('$IMS-CC-FILEBASE$', f'/courses/{self.id}/file_contents/course%20files')
            b = re.sub(r'\s+data-api-(?:endpoint|returntype)="[^"]*"', '', b)   # en el curso real apuntan a sus propios IDs
            self.pages[u]['body'] = re.sub(r'\$CANVAS_OBJECT_REFERENCE\$/(\w+)/\w+', rf'/courses/{self.id}/\1', b)
        for n in z.namelist():
            if n.endswith('assignment_settings.xml'):
                s = ET.fromstring(z.read(n))
                a = {'id': self.nid(), 'name': s.find('c:title', NS).text, 'description': '', 'published': False,
                     'points_possible': float((s.find('c:points_possible', NS).text if s.find('c:points_possible', NS) is not None else 0) or 0)}
                self.assignments[a['id']] = a
                por_ident[s.get('identifier')] = ('Assignment', a['id'])
            if n.startswith('non_cc_assessments/') and n.endswith('.xml.qti'):
                m = re.search(r'<assessment[^>]*title="([^"]*)"', z.read(n).decode('utf-8', 'replace'))
                q = {'id': self.nid(), 'title': html.unescape(m[1]) if m else 'Q'}
                self.quizzes[q['id']] = q
        for pos, m in enumerate(ET.fromstring(z.read('course_settings/module_meta.xml')).findall('c:module', NS), 1):
            mod = {'id': self.nid(), 'name': m.find('c:title', NS).text, 'position': pos, 'published': True, 'items': []}
            for it in m.findall('.//c:item', NS):
                ref = it.find('c:identifierref', NS)
                if ref is not None and ref.text in por_ident and por_ident[ref.text][0] == 'Page':
                    mod['items'].append({'id': self.nid(), 'type': 'Page', 'page_url': por_ident[ref.text][1], 'title': it.find('c:title', NS).text})
            self.modules[mod['id']] = mod


class Handler(BaseHTTPRequestHandler):
    curso: Curso = None

    def log_message(self, *a):
        pass

    def send(self, code, data=None):
        b = json.dumps(data).encode() if data is not None else b''
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        raw = self.rfile.read(n) if n else b''
        return raw

    def route(self, metodo):
        c = self.curso
        u = urlparse(self.path)
        if u.path.startswith('/upload/'):
            info = c.uploads.pop(u.path.split('/')[-1])
            self.body()
            f = {'id': c.nid(), 'display_name': info['name'], 'size': info['size'], 'folder_id': info['folder_id']}
            c.files[f['id']] = f
            c.log.append(('UPLOAD', info['name']))
            return self.send(201, f)
        if self.headers.get('Authorization') != 'Bearer ' + TOKEN:
            return self.send(401, {'errors': [{'message': 'Invalid access token.'}]})
        base = f'/api/v1/courses/{c.id}'
        if not u.path.startswith(base):
            return self.send(404, {})
        r = u.path[len(base):]
        datos = json.loads(self.body() or b'null') if metodo in ('POST', 'PUT') else None
        if metodo != 'GET':
            c.log.append((metodo, r))
        if r == '' and metodo == 'GET':
            return self.send(200, {'id': c.id, 'name': 'Curso ficticio', 'course_code': 'CF', 'workflow_state': 'available', 'default_view': 'wiki'})
        if r == '/permissions':
            return self.send(200, {'manage_wiki_create': True, 'manage_wiki_delete': False, 'manage_assignments': True})
        if r == '/enrollments':
            return self.send(200, [{'type': 'StudentEnrollment'}] * 3 + [{'type': 'TeacherEnrollment'}])
        if r == '/folders':
            return self.send(200, [{'id': k, 'full_name': v} for k, v in c.folders.items()])
        if r == '/files' and metodo == 'GET':
            return self.send(200, list(c.files.values()))
        if r == '/files' and metodo == 'POST':
            ruta = 'course files' + ('/' + datos['parent_folder_path'] if datos['parent_folder_path'] else '')
            fid = next((k for k, v in c.folders.items() if v == ruta), None) or c.nid()
            c.folders[fid] = ruta
            tok = str(c.nid())
            c.uploads[tok] = {'name': datos['name'], 'size': datos['size'], 'folder_id': fid}
            host = self.headers.get('Host')
            return self.send(200, {'upload_url': f'http://{host}/upload/{tok}', 'upload_params': {'filename': datos['name']}})
        if r == '/pages' and metodo == 'GET':
            return self.send(200, [{k: v for k, v in p.items() if k != 'body'} for p in c.pages.values()])
        if r == '/pages' and metodo == 'POST':
            w = datos['wiki_page']
            return self.send(200, c.page(w['title'], w.get('body', ''), w.get('published', True)))
        if m := re.fullmatch(r'/pages/([^/]+)', r):
            p = c.resolve(m[1])
            if not p:
                return self.send(404, {})
            if metodo == 'PUT':
                w = datos['wiki_page']
                if 'title' in w and w['title'] != p['title']:
                    nuevo = slug(w['title'])
                    if nuevo != p['url'] and nuevo not in c.pages:
                        c.alias[p['url']] = nuevo
                        c.pages[nuevo] = c.pages.pop(p['url'])
                        p['url'] = nuevo
                    p['title'] = w['title']
                for k in ('body', 'published'):
                    if k in w:
                        p[k] = w[k]
            return self.send(200, p)
        if r == '/assignments' and metodo == 'GET':
            return self.send(200, list(c.assignments.values()))
        if r == '/assignments' and metodo == 'POST':
            a = {'id': c.nid(), 'description': '', **datos['assignment']}
            c.assignments[a['id']] = a
            return self.send(200, a)
        if m := re.fullmatch(r'/assignments/(\d+)', r):
            a = c.assignments[int(m[1])]
            if metodo == 'PUT':
                a.update(datos['assignment'])
            return self.send(200, a)
        if r == '/quizzes':
            return self.send(200, list(c.quizzes.values()))
        if r == '/modules' and metodo == 'GET':
            inc = 'items' in parse_qs(u.query).get('include[]', [])
            return self.send(200, [{k: v for k, v in m.items() if inc or k != 'items'} for m in sorted(c.modules.values(), key=lambda x: x['position'])])
        if r == '/modules' and metodo == 'POST':
            m = {'id': c.nid(), 'published': False, 'items': [], **datos['module']}
            c.modules[m['id']] = m
            return self.send(200, m)
        if m := re.fullmatch(r'/modules/(\d+)', r):
            mod = c.modules[int(m[1])]
            mod.update(datos['module'])
            if mod.get('published'):          # como en Canvas: publicar el módulo publica sus elementos
                for it in mod['items']:
                    if it['type'] == 'Assignment':
                        c.assignments[it['content_id']]['published'] = True
                    elif it['type'] == 'Page':
                        c.resolve(it['page_url'])['published'] = True
            return self.send(200, mod)
        if m := re.fullmatch(r'/modules/(\d+)/items', r):
            mod = c.modules[int(m[1])]
            if metodo == 'GET':
                return self.send(200, mod['items'])
            it = {'id': c.nid(), **datos['module_item']}
            if it['type'] == 'Page':
                p = c.resolve(it['page_url'])
                if not p or p['url'] != it['page_url']:
                    return self.send(400, {'errors': {'page_url': 'invalid page_url parameter'}})
            mod['items'].append(it)
            return self.send(200, it)
        if m := re.fullmatch(r'/modules/(\d+)/items/(\d+)', r):
            mod = c.modules[int(m[1])]
            mod['items'] = [x for x in mod['items'] if x['id'] != int(m[2])]
            return self.send(200, {})
        return self.send(404, {'ruta': r})

    def do_GET(self):
        self.route('GET')

    def do_POST(self):
        self.route('POST')

    def do_PUT(self):
        self.route('PUT')

    def do_DELETE(self):
        self.route('DELETE')


def iniciar(curso):
    h = type('H', (Handler,), {'curso': curso})
    srv = ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}/courses/{curso.id}'
