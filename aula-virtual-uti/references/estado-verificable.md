# Verificar el estado del aula (mejora 2)

## Qué resuelve

`control/estado.py` contrasta el estado declarado con archivos reales. Detecta entregables ausentes o modificados, fuentes o informes de pruebas cambiados y fases marcadas ✅ sin respaldo vigente. El registro de evidencia vive en un bloque al final de **ESTADO.md**, junto a las decisiones y el punto de reanudación: no hay un segundo tablero.

El asistente ejecuta los comandos. El profesor decide sobre lo académico y puede pedir: «Comprueba el estado y dime desde dónde continuar». Este control verifica las evidencias declaradas; no descubre todos los archivos del curso, no ejecuta comandos escritos en documentos ni certifica el contenido de un informe. La [actualización por cambios](actualizacion-incremental.md) propaga la vigencia entre entregables y prepara un plan de revisión en orden.

## Al retomar o cerrar una sesión

Desde la carpeta del aula:

```bash
python3 control/estado.py verificar
```

En Windows usa el ejecutable disponible, por ejemplo `py -3`. Para leer el resultado estructurado, añade `--json`. El informe legible se escribe en `control/VERIFICACION_ESTADO.md`; es una salida regenerable. Lleva fecha y huella del estado comprobado. Vuelve a generarlo después de cualquier cambio, incluso si ayer no tenía incidencias.

Códigos de salida: **0** sin discrepancias detectadas en lo registrado; **1** hay evidencia pendiente, obsoleta o contradicción en el estado; **2** no se pudo comprobar por formato, rutas o lectura/escritura. Un resultado 0 no significa curso terminado: las fases pendientes siguen pendientes. Si no hay registros, el informe lo advierte. Si el estado está malformado, reemplaza el informe anterior por «Verificación no completada» cuando la ruta permite escribirlo.

La herramienta conserva las decisiones y no cambia los símbolos de las fases. Muestra la próxima acción guardada y, si hay una incidencia, señala qué debe resolverse primero. El asistente interpreta el resultado, revisa lo necesario y actualiza el punto de reanudación en Markdown.

## Registrar después de comprobar

Ejemplo: tras ejecutar el validador del sílabo, conservar su resultado real en `control/validacion-silabo.txt` y cotejar qué datos utilizó:

```bash
python3 control/estado.py registrar silabo --fase 2 --entregable canvas/silabo.json --fuente fuentes/silabo/vigente.pdf --prueba control/validacion-silabo.txt --resultado pasado
```

Sustituye las rutas por las existentes; el comando no crea el sílabo ni realiza la validación. Debe haber al menos un entregable, una fuente y, si el resultado es `pasado` o `fallido`, un informe real. `no_ejecutado` permite registrar trabajo parcial, pero no respalda una fase lista.

- Repite `--entregable`, `--fuente` o `--prueba` para cubrir todos los archivos que sustentan ese hito. Incluye el código o configuración relevantes como fuentes de una prueba técnica.
- Los archivos deben ser distintos, no vacíos y estar dentro del aula. No se leen enlaces, carpetas privadas ni rutas externas.
- Se guardan fecha UTC y SHA256 de cada archivo. Si cambia una fuente, salida o prueba registrada, la evidencia deja de estar vigente hasta revisarla y registrarla de nuevo.
- Un ID existente exige `--reemplazar`. No lo uses solo para borrar una alerta: repite la comprobación afectada primero. La herramienta preserva el resto del Markdown, incluso notas añadidas después del bloque.
- No registres `ESTADO.md` ni el informe derivado como prueba de sí mismos. Conserva informes específicos en otros archivos.

Para fases que requieren decisión docente (3, 4 y 9), añade `--aprobacion control/revision-docente.md`, con la decisión real, fecha y alcance. La presencia y huella de ese archivo no autentican quién lo escribió: no fabriques aprobaciones para pasar el control.

Para fase 9, añade `--tipo remota` solo después de observar la importación y la revisión en el curso. Guarda el informe real sin credenciales ni datos de estudiantes. Un paquete ZIP validado localmente no respalda una importación. `--tipo docente` identifica una revisión manual; por defecto es `local`. Estos tipos son declaraciones, no conexiones a un servicio.

## Formato y fases

Conserva la tabla «## 1. Fases» (también admite «## Fases»), las diez filas 0–9 y los estados ✅, 🟡, ⬜ o ⛔. Para omitir videos por decisión docente usa **⏭** en fase 7 y explica el motivo en Notas; las demás fases no se omiten con ese símbolo.

Una fase ✅ debe tener registros vigentes con resultado `pasado`. Se comprueban además entregables fijos: fase 0, `hub/src/course.json` y `hub/dist/index.html`; fase 1, `fuentes/INVENTARIO.md`; fase 2, `canvas/silabo.json`; fase 3, `PLANIFICACION.md`; fase 8, algún `.imscc` registrado. El resto del alcance de cada fase debe revisarlo el asistente con el docente: un archivo existente no demuestra completitud académica.

En «Punto de reanudación» conserva **Fase actual**, **Próxima acción exacta** y **Archivo o carpeta de trabajo**. Escribe las rutas de trabajo entre acentos graves, por ejemplo `hub/src/content/u1/`. No inventes un avance para adaptar el formato.

## Aulas creadas con una versión anterior

Puedes ejecutar la herramienta actual sobre el aula sin recrearla ni reemplazar sus archivos:

```bash
python3 <skill>/assets/plantilla-aula/control/estado.py --aula <carpeta-del-aula> verificar
```

No necesita que exista el bloque de evidencia para leer el estado. Al registrar el primer hito, lo añade al final. Si hay fases listas sin registro, inspecciona sus archivos y repite las pruebas necesarias antes de registrarlas. Si la tabla tiene otro formato, adapta solo encabezados y columnas, conservando decisiones, pendientes y fechas. No cambies los resultados para obtener un código 0.

## Interrupciones y límites

El registro se escribe de forma atómica. `.estado.lock` impide dos registros simultáneos; si queda tras una interrupción, comprueba que no haya otro proceso activo antes de retirarlo. Un cambio externo de ESTADO.md durante el registro provoca error para evitar perder notas. No trabajes con dos asistentes editando simultáneamente.

Los informes y evidencias son material de trabajo del profesor; no se incorporan al HTML estudiantil ni al paquete Canvas. Trasladar el aula completa conserva sus rutas relativas. El análisis de impacto no regenera contenido automáticamente. La skill guía su actualización selectiva; la matriz del sílabo, el panel y los respaldos quedan fuera de esta entrega.
