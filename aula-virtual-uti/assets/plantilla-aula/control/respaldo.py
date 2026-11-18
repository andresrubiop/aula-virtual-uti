#!/usr/bin/env python3
"""Respaldos locales por hitos y recuperación que nunca toca los documentos originales del docente.

python3 control/respaldo.py crear --tipo antes --motivo "Antes de rehacer la unidad 2"
python3 control/respaldo.py crear --tipo aprobado --unidad U2 --motivo "Unidad 2 aprobada por el docente"
python3 control/respaldo.py listar
python3 control/respaldo.py comparar ultimo-aprobado --ruta hub/src/content/u2
python3 control/respaldo.py restaurar ultimo-aprobado --ruta hub/src/content/u2           # solo muestra el plan
python3 control/respaldo.py restaurar ultimo-aprobado --ruta hub/src/content/u2 --aplicar
python3 control/respaldo.py restaurar --evidencia u2-revision --aplicar                   # vuelve a lo registrado
python3 control/respaldo.py comprobar
python3 control/respaldo.py extraer NOMBRE --destino <carpeta nueva fuera del aula>

Los respaldos quedan en respaldos/ dentro del aula: un manifiesto por hito y cada versión de archivo una sola vez.
Antes de aplicar una restauración se guarda automáticamente un respaldo de seguridad del estado actual.
En aulas anteriores: python3 <skill>/assets/plantilla-aula/control/respaldo.py --aula <aula> ...
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import unicodedata

from estado import DERIVADOS, RESERVADOS, analizar, clave_ruta, escribir, leer, ruta

CARPETA = 'respaldos'
VERSION = 1
TIPOS = {'antes': 'antes de un cambio amplio', 'aprobado': 'resultado aprobado', 'manual': 'a pedido',
         'seguridad': 'automático antes de restaurar'}
# Documentos del docente: se guardan solo sus huellas y nunca se sobrescriben ni se retiran.
ORIGINALES = ('fuentes/', 'canvas/fuentes/', 'canvas/exportado/')
# Generados en fuentes/ por las herramientas: se respaldan como trabajo.
TRABAJO_EN_FUENTES = ('fuentes/INVENTARIO.md', 'fuentes/TRAZABILIDAD.md')
CACHE = ('fuentes/_texto/',)
# Salidas que se regeneran; se respaldan solo si una evidencia de ESTADO.md las cita.
GENERADOS = ('hub/dist/', 'hub/tools/shots/', 'autonomo/', 'canvas/salida/', 'videos/bruto/')
MEDIOS = ('.mp4', '.mov', '.webm', '.mkv', '.m4a', '.mp3', '.wav')
SECRETOS = {'credentials.json', 'cookies.json', 'token.json', 'tokens.json', 'storage_state.json', 'auth.json',
            'client_secret.json', 'id_rsa', 'id_ed25519'}
HEX = re.compile(r'[a-f0-9]{64}')
NOMBRE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,119}')


# ── Recorrido y clasificación ──────────────────────────────────────────────────

def bajo(rel, prefijos):
    r = rel.casefold()
    return any(r == p.rstrip('/').casefold() or r.startswith(p.casefold()) for p in prefijos)


def clase(rel, evidencia):
    """trabajo (se guarda y restaura), original (solo huella), generado (solo si es evidencia) u omitido."""
    if rel in TRABAJO_EN_FUENTES:
        return 'trabajo'
    if bajo(rel, CACHE) or rel in DERIVADOS:
        return 'omitido'
    if bajo(rel, ORIGINALES):
        return 'original'
    if bajo(rel, GENERADOS) or rel.casefold().endswith(MEDIOS):
        return 'generado' if clave_ruta(rel) in evidencia else 'omitido'
    return 'trabajo'


def recorrer(root):
    """Archivos regulares del aula, sin privados, ocultos, enlaces, credenciales conocidas ni respaldos."""
    for folder, dirs, files in os.walk(root, followlinks=False):
        base = Path(folder)
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d.casefold() not in RESERVADOS
                         and not (base == root and d.casefold() == CARPETA)
                         and not (base / d).is_symlink() and not getattr(base / d, 'is_junction', lambda: False)())
        for name in sorted(files):
            p = base / name
            if (name.startswith('.') and name != '.gitignore') or name.casefold().startswith('.env') \
                    or name.casefold() in SECRETOS or name.endswith(('.pyc', '.tmp', '.lock')):
                continue
            try:
                if p.is_symlink() or not stat.S_ISREG(p.lstat().st_mode):
                    continue
            except OSError:
                continue
            yield p.relative_to(root).as_posix()


def evidencia_actual(root):
    """Rutas citadas por ESTADO.md y sus registros; un estado dañado no impide respaldar."""
    try:
        _, data = leer(root)
    except (ValueError, OSError, UnicodeError) as ex:
        return {}, {}, f'ESTADO.md no se pudo leer ({ex}); se respalda igual, sin salidas generadas.'
    registros = data['registros']
    rutas = {clave_ruta(p) for item in registros.values()
             for g in ('entregables', 'fuentes', 'pruebas', 'aprobacion') for p in item[g]}
    return registros, rutas, ''


def inventario(root):
    registros, evidencia, aviso = evidencia_actual(root)
    trabajo, originales, omitidos = [], [], 0
    for rel in recorrer(root):
        c = clase(rel, evidencia)
        if c in ('trabajo', 'generado'):
            trabajo.append(rel)
        elif c == 'original':
            originales.append(rel)
        else:
            omitidos += 1
    return trabajo, originales, omitidos, registros, aviso


# ── Almacén por huella ─────────────────────────────────────────────────────────

def almacen(root):
    return root / CARPETA


def objeto(root, digest):
    if not HEX.fullmatch(digest):
        raise ValueError('Huella no válida en el respaldo.')
    return almacen(root) / 'objetos' / digest[:2] / (digest + '.gz')


def preparar(root):
    base = almacen(root)
    if base.is_symlink() or (base.exists() and not base.is_dir()):
        raise ValueError('respaldos/ no es una carpeta normal; revísala antes de continuar.')
    for d in (base, base / 'objetos', base / 'hitos'):
        if d.is_symlink():
            raise ValueError('No se usan enlaces simbólicos dentro de respaldos/.')
        d.mkdir(exist_ok=True)
        try:
            os.chmod(d, 0o700)  # Contienen trabajo del docente: solo su usuario los lee.
        except OSError:
            pass
    leeme = base / 'LEEME.txt'
    if not leeme.exists():
        leeme.write_text('Respaldos privados de esta aula (versiones anteriores de tu trabajo).\n'
                         'No los compartas, no los subas a Canvas y no edites su contenido.\n'
                         'Pide al asistente «muéstrame los respaldos» o «vuelve al último resultado aprobado».\n'
                         'Los documentos de fuentes/ no se copian aquí: solo se anotan sus huellas.\n'
                         'Para protegerte de la pérdida del equipo, copia esta carpeta junto con fuentes/ a otro disco.\n',
                         encoding='utf-8')


def guardar_objeto(root, p):
    """Lee el archivo una sola vez: calcula su huella y lo comprime; si ya existe, no lo duplica."""
    before = p.lstat()
    h = hashlib.sha256()
    carpeta = almacen(root) / 'objetos'
    fd, temp = tempfile.mkstemp(prefix='.nuevo-', dir=carpeta)
    try:
        with os.fdopen(fd, 'wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as gz, p.open('rb') as src:
            for block in iter(lambda: src.read(1024 * 1024), b''):
                h.update(block); gz.write(block)
        after = p.lstat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise ValueError(f'{p.name} cambió mientras se respaldaba; repite el respaldo.')
        digest = h.hexdigest()
        final = objeto(root, digest)
        # Una copia existente solo se reutiliza si está íntegra; si no, se repara con la recién leída del original.
        if not final.exists() or final.is_symlink() or not verificar_objeto(root, digest):
            final.parent.mkdir(exist_ok=True)
            if final.is_symlink():
                final.unlink()
            os.chmod(temp, 0o600)
            os.replace(temp, final)
        return digest, before.st_size
    finally:
        Path(temp).unlink(missing_ok=True)


def preparar_copia(root, digest, destino):
    """Descomprime en un temporal junto al destino y devuelve su ruta solo si la huella coincide."""
    src = objeto(root, digest)
    if not src.is_file() or src.is_symlink():
        raise ValueError(f'Falta la copia con huella {digest[:12]}… en respaldos/objetos.')
    fd, temp = tempfile.mkstemp(prefix='.restaurar-', dir=destino.parent)
    try:
        h = hashlib.sha256()
        with os.fdopen(fd, 'wb') as out, gzip.open(src, 'rb') as gz:
            for block in iter(lambda: gz.read(1024 * 1024), b''):
                h.update(block); out.write(block)
            out.flush(); os.fsync(out.fileno())
        if h.hexdigest() != digest:
            raise ValueError(f'La copia de {destino.name} está dañada (huella distinta); no se restauró.')
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise
    return Path(temp)


def leer_objeto(root, digest, destino):
    """Coloca una copia verificada en destino (para extraer en una carpeta nueva)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    temp = preparar_copia(root, digest, destino)
    try:
        if destino.exists():
            os.chmod(temp, stat.S_IMODE(destino.stat().st_mode))
        else:
            mascara = os.umask(0); os.umask(mascara)
            os.chmod(temp, 0o666 & ~mascara)
        os.replace(temp, destino)
    finally:
        Path(temp).unlink(missing_ok=True)


def verificar_objeto(root, digest):
    """True si la copia existe, se descomprime y su contenido conserva la huella."""
    p = objeto(root, digest)
    if not p.is_file() or p.is_symlink():
        return False
    try:
        h = hashlib.sha256()
        with gzip.open(p, 'rb') as gz:
            for block in iter(lambda: gz.read(1024 * 1024), b''):
                h.update(block)
        return h.hexdigest() == digest
    except (OSError, EOFError):
        return False


def huella(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


# ── Hitos ──────────────────────────────────────────────────────────────────────

def slug(s):
    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:24]


def validar_manifiesto(root, m, nombre):
    claves = {'version', 'id', 'fecha', 'tipo', 'motivo', 'unidad', 'estado_sha256', 'evidencias', 'archivos', 'originales', 'omitidos'}
    if not isinstance(m, dict) or set(m) != claves or m['version'] != VERSION or m['id'] != nombre or m['tipo'] not in TIPOS:
        raise ValueError(f'Manifiesto {nombre}: formato no reconocido; no se usa.')
    datetime.fromisoformat(m['fecha'])
    if not isinstance(m['archivos'], dict) or not isinstance(m['originales'], dict):
        raise ValueError(f'Manifiesto {nombre}: listas de archivos no válidas.')
    for rel, info in m['archivos'].items():
        if not isinstance(info, dict) or not HEX.fullmatch(str(info.get('sha256', ''))) or type(info.get('bytes')) is not int:
            raise ValueError(f'Manifiesto {nombre}: entrada no válida.')
        ruta(root, rel, existe=False)  # sin .., sin privados ni reservados
        if bajo(rel, ORIGINALES) and rel not in TRABAJO_EN_FUENTES or bajo(rel, (CARPETA + '/',)):
            raise ValueError(f'Manifiesto {nombre}: incluye una ruta que nunca se restaura ({rel}).')
    for rel, h in m['originales'].items():
        if not HEX.fullmatch(str(h)):
            raise ValueError(f'Manifiesto {nombre}: huella de original no válida.')
    return m


def hitos(root):
    carpeta = almacen(root) / 'hitos'
    if not carpeta.is_dir():
        return []
    result = []
    for p in sorted(carpeta.glob('*.json')):
        if p.is_symlink() or not NOMBRE.fullmatch(p.stem):
            continue
        try:
            m = validar_manifiesto(root, json.loads(p.read_text(encoding='utf-8')), p.stem)
        except (ValueError, OSError, UnicodeError, KeyError, TypeError) as ex:
            result.append({'id': p.stem, 'error': str(ex)})
            continue
        result.append(m)
    return sorted(result, key=lambda m: (m.get('fecha', ''), m['id']))


def buscar_hito(root, nombre):
    validos = [m for m in hitos(root) if 'error' not in m]
    if nombre in ('ultimo', 'último'):
        elegidos = validos
    elif nombre in ('ultimo-aprobado', 'último-aprobado'):
        elegidos = [m for m in validos if m['tipo'] == 'aprobado']
    else:
        elegidos = [m for m in validos if m['id'] == nombre]
    if not elegidos:
        dañado = [m for m in hitos(root) if m['id'] == nombre and 'error' in m]
        if dañado:
            raise ValueError(dañado[0]['error'])
        raise ValueError(f'No hay un respaldo «{nombre}». Usa «listar» para ver los disponibles.')
    return elegidos[-1]


def candado(root):
    if (root / '.estado.lock').exists():
        raise ValueError('Hay un registro de evidencia en curso (.estado.lock); espera a que termine.')
    lock = almacen(root) / '.respaldo.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError('Hay otro respaldo o restauración en curso (respaldos/.respaldo.lock). '
                         'Si una sesión se interrumpió, comprueba que nada esté en marcha antes de retirarlo.') from None
    os.close(fd)
    return lock


def crear(root, tipo, motivo, unidad='', _con_candado=True):
    motivo = ' '.join(str(motivo).split())
    if not motivo:
        raise ValueError('Escribe el motivo del respaldo (por ejemplo, «Antes de rehacer la unidad 2»).')
    if tipo not in TIPOS:
        raise ValueError('Tipo de respaldo no válido.')
    if unidad and not re.fullmatch(r'[A-Za-z0-9 _.-]{1,40}', unidad):
        raise ValueError('La unidad admite letras, números, espacio, punto y guion (máximo 40).')
    ruta(root, 'ESTADO.md', existe=False)
    preparar(root)
    lock = candado(root) if _con_candado else None
    try:
        trabajo, originales, omitidos, registros, aviso = inventario(root)
        archivos = {}
        for rel in trabajo:
            digest, size = guardar_objeto(root, ruta(root, rel))
            archivos[rel] = {'sha256': digest, 'bytes': size}
        orig = {}
        for rel in originales:
            try:
                orig[rel] = huella(ruta(root, rel, existe=False))
            except (ValueError, OSError):
                continue
        estado_sha = archivos.get('ESTADO.md', {}).get('sha256')
        evid = {}
        avisos = [aviso] if aviso else []
        if registros:
            try:
                detalles, _ = analizar(root, registros)
                evid = {d['id']: {'fase': d['fase'], 'vigente': d['vigente'], 'resultado': registros[d['id']]['resultado'],
                                  'aprobacion': bool(registros[d['id']]['aprobacion'])} for d in detalles}
            except ValueError as ex:
                avisos.append(f'No se pudo analizar la vigencia de las evidencias: {ex}')
        if tipo == 'aprobado' and not any(e['vigente'] and e['aprobacion'] for e in evid.values()):
            avisos.append('No hay una evidencia vigente con aprobación docente en ESTADO.md: el respaldo se rotula «aprobado» '
                          'por indicación, sin comprobación de la aprobación.')
        ahora = datetime.now(timezone.utc).astimezone()
        base = '_'.join(x for x in (ahora.strftime('%Y-%m-%d_%H%M%S'), tipo, slug(unidad)) if x)
        nombre, n = base, 2
        while (almacen(root) / 'hitos' / (nombre + '.json')).exists():
            nombre, n = f'{base}_{n}', n + 1
        m = {'version': VERSION, 'id': nombre, 'fecha': ahora.isoformat(timespec='seconds'), 'tipo': tipo, 'motivo': motivo,
             'unidad': unidad or None, 'estado_sha256': estado_sha, 'evidencias': evid, 'archivos': archivos,
             'originales': orig, 'omitidos': omitidos}
        p = almacen(root) / 'hitos' / (nombre + '.json')
        escribir(p, json.dumps(m, ensure_ascii=False, indent=1) + '\n')
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
        return {'respaldo': nombre, 'tipo': tipo, 'motivo': motivo, 'unidad': unidad or None,
                'archivos': len(archivos), 'bytes': sum(a['bytes'] for a in archivos.values()),
                'originales_anotados': len(orig), 'avisos': avisos,
                'limite': 'Copia local dentro del aula: protege contra cambios no deseados, no contra la pérdida del equipo.'}
    finally:
        if lock:
            lock.unlink(missing_ok=True)


# ── Comparar y restaurar ───────────────────────────────────────────────────────

def alcance(root, rutas):
    result = []
    for value in rutas or []:
        rel = ruta(root, value, existe=False).relative_to(root).as_posix()
        if bajo(rel, ORIGINALES) and rel not in TRABAJO_EN_FUENTES:
            raise ValueError(f'{rel}: los documentos originales no se restauran; quedan como están.')
        if bajo(rel, (CARPETA + '/',)):
            raise ValueError('No se restaura la carpeta de respaldos.')
        result.append(rel.rstrip('/'))
    return result


def dentro(rel, prefijos):
    return not prefijos or any(rel == p or rel.startswith(p + '/') for p in prefijos)


def originales_cambiados(root, m):
    actuales = {}
    _, evidencia, _ = evidencia_actual(root)
    for rel in recorrer(root):
        if clase(rel, evidencia) == 'original':
            try:
                actuales[rel] = huella(ruta(root, rel, existe=False))
            except (ValueError, OSError):
                pass
    antes = m['originales']
    return {'modificados': sorted(r for r in antes if r in actuales and actuales[r] != antes[r]),
            'nuevos': sorted(r for r in actuales if r not in antes),
            'ya_no_estan': sorted(r for r in antes if r not in actuales)}


def comparar(root, m, rutas=(), incluir_estado=False):
    prefijos = alcance(root, rutas)
    trabajo, _, _, _, _ = inventario(root)
    actuales = set(trabajo)
    guardados = m['archivos']
    iguales, modificados, eliminados, nuevos, no_restaurar = [], [], [], [], []
    for rel, info in sorted(guardados.items()):
        if not dentro(rel, prefijos):
            continue
        if rel == 'ESTADO.md' and not incluir_estado:
            p = root / rel
            if not p.is_file() or huella(p) != info['sha256']:
                no_restaurar.append(rel)
            continue
        p = ruta(root, rel, existe=False)
        if not p.is_file():
            eliminados.append(rel)
        elif huella(p) == info['sha256']:
            iguales.append(rel)
        else:
            modificados.append(rel)
    _, evidencia, _ = evidencia_actual(root)
    for rel in sorted(actuales - set(guardados)):
        # Solo se retiran archivos de trabajo creados después; las salidas generadas se regeneran.
        if dentro(rel, prefijos) and rel != 'ESTADO.md' and clase(rel, set()) == 'trabajo':
            nuevos.append(rel)
    return {'respaldo': m['id'], 'fecha': m['fecha'], 'tipo': m['tipo'], 'motivo': m['motivo'], 'alcance': prefijos or ['todo el aula'],
            'iguales': len(iguales), 'modificados': modificados, 'eliminados': eliminados, 'nuevos': nuevos,
            'estado_distinto': no_restaurar, 'originales': originales_cambiados(root, m)}


def aplicar_plan(root, escribir_rutas, retirar, motivo_seguridad):
    """Respaldo de seguridad, escritura verificada y retiro; todo bajo el mismo candado."""
    preparar(root)
    lock = candado(root)
    try:
        # Todas las copias se comprueban antes de tocar un solo archivo: nunca queda una restauración a medias por una copia dañada.
        dañadas = [rel for rel, digest in escribir_rutas if not verificar_objeto(root, digest)]
        if dañadas:
            raise ValueError('Copias ausentes o dañadas; no se restauró nada: ' + ', '.join(dañadas) + '. Ejecuta «comprobar».')
        conflictos = conflictos_destino(root, [rel for rel, _ in escribir_rutas])
        if conflictos:
            raise ValueError('No se restauró nada: ' + '; '.join(conflictos) + '. Resuélvelo y repite la vista previa.')
        seguridad = crear(root, 'seguridad', motivo_seguridad, _con_candado=False)
        transaccion(root, escribir_rutas, retirar)
        return seguridad['respaldo']
    finally:
        lock.unlink(missing_ok=True)


def conflictos_destino(root, rutas):
    """Carpetas donde iría un archivo, o archivos donde haría falta una carpeta."""
    result = []
    for rel in rutas:
        p = ruta(root, rel, existe=False)
        if p.exists() and not p.is_file():
            result.append(f'{rel} es ahora una carpeta')
            continue
        d = p.parent
        while d != root:
            if d.exists() and not d.is_dir():
                result.append(f'{d.relative_to(root).as_posix()} es un archivo y {rel} necesita esa carpeta')
                break
            d = d.parent
    return result


def transaccion(root, escribir_rutas, retirar):
    """Prepara todas las copias y después reemplaza; si algo falla, devuelve cada archivo a como estaba."""
    creadas, preparados, hechos = [], [], []   # hechos: (destino, archivo anterior apartado o None)
    try:
        for rel, digest in escribir_rutas:
            dest = ruta(root, rel, existe=False)
            faltan, d = [], dest.parent
            while not d.exists():
                faltan.append(d); d = d.parent
            for d in reversed(faltan):
                d.mkdir(); creadas.append(d)
            temp = preparar_copia(root, digest, dest)
            preparados.append((temp, dest))
            if dest.exists():
                os.chmod(temp, stat.S_IMODE(dest.stat().st_mode))
            else:
                mascara = os.umask(0); os.umask(mascara)
                os.chmod(temp, 0o666 & ~mascara)
        for temp, dest in preparados:
            apartado = None
            if dest.exists():
                apartado = apartar(dest)
            hechos.append((dest, apartado))
            os.replace(temp, dest)
        for rel in retirar:
            p = ruta(root, rel, existe=False)
            if p.is_file():
                hechos.append((p, apartar(p)))
    except BaseException:
        for dest, apartado in reversed(hechos):
            if apartado is not None:
                os.replace(apartado, dest)
            else:
                dest.unlink(missing_ok=True)
        for temp, _ in preparados:
            temp.unlink(missing_ok=True)
        for d in reversed(creadas):
            try:
                d.rmdir()
            except OSError:
                pass
        raise
    for dest, apartado in hechos:
        if apartado is not None:
            apartado.unlink(missing_ok=True)
    for rel in retirar:
        d = ruta(root, rel, existe=False).parent
        while d != root and d.is_dir() and not any(d.iterdir()):
            d.rmdir(); d = d.parent


def apartar(p):
    """Mueve el archivo actual a un temporal oculto en la misma carpeta, para poder devolverlo."""
    fd, nombre = tempfile.mkstemp(prefix='.anterior-', dir=p.parent)
    os.close(fd)
    os.replace(p, nombre)
    return Path(nombre)


def despues(root, restaurados):
    """Qué revisar tras restaurar: evidencias y recompilación."""
    pasos = []
    if any(r.startswith('hub/src/') for r in restaurados) and not any(r.startswith('hub/dist/') for r in restaurados):
        pasos.append('Recompila el aula (python3 hub/build.py) y regenera las entregas que dependan de ella.')
    try:
        _, data = leer(root)
        detalles, _ = analizar(root, data['registros'])
        pendientes = [d['id'] for d in detalles if not d['vigente']]
        if pendientes:
            pasos.append('Evidencias por revisar después de restaurar: ' + ', '.join(pendientes) + ' (control/estado.py verificar).')
    except (ValueError, OSError, UnicodeError) as ex:
        pasos.append(f'No se pudo contrastar ESTADO.md: {ex}')
    pasos.append('Anota la restauración en ESTADO.md (Decisiones y Punto de reanudación) y actualiza el panel.')
    return pasos


def restaurar(root, nombre, rutas=(), aplicar=False, incluir_estado=False):
    m = buscar_hito(root, nombre)
    c = comparar(root, m, rutas, incluir_estado)
    escribir_rutas = [(r, m['archivos'][r]['sha256']) for r in c['modificados'] + c['eliminados']]
    for rel, digest in escribir_rutas:
        if not objeto(root, digest).is_file():
            raise ValueError(f'Falta la copia de {rel} en respaldos/objetos; el respaldo está incompleto y no se aplicó nada.')
    plan = {**c, 'aplicado': False, 'restaurar': [r for r, _ in escribir_rutas], 'retirar': c['nuevos']}
    avisos = []
    if c['estado_distinto']:
        avisos.append('ESTADO.md no se restaura: conserva fases y decisiones posteriores. Compáralo a mano si hace falta '
                      '(--incluir-estado solo si el docente pide volver también al registro de entonces).')
    o = c['originales']
    if o['modificados'] or o['nuevos'] or o['ya_no_estan']:
        avisos.append('Los documentos originales cambiaron desde ese respaldo y se conservan tal como están; '
                      'las evidencias que los usan quedarán pendientes de revisión.')
    plan['avisos'] = avisos
    if not escribir_rutas and not c['nuevos']:
        plan['mensaje'] = 'Nada que restaurar: los archivos del alcance ya coinciden con el respaldo.'
        return plan
    if not aplicar:
        plan['mensaje'] = 'Vista previa: no se cambió nada. Repite con --aplicar para restaurar.'
        return plan
    plan['respaldo_de_seguridad'] = aplicar_plan(root, escribir_rutas, c['nuevos'],
                                                 f'Antes de restaurar {m["id"]}' + (f' ({", ".join(c["alcance"])})' if rutas else ''))
    plan['aplicado'] = True
    plan['mensaje'] = f'Restaurado. Para deshacerlo: restaurar {plan["respaldo_de_seguridad"]}.'
    plan['siguientes_pasos'] = despues(root, plan['restaurar'])
    return plan


def restaurar_evidencia(root, ident, aplicar=False):
    """Vuelve los entregables, pruebas y aprobaciones de un registro a las huellas guardadas en ESTADO.md."""
    _, data = leer(root)
    if ident not in data['registros']:
        raise ValueError(f'No existe la evidencia «{ident}» en ESTADO.md.')
    item = data['registros'][ident]
    escribir_rutas, sin_copia, regenerar = [], [], []
    for grupo in ('entregables', 'pruebas', 'aprobacion'):
        for name, digest in item[grupo].items():
            p = ruta(root, name, existe=False)
            rel = p.relative_to(root).as_posix()
            if p.is_file() and huella(p) == digest:
                continue
            if bajo(rel, ORIGINALES) and rel not in TRABAJO_EN_FUENTES:
                regenerar.append(rel)
            elif objeto(root, digest).is_file():
                escribir_rutas.append((rel, digest))
            else:
                sin_copia.append(rel)
    fuentes = []
    for name, digest in item['fuentes'].items():
        try:
            if huella(ruta(root, name)) != digest:
                fuentes.append(name)
        except (ValueError, OSError):
            fuentes.append(name)
    plan = {'evidencia': ident, 'fase': item['fase'], 'fecha_registro': item['fecha'], 'aplicado': False,
            'restaurar': [r for r, _ in escribir_rutas], 'sin_copia': sin_copia, 'no_restaurables': regenerar,
            'fuentes_cambiadas': fuentes, 'avisos': []}
    if fuentes:
        plan['avisos'].append('Estas fuentes cambiaron desde la revisión y no se tocan: ' + ', '.join(fuentes) +
                              '. Tras restaurar, la evidencia seguirá pendiente hasta revisarla con las fuentes actuales.')
    if regenerar:
        plan['avisos'].append('Documentos en carpetas de originales que no se restauran: ' + ', '.join(regenerar) + '.')
    if sin_copia:
        plan['mensaje'] = ('No se aplicó nada: no hay copia guardada de ' + ', '.join(sin_copia) +
                           '. Crea respaldos «aprobado» justo después de registrar una revisión para poder volver a ella.')
        return plan
    if not escribir_rutas:
        plan['mensaje'] = 'Nada que restaurar: los archivos ya coinciden con lo registrado en ESTADO.md.'
        return plan
    if not aplicar:
        plan['mensaje'] = 'Vista previa: no se cambió nada. Repite con --aplicar para restaurar.'
        return plan
    plan['respaldo_de_seguridad'] = aplicar_plan(root, escribir_rutas, [], f'Antes de volver a la evidencia {ident}')
    plan['aplicado'] = True
    plan['mensaje'] = f'Restaurado a lo registrado en «{ident}». Para deshacerlo: restaurar {plan["respaldo_de_seguridad"]}.'
    plan['siguientes_pasos'] = despues(root, plan['restaurar'])
    return plan


# ── Consultas de mantenimiento ─────────────────────────────────────────────────

def tamaño_almacen(root):
    base = almacen(root) / 'objetos'
    if not base.is_dir():
        return 0, set()
    total, presentes = 0, set()
    for p in base.glob('*/*.gz'):
        if p.is_file() and not p.is_symlink():
            total += p.stat().st_size
            presentes.add(p.name[:-3])
    return total, presentes


def listar(root):
    lista = hitos(root)
    total, _ = tamaño_almacen(root)
    return {'respaldos': [{k: m.get(k) for k in ('id', 'fecha', 'tipo', 'unidad', 'motivo', 'error')} |
                          {'archivos': len(m.get('archivos', {}))} for m in reversed(lista)],
            'bytes_en_disco': total, 'carpeta': CARPETA + '/'}


def comprobar(root):
    lista = hitos(root)
    _, presentes = tamaño_almacen(root)
    usados, problemas, revisados = set(), [], {}
    for m in lista:
        if 'error' in m:
            problemas.append(f'{m["id"]}: {m["error"]}')
            continue
        for rel, info in m['archivos'].items():
            d = info['sha256']
            usados.add(d)
            if d not in revisados:
                revisados[d] = verificar_objeto(root, d)
            ok = revisados[d]
            if not ok:
                problemas.append(f'{m["id"]}: copia ausente o dañada de {rel}')
    huerfanos = presentes - usados
    total, _ = tamaño_almacen(root)
    return {'respaldos': len(lista), 'copias_revisadas': len(revisados), 'problemas': problemas,
            'copias_sin_respaldo_que_las_use': len(huerfanos), 'bytes_en_disco': total,
            'resultado': 'con_problemas' if problemas else 'sin_problemas'}


def extraer(root, nombre, destino):
    m = buscar_hito(root, nombre)
    destino = destino.expanduser().resolve()
    if destino.is_relative_to(root):
        raise ValueError('Extrae fuera del aula para no mezclar una copia antigua con el trabajo actual.')
    if destino.exists() and (not destino.is_dir() or any(destino.iterdir())):
        raise ValueError('La carpeta de destino debe ser nueva o estar vacía.')
    destino.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.extraer-', dir=destino.parent))
    try:
        for rel, info in m['archivos'].items():
            leer_objeto(root, info['sha256'], ruta(temp, rel, existe=False))
        (temp / 'RESPALDO.json').write_text(json.dumps(m, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        if destino.exists():
            destino.rmdir()
        temp.rename(destino)
    finally:
        if temp.exists():
            shutil.rmtree(temp, ignore_errors=True)
    return {'respaldo': m['id'], 'destino': str(destino), 'archivos': len(m['archivos']),
            'aviso': 'Los documentos de fuentes/ no forman parte del respaldo: cópialos desde su ubicación original.'}


def resumen(root):
    """Para el panel: último respaldo, último aprobado y evidencias aprobadas sin copia guardada."""
    lista = [m for m in hitos(root) if 'error' not in m]
    dañados = sum(1 for m in hitos(root) if 'error' in m)
    _, presentes = tamaño_almacen(root)
    sin_copia = []
    try:
        _, data = leer(root)
        for ident, item in data['registros'].items():
            if item['resultado'] == 'pasado' and (item['aprobacion'] or item['tipo'] == 'docente'):
                if any(d not in presentes for d in item['entregables'].values()):
                    sin_copia.append(ident)
    except (ValueError, OSError, UnicodeError):
        pass
    corto = lambda m: m and {k: m[k] for k in ('id', 'fecha', 'tipo', 'unidad', 'motivo')}
    aprobados = [m for m in lista if m['tipo'] == 'aprobado']
    return {'total': len(lista), 'dañados': dañados, 'ultimo': corto(lista[-1] if lista else None),
            'ultimo_aprobado': corto(aprobados[-1] if aprobados else None), 'aprobadas_sin_copia': sorted(sin_copia)}


# ── Salida ─────────────────────────────────────────────────────────────────────

def texto(cmd, r):
    if cmd == 'listar':
        if not r['respaldos']:
            return 'Aún no hay respaldos en esta aula.\n'
        lines = [f'Respaldos ({len(r["respaldos"])}, {r["bytes_en_disco"] / 1e6:.1f} MB en {r["carpeta"]}), del más reciente al más antiguo:', '']
        for m in r['respaldos']:
            if m.get('error'):
                lines.append(f'- {m["id"]}: DAÑADO ({m["error"]})'); continue
            u = f' · {m["unidad"]}' if m.get('unidad') else ''
            lines.append(f'- {m["id"]} · {TIPOS[m["tipo"]]}{u} · {m["archivos"]} archivos · {m["motivo"]}')
        return '\n'.join(lines) + '\n'
    if cmd == 'crear':
        lines = [f'Respaldo creado: {r["respaldo"]} ({r["archivos"]} archivos, {r["bytes"] / 1e6:.1f} MB sin comprimir).',
                 f'Documentos originales anotados por huella (no copiados): {r["originales_anotados"]}.', r['limite']]
        return '\n'.join(lines + ['Aviso: ' + a for a in r['avisos']]) + '\n'
    if cmd in ('comparar', 'restaurar'):
        lines = []
        if 'evidencia' in r:
            lines.append(f'Evidencia {r["evidencia"]} (fase {r["fase"]}, registrada {r["fecha_registro"]}).')
        else:
            lines.append(f'Respaldo {r["respaldo"]} · {TIPOS[r["tipo"]]} · {r["motivo"]} · alcance: {", ".join(r["alcance"])}')
        hecho = r.get('aplicado')
        for clave, titulo in (('modificados', 'Cambiaron desde entonces (se restaurarían)'),
                              ('eliminados', 'Ya no están (se recuperarían)'),
                              ('nuevos', 'Creados después (retirados; están en el respaldo de seguridad)' if hecho
                               else 'Creados después (se retirarían; quedan en el respaldo de seguridad)'),
                              ('restaurar', 'Restaurados' if hecho else 'Se restaurarían'), ('sin_copia', 'Sin copia guardada'),
                              ('fuentes_cambiadas', 'Fuentes cambiadas desde la revisión (no se tocan)')):
            if clave in r and r[clave] and not (cmd == 'restaurar' and clave in ('modificados', 'eliminados') and 'restaurar' in r):
                lines += ['', titulo + ':'] + ['  - ' + x for x in r[clave]]
        o = r.get('originales')
        if o and (o['modificados'] or o['nuevos'] or o['ya_no_estan']):
            lines += ['', 'Documentos originales distintos de entonces (se conservan como están):']
            lines += ['  - modificado: ' + x for x in o['modificados']] + ['  - nuevo: ' + x for x in o['nuevos']]
            lines += ['  - ya no está: ' + x for x in o['ya_no_estan']]
        if r.get('estado_distinto'):
            lines += ['', 'ESTADO.md es distinto del de entonces y no se restaura.']
        lines += [''] + ['Aviso: ' + a for a in r.get('avisos', [])]
        if r.get('mensaje'):
            lines.append(r['mensaje'])
        lines += ['Siguiente: ' + p for p in r.get('siguientes_pasos', [])]
        return '\n'.join(lines).strip() + '\n'
    if cmd == 'comprobar':
        lines = [f'{r["respaldos"]} respaldos, {r["copias_revisadas"]} copias revisadas, {r["bytes_en_disco"] / 1e6:.1f} MB.',
                 'Sin problemas.' if not r['problemas'] else 'Problemas:']
        lines += ['  - ' + p for p in r['problemas']]
        if r['copias_sin_respaldo_que_las_use']:
            lines.append(f'{r["copias_sin_respaldo_que_las_use"]} copias ya no las usa ningún respaldo (quedaron al borrar manifiestos).')
        return '\n'.join(lines) + '\n'
    if cmd == 'extraer':
        return f'Respaldo {r["respaldo"]} reconstruido en {r["destino"]} ({r["archivos"]} archivos).\n{r["aviso"]}\n'
    return json.dumps(r, ensure_ascii=False, indent=2) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--aula', type=Path, default=Path(__file__).resolve().parents[1])
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('crear', help='Guardar un hito recuperable')
    c.add_argument('--tipo', choices=('antes', 'aprobado', 'manual'), default='manual')
    c.add_argument('--motivo', required=True); c.add_argument('--unidad', default='')
    sub.add_parser('listar', help='Respaldos disponibles, del más reciente al más antiguo')
    k = sub.add_parser('comparar', help='Qué cambió desde un respaldo (no modifica nada)')
    k.add_argument('respaldo', help='nombre, «ultimo» o «ultimo-aprobado»'); k.add_argument('--ruta', action='append', default=[])
    r = sub.add_parser('restaurar', help='Volver a un respaldo o a lo registrado en una evidencia; vista previa sin --aplicar')
    r.add_argument('respaldo', nargs='?', help='nombre, «ultimo» o «ultimo-aprobado»')
    r.add_argument('--evidencia', help='ID de ESTADO.md cuyos entregables vuelven a las huellas registradas')
    r.add_argument('--ruta', action='append', default=[], help='limitar a un archivo o carpeta (repetible)')
    r.add_argument('--incluir-estado', action='store_true', help='restaurar también ESTADO.md (solo si el docente lo pide)')
    r.add_argument('--aplicar', action='store_true')
    sub.add_parser('comprobar', help='Comprobar que las copias guardadas estén completas e intactas')
    e = sub.add_parser('extraer', help='Reconstruir un respaldo completo en una carpeta nueva fuera del aula')
    e.add_argument('respaldo'); e.add_argument('--destino', type=Path, required=True)
    for p in sub.choices.values():
        p.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    root = args.aula.expanduser().resolve()
    try:
        if not (root / 'ESTADO.md').is_file():
            raise ValueError(f'{root} no parece un aula (falta ESTADO.md).')
        if args.cmd == 'crear':
            res = crear(root, args.tipo, args.motivo, args.unidad)
        elif args.cmd == 'listar':
            res = listar(root)
        elif args.cmd == 'comparar':
            res = comparar(root, buscar_hito(root, args.respaldo), args.ruta)
        elif args.cmd == 'restaurar':
            if bool(args.respaldo) == bool(args.evidencia):
                raise ValueError('Indica un respaldo o --evidencia ID (uno de los dos).')
            if args.evidencia and (args.ruta or args.incluir_estado):
                raise ValueError('--evidencia ya define qué archivos vuelven; no se combina con --ruta ni --incluir-estado.')
            res = (restaurar_evidencia(root, args.evidencia, args.aplicar) if args.evidencia
                   else restaurar(root, args.respaldo, args.ruta, args.aplicar, args.incluir_estado))
        elif args.cmd == 'comprobar':
            res = comprobar(root)
        else:
            res = extraer(root, args.respaldo, args.destino)
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=2) + '\n' if args.json else texto(args.cmd, res))
        if args.cmd == 'comprobar':
            return int(bool(res['problemas']))
        if args.cmd == 'restaurar' and res.get('sin_copia'):
            return 1
        return 0
    except (ValueError, OSError, UnicodeError) as ex:
        print('No se completó la operación: ' + str(ex), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
