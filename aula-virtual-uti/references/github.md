# El aula en GitHub (obligatorio)

Cada aula vive en un **repositorio privado de la cuenta de GitHub del docente**. Así tiene historial de cada cambio, una copia fuera del equipo y un relevo seguro entre días, equipos y asistentes. Es obligatorio: sin el aula conectada a GitHub, `canvas/generar_canvas.py` no produce la entrega (solo un borrador con `--borrador`) y el panel lo marca en rojo.

## Antes de empezar

1. **Git instalado.** `python3 <skill>/scripts/entorno.py` lo exige (Linux: `sudo apt install git`; macOS: `xcode-select --install`; Windows: `winget install Git.Git`).
2. **Cuenta de GitHub del docente.** La crea él mismo en <https://github.com/signup> (gratis); conviene usar el correo institucional. El asistente no crea cuentas ni escribe contraseñas o códigos.
3. **Sesión iniciada.** El docente instala GitHub CLI (`gh`) y ejecuta él mismo `gh auth login` (GitHub.com → navegador). `entorno.py` muestra «Cuenta de GitHub (gh): sesión iniciada».
4. **Identidad de Git** (aparece en el historial): `git config --global user.name "Nombre Apellido"` y `git config --global user.email "correo@…"`, con los datos que indique el docente.

## Conectar el aula

`nuevo_aula.py` crea el aula ya como repositorio Git (rama `main`). Con la conformidad del docente para crear el repositorio en su cuenta:

```bash
python3 control/repositorio.py iniciar --crear aula-<clave>          # repositorio PRIVADO nuevo en su cuenta (gh)
python3 control/repositorio.py iniciar --remoto https://github.com/<usuario>/<repo>.git   # o uno vacío que él creó
python3 control/repositorio.py                                       # estado
```

El repositorio se crea **privado**: contiene el sílabo y los materiales del docente. Si el estado avisa «PÚBLICO», recomiéndale cambiarlo a privado salvo decisión expresa suya (por ejemplo, para compartir una plantilla sin documentos).

## Guardar en cada hito y al cerrar

```bash
python3 control/repositorio.py guardar -m "Unidad 2 lista para revisión"
```

Hace commit de los cambios y los sube. Antes revisa lo preparado y **se detiene** si encuentra `fuentes/privado/`, `canvas/api/privado/`, `respaldos/`, `.env`, llaves, el token de Canvas guardado en el equipo o algo con forma de token, o archivos de más de 50 MB. Lo generado (`hub/dist/`, `autonomo/`, `canvas/salida/`, videos MP4, `pis/compartir/`) está en `.gitignore` y se regenera desde la fuente.

Guarda al terminar cada unidad, antes de una operación externa (Canvas, videos) y al cerrar cada sesión, después de actualizar ESTADO.md. En el mensaje describe el avance en lenguaje del docente.

## Qué no hace

- No sustituye los respaldos por hitos (`control/respaldo.py`), que permiten volver atrás dentro del aula; GitHub guarda el historial completo fuera del equipo.
- No publica el aula para los estudiantes: la entrega sigue siendo Canvas o el aula para llevar.
- No resuelve conflictos si dos asistentes editan a la vez: trabaja en un solo equipo o guarda y descarga (`git pull`) antes de cambiar de equipo.
