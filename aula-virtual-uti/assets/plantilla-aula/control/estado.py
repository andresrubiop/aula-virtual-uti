#!/usr/bin/env python3
"""Registra evidencia en ESTADO.md y comprueba su vigencia; no ejecuta pruebas ni aprueba fases.

python control/estado.py registrar ID --fase 2 --entregable canvas/silabo.json \
    --fuente fuentes/silabo/vigente.pdf --prueba control/validacion.txt --resultado pasado
python control/estado.py verificar
python control/estado.py impacto

En aulas anteriores: python <skill>/assets/plantilla-aula/control/estado.py --aula <aula> verificar
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile

INICIO = '<!-- evidencias-aula:inicio -->'
FIN = '<!-- evidencias-aula:fin -->'
RESERVADOS = {'privado', '.git', '.env', '.venv', '.claude', '.agents', 'node_modules', '__pycache__'}
RESULTADOS = ('pasado', 'fallido', 'no_ejecutado')
TIPOS = ('local', 'docente', 'remota')
REQUERIDOS = {0: ('hub/src/course.json', 'hub/dist/index.html'), 1: ('fuentes/INVENTARIO.md',),
              2: ('canvas/silabo.json',), 3: ('PLANIFICACION.md',)}


def ruta(root, value, existe=True):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
        raise ValueError('Ruta vacía o con caracteres de control.')
    value = value.replace('\\', '/')
    rel = PurePosixPath(value)
    if rel.is_absolute() or '..' in rel.parts or ':' in value or not rel.parts:
        raise ValueError('Usa rutas relativas dentro del aula, sin .. ni unidad de disco.')
    if any(p.casefold() in RESERVADOS or p.casefold().startswith('.env.') for p in rel.parts):
        raise ValueError('No se leen archivos privados, credenciales ni carpetas reservadas.')
    target = root
    for part in rel.parts:
        target = target / part
        if target.is_symlink() or getattr(target, 'is_junction', lambda: False)():
            raise ValueError('No se siguen enlaces simbólicos ni uniones de directorios.')
    if not target.resolve().is_relative_to(root):
        raise ValueError('La ruta sale del aula.')
    if existe and (not target.is_file() or target.stat().st_size == 0):
        raise ValueError(f'Archivo ausente o vacío: {rel.as_posix()}')
    return target


def digest(path):
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('La evidencia debe ser un archivo regular.')
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
        raise ValueError('El archivo cambió durante la lectura; repite la comprobación.')
    return h.hexdigest()


def sin_duplicados(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Clave duplicada en el registro: {key}')
        result[key] = value
    return result


def validar_registro(data):
    if not isinstance(data, dict) or set(data) != {'version', 'registros'} or type(data['version']) is not int or data['version'] != 1 or not isinstance(data['registros'], dict):
        raise ValueError('Formato de evidencia incompatible; conserva ESTADO.md y revisa el bloque.')
    for ident, item in data['registros'].items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', ident) or not isinstance(item, dict):
            raise ValueError('ID de evidencia o registro no válido.')
        fields = {'fase', 'fecha', 'resultado', 'tipo', 'entregables', 'fuentes', 'pruebas', 'aprobacion'}
        if set(item) != fields or type(item['fase']) is not int or item['fase'] not in range(10):
            raise ValueError(f'{ident}: estructura o fase no válida.')
        if item['resultado'] not in RESULTADOS or item['tipo'] not in TIPOS:
            raise ValueError(f'{ident}: resultado o tipo no válido.')
        try:
            if datetime.fromisoformat(item['fecha']).tzinfo is None:
                raise ValueError('Falta zona horaria')
        except (TypeError, ValueError):
            raise ValueError(f'{ident}: fecha no válida.') from None
        for field in ('entregables', 'fuentes', 'pruebas', 'aprobacion'):
            values = item[field]
            if not isinstance(values, dict) or any(not isinstance(p, str) or not isinstance(h, str) or not re.fullmatch(r'[a-f0-9]{64}', h) for p, h in values.items()):
                raise ValueError(f'{ident}: rutas o hashes no válidos en {field}.')
        all_paths = [clave_ruta(p) for field in ('entregables', 'fuentes', 'pruebas', 'aprobacion') for p in item[field]]
        if len(all_paths) != len(set(all_paths)):
            raise ValueError(f'{ident}: un mismo archivo no puede cumplir dos papeles de evidencia.')
        if not item['entregables'] or not item['fuentes'] or (item['resultado'] != 'no_ejecutado' and not item['pruebas']):
            raise ValueError(f'{ident}: faltan entregables, fuentes o informe de prueba.')


def leer(root):
    text = ruta(root, 'ESTADO.md').read_bytes().decode('utf-8')
    if not text.count(INICIO) and not text.count(FIN):
        return text, {'version': 1, 'registros': {}}
    if text.count(INICIO) != 1 or text.count(FIN) != 1 or text.index(FIN) < text.index(INICIO):
        raise ValueError('Marcadores de evidencia incompletos o repetidos; no se modifica el estado.')
    body = text.split(INICIO, 1)[1].split(FIN, 1)[0].strip()
    match = re.fullmatch(r'```json\s*\r?\n(.*?)\r?\n```', body, re.S)
    if not match:
        raise ValueError('El bloque de evidencia debe contener un único bloque JSON válido.')
    data = json.loads(match[1], object_pairs_hook=sin_duplicados)
    validar_registro(data)
    return text, data


def hashes(root, paths):
    result = {}
    for value in paths:
        p = ruta(root, value)
        rel = p.relative_to(root).as_posix()
        if rel in ('ESTADO.md', 'control/VERIFICACION_ESTADO.md', 'control/IMPACTO.md'):
            raise ValueError('No registres el propio estado ni el informe derivado como evidencia.')
        if rel in result:
            raise ValueError(f'Archivo repetido: {rel}')
        result[rel] = digest(p)
    return result


def escribir(path, text):
    """Reemplazo atómico: nunca deja medio archivo tras una interrupción."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.estado-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        if path.exists():
            os.chmod(temp, stat.S_IMODE(path.stat().st_mode))
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def registrar(root, args):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', args.id):
        raise ValueError('El ID admite letras, números, guion y guion bajo (máximo 80).')
    lock = ruta(root, '.estado.lock', existe=False)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Hay un registro en curso o un bloqueo de una sesión interrumpida. Revisa antes de retirar .estado.lock.') from None
    try:
        os.close(fd)
        text, data = leer(root)
        if args.id in data['registros'] and not args.reemplazar:
            raise ValueError('El ID ya existe. Usa --reemplazar solo después de repetir la revisión necesaria.')
        item = {'fase': args.fase, 'fecha': datetime.now(timezone.utc).isoformat(),
                'resultado': args.resultado, 'tipo': args.tipo,
                'entregables': hashes(root, args.entregable), 'fuentes': hashes(root, args.fuente),
                'pruebas': hashes(root, args.prueba or []), 'aprobacion': hashes(root, args.aprobacion or [])}
        groups = list(item[k] for k in ('entregables', 'fuentes', 'pruebas', 'aprobacion'))
        if any(set(a) & set(b) for i, a in enumerate(groups) for b in groups[i+1:]):
            raise ValueError('Entregables, fuentes, pruebas y aprobación deben ser archivos distintos.')
        data['registros'][args.id] = item
        validar_registro(data)
        detalles, _ = analizar(root, data['registros'])
        current = next(d for d in detalles if d['id'] == args.id)
        if args.resultado == 'pasado' and current['bloqueado_por']:
            raise ValueError('No se registra como pasado mientras sus fuentes dependan de evidencia pendiente: '+', '.join(current['bloqueado_por']))
        block = INICIO + '\n```json\n' + json.dumps(data, ensure_ascii=False, indent=2) + '\n```\n' + FIN
        if INICIO in text:
            updated = text[:text.index(INICIO)] + block + text[text.index(FIN)+len(FIN):]
        else:
            updated = text + ('\n' if text.endswith('\n') else '\n\n') + '## Evidencias verificables\n\n' + block + '\n'
        if ruta(root, 'ESTADO.md').read_bytes().decode('utf-8') != text:
            raise ValueError('ESTADO.md cambió durante el registro; vuelve a leerlo antes de continuar.')
        escribir(ruta(root, 'ESTADO.md'), updated)
        return {'registrado': args.id, 'fase': args.fase, 'aviso': 'Huellas guardadas; las fases y decisiones no se modificaron.'}
    finally:
        lock.unlink(missing_ok=True)


def fases(text):
    # Solo la tabla de fases: ignora ejemplos de comandos, otros cuadros y el JSON.
    visible = re.sub(re.escape(INICIO) + r'.*?' + re.escape(FIN), '', text, flags=re.S)
    visible = re.sub(r'^```.*?^```[^\n]*', '', visible, flags=re.M | re.S)
    sections = re.split(r'^##\s+', visible, flags=re.M)
    selected = [s for s in sections[1:] if re.match(r'(?:\d+\.\s*)?Fases\s*\r?\n', s, re.I)]
    if len(selected) != 1:
        raise ValueError('Debe existir una sección «## Fases» o «## 1. Fases» con su tabla; adapta el formato sin inventar avances.')
    rows = {}
    for line in selected[0].splitlines()[1:]:
        if not line.lstrip().startswith('|'):
            continue
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if not cells or cells[0].casefold() == 'fase' or re.fullmatch(r'[-: ]+', cells[0]):
            continue
        m = re.match(r'^(\d+)\s*(?:[.·-]|$)', cells[0])
        if not m or len(cells) < 3 or int(m[1]) not in range(10) or int(m[1]) in rows:
            raise ValueError('Fila de fase no válida o duplicada: conserva números 0–9 y columnas Fase, Estado, Notas.')
        n = int(m[1]); status = cells[1]
        if not status.startswith(('✅', '🟡', '⬜', '⛔', '⏭')):
            raise ValueError(f'Fase {n}: estado no reconocido; usa la leyenda del molde.')
        if status.startswith('⏭') and (n != 7 or not ''.join(cells[2:]).strip()):
            raise ValueError('Solo videos (fase 7) puede omitirse; escribe el motivo en Notas.')
        rows[n] = status
    if set(rows) != set(range(10)):
        raise ValueError('La tabla debe conservar las diez fases 0–9, aunque sigan pendientes.')
    return rows, visible


def clave_ruta(value):
    """Una misma ruta con ./ o separadores Windows forma la misma dependencia."""
    return os.path.normcase(PurePosixPath(value.replace('\\', '/')).as_posix())


def dependencias(registros):
    productores = {}
    for ident, item in registros.items():
        for name in item['entregables']:
            productores.setdefault(clave_ruta(name), set()).add(ident)
    deps = {ident: {} for ident in registros}
    for ident, item in registros.items():
        for source in item['fuentes']:
            for origin in sorted(productores.get(clave_ruta(source), ())):
                if origin == ident:
                    raise ValueError(f'{ident}: un entregable no puede ser fuente de sí mismo.')
                deps[ident].setdefault(origin, []).append(source)
    # Orden determinista; un ciclo impide proponer una actualización segura.
    import heapq
    followers = {ident: [] for ident in registros}
    counts = {ident: len(origins) for ident, origins in deps.items()}
    for ident, origins in deps.items():
        for origin in origins:
            followers[origin].append(ident)
    ready = [ident for ident, count in counts.items() if count == 0]
    heapq.heapify(ready); order = []
    while ready:
        ident = heapq.heappop(ready); order.append(ident)
        for following in sorted(followers[ident]):
            counts[following] -= 1
            if counts[following] == 0:
                heapq.heappush(ready, following)
    if len(order) != len(registros):
        blocked = ', '.join(sorted(ident for ident, count in counts.items() if count))
        raise ValueError('Dependencias circulares o bloqueadas por un ciclo: '+blocked+'. Revisa las fuentes declaradas o agrupa la producción conjunta en un registro.')
    return deps, order


def analizar(root, registros, cambios=()):
    deps, order = dependencias(registros)
    proposed = {clave_ruta(p) for p in cambios}
    details = {}
    actual = {}
    for ident in order:
        item = registros[ident]
        problems, changed = [], []
        for group in ('entregables', 'fuentes', 'pruebas', 'aprobacion'):
            for name, expected in item[group].items():
                key = clave_ruta(name)
                if key not in actual:
                    try:
                        actual[key] = digest(ruta(root, name))
                    except (ValueError, OSError):
                        actual[key] = None
                kind = 'ausente_o_no_permitido' if actual[key] is None else 'modificado' if actual[key] != expected else None
                if kind:
                    changed.append({'grupo': group, 'ruta': name, 'cambio': kind})
                    problems.append(f'{group}: {name} ({kind}); revisar la evidencia registrada')
                if key in proposed:
                    changed.append({'grupo': group, 'ruta': name, 'cambio': 'declarado'})
                    problems.append(f'Cambio declarado para analizar: {group} {name}')
        if item['resultado'] != 'pasado':
            problems.append('Revisión '+item['resultado']+'; no respalda una entrega vigente')
        if item['fase'] in (3, 4, 9) and not item['aprobacion']:
            problems.append('Falta evidencia de decisión docente para esta fase')
        if item['fase'] == 9 and item['tipo'] != 'remota':
            problems.append('La fase 9 necesita evidencia remota observada; una prueba local no la sustituye')
        direct = list(problems)
        upstream = [origin for origin in sorted(deps[ident]) if not details[origin]['vigente']]
        for origin in upstream:
            problems.append('Depende de '+origin+' pendiente de revisión mediante '+', '.join(sorted(deps[ident][origin])))
        details[ident] = {'id': ident, 'fase': item['fase'], 'vigente': not problems,
                          'problemas': problems, 'problemas_directos': direct, 'cambios': changed,
                          'depende_de': sorted(deps[ident]), 'bloqueado_por': upstream}
    return [details[k] for k in order], deps


def insumos_sin_relacion(root, registros):
    """Solo enumera fuentes públicas locales; no lee contenidos ni inventa su relación."""
    base = ruta(root, 'fuentes', existe=False)
    if not base.exists():
        return []
    linked = {clave_ruta(p) for item in registros.values() for p in item['fuentes']}
    result = []
    for folder, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d.casefold() not in RESERVADOS | {'_texto'}
                         and not (Path(folder)/d).is_symlink() and not getattr(Path(folder)/d, 'is_junction', lambda: False)())
        for name in sorted(files):
            if name.startswith('.') or name in ('LEEME.txt', 'INVENTARIO.md', 'TRAZABILIDAD.md'):
                continue
            rel = (Path(folder)/name).relative_to(root).as_posix()
            try:
                p = ruta(root, rel, existe=False)
                if not p.is_file():
                    continue
            except ValueError:
                continue
            if clave_ruta(rel) not in linked:
                result.append(rel)
    return sorted(result)


def plan_impacto(root, cambios=()):
    text, data = leer(root)
    explicit = [ruta(root, p, existe=False).relative_to(root).as_posix() for p in cambios]
    details, deps = analizar(root, data['registros'], explicit)
    unknown = insumos_sin_relacion(root, data['registros'])
    tracked = {clave_ruta(p) for item in data['registros'].values() for group in ('entregables', 'fuentes', 'pruebas', 'aprobacion') for p in item[group]}
    unknown += [p for p in explicit if clave_ruta(p) not in tracked and p not in unknown]
    affected = []
    for detail in details:
        if detail['vigente']:
            continue
        item = data['registros'][detail['id']]
        edited = [c['ruta'] for c in detail['cambios'] if c['grupo'] == 'entregables' and c['cambio'] == 'modificado']
        actions = []
        if edited:
            actions.append('Conservar las ediciones actuales de '+', '.join(edited)+'; revisarlas antes de regenerar.')
        if detail['bloqueado_por']:
            actions.append('Resolver primero '+', '.join(detail['bloqueado_por'])+' y volver a analizar antes de actualizar esta entrega.')
        if any(c['grupo'] in ('fuentes', 'entregables') for c in detail['cambios']):
            actions.append('Revisar los cambios académicos y actualizar solo los recursos afectados; no sustituir correcciones aprobadas por la plantilla.')
        if not detail['bloqueado_por']:
            actions.append('Ejecutar las comprobaciones pertinentes y registrar de nuevo solo después de revisarlas.')
        if item['aprobacion'] or item['fase'] in (3,4,9):
            actions.append('Comprobar que la decisión docente conserve su alcance; registrar una nueva revisión real cuando corresponda.')
        if item['tipo'] == 'remota' or item['fase'] in (7,9):
            actions.append('Mantener la operación remota pendiente de revisión; este plan no autoriza envío, generación o importación.')
        affected.append({**detail, 'entregables': sorted(item['entregables']),
                         'conservar_ediciones': edited, 'acciones': actions})
    return {'fecha': datetime.now(timezone.utc).isoformat(), 'estado_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'modo': 'incluye_cambios_declarados' if explicit else 'archivos_actuales',
            'cambios_declarados': explicit, 'afectados': affected,
            'orden_actualizacion': [d['id'] for d in affected],
            'sin_impacto_detectado': [d['id'] for d in details if d['vigente']],
            'sin_relacion_declarada': sorted(unknown),
            'avisos': [] if details else ['Sin registros: no hay mapa de entregables que analizar.'],
            'limite': 'Plan basado en fuentes y entregables registrados. No regenera archivos, no aprueba cambios ni realiza operaciones remotas. Las fuentes sin relación requieren revisión; no se puede deducir qué afectan.'}


def informe_impacto(report):
    safe = lambda s: str(s).replace('\r',' ').replace('\n',' ').replace('<','&lt;').replace('>','&gt;')
    lines = ['# Plan de actualización por cambios', '', report['limite'], '',
             '**Fecha:** '+report['fecha'], '', '**SHA256 de ESTADO.md:** '+report['estado_sha256'],
             '', '**Modo:** '+report['modo'], '', '## Orden de revisión y actualización', '']
    for n, item in enumerate(report['afectados'], 1):
        lines += [f'{n}. **{safe(item["id"])}** · fase {item["fase"]}', '',
                  '   Entregables: '+safe(', '.join(item['entregables'])), '',
                  '   Motivos: '+safe('; '.join(item['problemas'])), '',
                  '   Acción: '+safe(' '.join(item['acciones'])), '']
    if not report['afectados']:
        lines += ['No se detectó impacto entre los entregables registrados. Revisa también las fuentes sin relación.', '']
    lines += ['## Sin impacto detectado en el mapa', ''] + ['- '+safe(x) for x in report['sin_impacto_detectado'] or ['Ninguno registrado.']]
    lines += ['', '## Fuentes o cambios sin relación declarada', ''] + ['- '+safe(x) for x in report['sin_relacion_declarada'] or ['Ninguno detectado.']]
    lines += ['', '## Avisos', ''] + ['- '+safe(x) for x in report['avisos'] or ['Vuelve a analizar tras cada actualización; una entrega puede conservarse si las fuentes que consume no cambiaron.']]
    return '\n'.join(lines)+'\n'


def verificar(root):
    text, data = leer(root)
    rows, visible = fases(text)
    errors, warnings, details = [], [], []
    details, _ = analizar(root, data['registros'])
    errors.extend(d['id']+': '+p for d in details for p in d['problemas'])
    for phase, status in rows.items():
        if not status.startswith('✅'):
            continue
        ids = [k for k,v in data['registros'].items() if v['fase'] == phase]
        if not ids:
            errors.append(f'Fase {phase} marcada lista sin evidencia registrada.')
            continue
        outputs = {p for key in ids for p in data['registros'][key]['entregables']}
        for required in REQUERIDOS.get(phase, ()):
            if required not in outputs:
                errors.append(f'Fase {phase}: falta registrar el entregable {required}.')
        if phase == 8 and not any(p.endswith('.imscc') for p in outputs):
            errors.append('Fase 8: falta registrar el paquete .imscc.')
        valid_ids = {d['id'] for d in details if d['vigente'] and d['fase'] == phase}
        if phase in (3,4,9) and not any(data['registros'][k]['aprobacion'] for k in valid_ids):
            errors.append(f'Fase {phase}: falta evidencia vigente de la decisión docente.')
        if phase == 9 and not any(data['registros'][k]['tipo'] == 'remota' for k in valid_ids):
            errors.append('Fase 9: una prueba local no respalda una importación real; registra la revisión remota observada.')
    if not details:
        warnings.append('Sin registros: aún no se puede contrastar la vigencia de pruebas o entregables.')
    def campo(label):
        matches = re.findall(r'^-\s*\*\*'+re.escape(label)+r':\*\*\s*(.*)$', visible, re.M)
        return matches[0].strip() if len(matches) == 1 else ''
    next_action = campo('Próxima acción exacta')
    work = campo('Archivo o carpeta de trabajo')
    phase_text = campo('Fase actual')
    placeholder = next_action.casefold().strip(' .:') in {'pendiente', 'por definir', 'pendiente de definir', 'definir', 'completar', 'tbd', 'n/a', '—', '…'}
    if not next_action or next_action.startswith('[') or placeholder:
        errors.append('Falta una próxima acción concreta en Punto de reanudación.')
    if not work or work.startswith('['):
        errors.append('Falta el archivo o carpeta de trabajo para retomar.')
    if not re.match(r'^[0-9](?:\s|[.·-]|$)', phase_text):
        errors.append('Falta una fase actual reconocible (0–9) en Punto de reanudación.')
    # Se señalan ubicaciones inexistentes sin leer su contenido ni interpretar órdenes.
    locations = re.findall(r'`([^`]+)`', work)
    if work and not locations:
        errors.append('Escribe al menos una ruta entre acentos graves en Archivo o carpeta de trabajo.')
    for name in locations:
        try:
            target = ruta(root, name, existe=False)
            if not target.exists():
                errors.append('Ubicación para retomar ausente: '+name)
        except ValueError:
            errors.append('Ubicación para retomar no permitida: '+name)
    action = 'Resolver primero: '+errors[0] if errors else next_action
    return {'fecha': datetime.now(timezone.utc).isoformat(), 'estado_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'resultado': 'requiere_revision' if errors else 'sin_incidencias', 'errores': errors,
            'avisos': warnings, 'registros': details, 'fase_actual': phase_text,
            'accion_guardada': next_action, 'ubicacion_guardada': work, 'siguiente_accion': action,
            'limite': 'Se comprueban archivos y huellas de evidencias declaradas. No se ejecutan pruebas ni se certifican aprobación docente, calidad académica o acceso remoto.'}


def informe(report):
    safe = lambda s: str(s).replace('\r',' ').replace('\n',' ').replace('<','&lt;').replace('>','&gt;')
    lines = ['# Verificación del estado del aula', '', report['limite'], '',
             '**Fecha:** '+report['fecha'], '', '**SHA256 de ESTADO.md:** '+report['estado_sha256'], '',
             '**Resultado:** '+report['resultado'], '', '**Siguiente acción:** '+safe(report['siguiente_accion']),
             '', '**Acción guardada:** '+safe(report['accion_guardada']), '', '**Ubicación guardada:** '+safe(report['ubicacion_guardada']),
             '', '## Incidencias', '']
    lines += ['- '+safe(x) for x in report['errores'] or ['No se detectaron discrepancias; esto no declara el aula terminada.']]
    lines += ['', '## Avisos', ''] + ['- '+safe(x) for x in report['avisos'] or ['Sin avisos adicionales.']]
    lines += ['', '## Evidencias', ''] + ['- '+safe(x['id'])+': '+('vigente' if x['vigente'] else 'revisar') for x in report['registros']]
    return '\n'.join(lines)+'\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--aula', type=Path, default=Path(__file__).resolve().parents[1])
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('registrar', help='Guardar huellas después de una comprobación real, sin cambiar fases')
    r.add_argument('id'); r.add_argument('--fase', type=int, choices=range(10), required=True)
    r.add_argument('--entregable', action='append', required=True); r.add_argument('--fuente', action='append', required=True)
    r.add_argument('--prueba', action='append'); r.add_argument('--aprobacion', action='append')
    r.add_argument('--resultado', choices=RESULTADOS, required=True); r.add_argument('--tipo', choices=TIPOS, default='local')
    r.add_argument('--reemplazar', action='store_true')
    v = sub.add_parser('verificar', help='Contrastar ESTADO.md y escribir control/VERIFICACION_ESTADO.md')
    v.add_argument('--json', action='store_true')
    i = sub.add_parser('impacto', help='Plan ordenado de actualización según dependencias declaradas')
    i.add_argument('--json', action='store_true')
    i.add_argument('--cambio', action='append', default=[], help='Analizar también un cambio propuesto; no modifica el archivo')
    args = ap.parse_args(argv); root = args.aula.expanduser().resolve()
    try:
        if args.cmd == 'registrar':
            result = registrar(root, args)
            print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
        if args.cmd == 'impacto':
            report = plan_impacto(root, args.cambio)
            escribir(ruta(root, 'control/IMPACTO.md', existe=False), informe_impacto(report))
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else informe_impacto(report))
            return int(bool(report['afectados'] or report['sin_relacion_declarada']))
        report = verificar(root)
        escribir(ruta(root, 'control/VERIFICACION_ESTADO.md', existe=False), informe(report))
        print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else informe(report))
        return int(bool(report['errores']))
    except (ValueError, OSError, UnicodeError) as ex:
        if args.cmd in ('verificar', 'impacto'):
            try:
                output = 'control/VERIFICACION_ESTADO.md' if args.cmd == 'verificar' else 'control/IMPACTO.md'
                escribir(ruta(root, output, existe=False),
                         '# Verificación no completada\n\nEl estado o sus rutas no se pudieron comprobar. No se conserva un resultado anterior como vigente.\n\n' + str(ex).replace('<', '&lt;') + '\n')
            except (ValueError, OSError):
                pass  # La salida tampoco es segura o escribible; el error se comunica por stderr.
        print('No se completó la operación: '+str(ex), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
