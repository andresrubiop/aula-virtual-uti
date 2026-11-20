# Proyecto Interdisciplinario Socioformativo (PIS)

El PIS integra varios proyectos formativos de un mismo nivel alrededor de un problema del territorio y una evidencia integradora común. Uno de ellos es el **articulador**; los demás **aportan**. La skill trata el PIS como un módulo propio que el articulador diseña y comparte.

## Pregunta inicial (obligatoria si el sílabo declara PIS)

> «¿Tu proyecto formativo es el articulador (integrador) del PIS de tu nivel, aporta a un PIS que integra otro proyecto formativo, o este período no tiene PIS?»

La respuesta se guarda en `canvas/silabo.json` → `"pis_rol"`: `"articulador"`, `"aportante"` o `"no_aplica"`. `validar_silabo.py` la exige cuando hay `pis`. Regístrala también en Decisiones de ESTADO.md.

## Si es el articulador: el PIS es obligatorio

1. Pide el **documento del PIS** (formato institucional o documento de formulación) y guárdalo en `fuentes/pis/`. Sin él no se genera el paquete de Canvas.
2. Transcribe el documento a `canvas/pis.json` sin inventar nada: título, proyecto formativo articulador, reto, propósito, resultado de aprendizaje del PIS, proyectos formativos con su RA y aporte, momentos (fechas, semanas, hito, propósito, actividades, evidencia parcial), evidencia integradora (trabajos y componentes), rúbrica (cinco niveles e indicadores con cinco descriptores, reglas) y competencias. Bloques `"es"` y `"en"` con las mismas piezas; la traducción la hace el asistente y el docente la revisa. Formato: [pis-ejemplo.json](pis-ejemplo.json).
3. `python3 control/pis.py` comprueba documento, datos y coherencia de idiomas. Lo faltante en el documento queda `[COMPLETAR: …]` y se pregunta.
4. `python3 hub/build.py` añade la vista **PIS** al aula (menú superior: proyecto, momentos, rúbrica, evidencia integradora, en ES/EN).
5. `python3 canvas/generar_canvas.py` reemplaza el módulo «PIS» de la plantilla por **«PIS: <título>»**: página del proyecto, una página por momento, rúbrica y evidencia integradora, y las tareas PIS de la plantilla (sus RA con `pis_ra`). Todo **sin publicar** hasta la revisión docente.
6. **Compartir:** `python3 control/pis.py exportar` crea `pis/compartir/PIS-<clave>-<fecha>.zip` (solo `pis.json`; `--con-documentos` añade los de `fuentes/pis/` si el docente lo decide; revisa antes que no contengan datos personales). El docente lo envía a los docentes de los proyectos formativos que aportan.

## Si aporta: se pide el PIS al articulador

Pide al docente que solicite al docente articulador el paquete del PIS. Mientras no llegue, el aula se construye igual y el PIS queda **pendiente** (aviso en `control/pis.py`, en el panel y en el generador de Canvas). Al recibirlo:

```bash
python3 control/pis.py importar PIS-<clave>-<fecha>.zip
python3 hub/build.py && python3 canvas/generar_canvas.py
```

La vista y el módulo indican que el PIS es compartido por el articulador. No edites el contenido importado: las correcciones las hace el articulador y vuelve a compartir (el import anterior queda en `canvas/pis.anterior.json`).

## Llevar solo el módulo PIS a Canvas

```bash
python3 canvas/canvas_api.py plan --modulo PIS        # solo lectura
python3 canvas/canvas_api.py aplicar --modulo PIS     # con la conformidad del docente
```

Actualiza o crea solo las páginas, tareas y archivos del módulo PIS y reutiliza el módulo «PIS» que ya tenga el curso (el de la plantilla institucional). El resto del curso no se toca. Sirve tanto en el curso del articulador como en el de cada proyecto formativo que aporta.

## Comprobaciones

- `python3 control/pis.py [--json]`: rol, documentos, datos, errores y pendientes (código 1 con errores).
- `python3 control/panel.py`: tarjeta PIS con el rol y lo que falta.
- El PIS se valora con su propia rúbrica; no sustituye las rúbricas de las evidencias de cada momento del proyecto formativo.
