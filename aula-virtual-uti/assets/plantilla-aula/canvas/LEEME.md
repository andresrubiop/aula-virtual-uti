# Llevar tu aula a Canvas

El asistente prepara el archivo que termina en `-canvas.imscc`, dentro de `canvas/salida/`. Tú lo importas en el curso que corresponda. Primero abre el aula local con doble clic en `hub/dist/index.html` y comprueba sus contenidos.

## Antes de importar

Revisa el sílabo, las actividades, sus fechas, los puntajes y los materiales. El asistente debe haber comprobado el paquete y explicado los avisos pendientes. Una prueba local satisfactoria todavía no demuestra que Canvas lo haya importado correctamente.

Si tu curso ya contiene material, conserva una exportación antes de modificarlo y usa un curso de prueba cuando esté disponible. Para adaptar la plantilla de tu curso, entrega al asistente esa exportación original; la colocará en `canvas/exportado/`. Si no la entregas, se utiliza la plantilla institucional incluida y pueden aparecer páginas duplicadas.

## Importar el archivo

1. Entra al curso de destino y abre **Configuración → Importar contenido del curso**.
2. Selecciona **Paquete de exportación de curso de Canvas** y el archivo `.imscc` preparado.
3. En un curso de prueba vacío, selecciona todo el contenido para probar la entrega completa. En un curso existente, revisa con el asistente qué se va a incorporar antes de iniciar la importación.
4. Revisa las opciones de fechas y añade la importación a la cola. Espera a que termine y revisa cualquier incidencia.

Estos pasos se basan en la [guía oficial de importación](https://community.instructure.com/en/kb/articles/660728-how-do-i-import-a-canvas-course-export-package), consultada el 13 de noviembre de 2026. Los nombres pueden variar según el idioma y la configuración de tu institución. Si falta espacio, consulta al administrador; el tamaño permitido no es igual en todos los cursos.

## Revisar antes de publicar

- Abre Inicio, Presentación, cada momento, sus sesiones y recursos.
- Prueba el aula en una pestaña nueva y también descargándola. Si la vista integrada no funciona, utiliza la descarga local.
- Comprueba PDF, guías prácticas, enlaces, imágenes y videos; prueba ES/EN dentro del aula y en los materiales disponibles.
- Revisa las tareas de prácticas y las actividades de cada momento: fechas, puntos, grupos de calificación y rúbricas. Algunas configuraciones pueden venir de la plantilla. Las rúbricas visibles son tablas de contenido; no equivalen a una rúbrica configurada en SpeedGrader.
- Comprueba la vista de estudiante. Conserva la edición `profesor.html` y sus solucionarios en tu equipo. Publica solo las tareas y páginas que corresponda.

Los videos que aún no se hayan producido aparecerán como pendientes. El cuestionario interactivo sirve para practicar y guarda el progreso en el navegador; no envía calificaciones a Canvas. Las páginas institucionales de Canvas se generan en español; el aula y los materiales bilingües se consultan desde ellas.

## Si necesitas conservar páginas existentes

El asistente puede preparar fragmentos en `canvas/salida/pegar/`. Abre la página correspondiente en Canvas, pulsa **Editar**, cambia a la vista **HTML**, pega el fragmento indicado y guarda. Después comprueba su aspecto y sus enlaces. [Guía oficial de la vista HTML](https://community.instructure.com/en/kb/articles/662912-how-do-i-use-the-html-view-in-the-rich-content-editor).

El asistente debe preparar primero los archivos, páginas y enlaces de tu curso: pegar un fragmento no crea esos recursos. No pegues el archivo completo del aula interactiva en el editor de páginas; se entrega como archivo descargable.

## Actualizar después

Guarda una copia de la entrega anterior. Pide al asistente que prepare los archivos actualizados y explique qué páginas o recursos cambian. No supongas que volver a importar evita duplicados o conserva todas las ediciones hechas dentro de Canvas. La [guía de exportación](https://community.instructure.com/en/kb/articles/660734-how-do-i-export-a-canvas-course) explica cómo descargar una copia del contenido del curso; esa exportación no respalda las entregas ni las notas de los estudiantes.

## Para el asistente

Ejecuta `python3 canvas/validar_silabo.py` antes de `python3 canvas/generar_canvas.py`, y después `python3 canvas/verificar_paquete.py`. El esquema detallado y el ejemplo están en `references/silabo.md` y `references/silabo-ejemplo.json` de la skill instalada. Copia el ejemplo a `canvas/silabo.json` solo para una demostración; para un curso real transcribe sus fuentes. No declares una demostración como sílabo aprobado.

## Versión bilingüe

Pide al asistente completar y revisar las traducciones de páginas y tareas con `traducir_paquete.py`. El paquete final termina en `-bilingue.imscc`; conserva el texto español y añade inglés. Los PDF bilingües no traducen por sí solos las páginas de Canvas. Si cambian las fuentes, el asistente debe revisar de nuevo las traducciones antes de generar la entrega.
