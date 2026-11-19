# Preparar la entrega para Canvas

Lee esta referencia al mapear sesiones y guías prácticas o al generar el `.imscc`. Para acompañar al docente usa `canvas/LEEME.md` de su aula; los comandos los ejecuta el asistente.

La [Guía del profesor](../GUIA_DE_USO.md#8-importar-en-canvas-indoamérica) explica el acceso en `https://indoamerica.instructure.com/login/saml`, la importación manual del `.imscc` y la revisión posterior. El docente inicia sesión; no se presupone acceso automático. En `ESTADO.md` registra por separado paquete validado localmente, revisión docente, importación real y publicación, con destino y evidencia. No marques las últimas fases por haber generado el ZIP.

## Entradas y salidas

- `canvas/silabo.json`: sílabo transcrito según [silabo.md](silabo.md).
- `hub/src/course.json`: clave estable del aula, nombre del archivo y catálogo de unidades. Mantén `key` estable durante el período.
- `canvas/exportado/*.imscc`: exportación autorizada del curso con la plantilla institucional, antes de aplicar este generador. Se selecciona la de modificación más reciente. Debe conservar las páginas Inicio y Presentación y los metadatos institucionales.
- En ausencia de exportación, se usa `canvas/plantilla/plantilla-uti.imscc`; el resultado requiere revisión de posibles duplicados en un curso ya poblado.
- `canvas/fuentes/silabo.pdf`: copia pública revisada del sílabo, opcional. Deja solo un PDF en esta carpeta: el motor elige el primero por nombre.
- `autonomo/<archivo>.html`, PDFs en `materiales/unidad-N/` y videos locales terminados en `videos/unidad-N/`: materiales que se empaquetan. La edición docente permanece local.

El generador produce `canvas/salida/<archivo>-canvas.imscc` y fragmentos `canvas/salida/pegar/*.html`. No sube nada a Canvas. Prepara una carpeta nueva por versión o conserva una copia de las salidas antes de regenerar; `salida/pegar/` se reemplaza.

## Secuencia de comprobación

Desde la raíz del aula:

```bash
python3 hub/build.py
node hub/tools/check.mjs --slides
python3 hub/tools/pdfs.py
python3 hub/tools/autonomo.py
python3 canvas/validar_silabo.py
python3 canvas/generar_canvas.py
python3 canvas/verificar_paquete.py
```

No ejecutes el generador si falla la validación anterior. Usa `--sin-videos` cuando se entreguen aparte. `--solo-es` omite adjuntos EN; no traduce ni convierte el aula bilingüe y no corresponde a la entrega bilingüe normal.

Revisa manualmente páginas, rúbricas, adjuntos y navegación del paquete, además de sus XML. La verificación local no acredita importación en Canvas ni equivalencia visual después de que Canvas procese el HTML. La cuota real la establece el curso: los umbrales de 450/480 MB de los scripts son advertencias orientativas, no una garantía institucional.

## Qué transforma y qué requiere revisión

La página Inicio conserva su contenido institucional, pero al comienzo se incrusta el aula interactiva a todo el ancho (85 % de la altura de la pantalla, mínimo 640 px), con botones para abrirla en una pestaña nueva, ver cómo usarla y descargarla. Así el estudiante la encuentra de lleno al entrar al curso. Se completa Presentación, se crean páginas por momento y sesión y una página de recursos por sesión. Las guías prácticas generan tareas inicialmente sin publicar; las evidencias de momentos usan tareas Actividad N. Se incluyen la página del aula, los materiales y una guía docente oculta. Las rúbricas se muestran como tablas HTML, no se crean como instrumentos nativos de SpeedGrader; el docente debe configurarlos si los necesita.

Las actividades heredadas conservan configuraciones de la plantilla que deben revisarse: puntajes, grupos, fechas y publicación. Las nuevas evidencias usan puntos declarados en el momento; sin ellos quedan sin calificar. No infieras ponderaciones. Las prácticas usan `puntos` cuando se declara. Los cuestionarios del aula son autoevaluaciones locales: no transfieren notas a Canvas ni se convierten automáticamente en New Quizzes.

El motor actual mantiene las páginas institucionales de Canvas en español. El aula interactiva y los PDF/videos producidos en ambos idiomas aportan ES/EN; `--solo-es` controla los adjuntos. No declares toda la interfaz de Canvas traducida. Para cumplir ES/EN en las páginas y tareas, aplica el paso de traducción siguiente.

## Actualizaciones y pegado manual

No prometas reimportación sin duplicados. Aunque los IDs nuevos son estables, la correspondencia depende del curso de destino y de su exportación; una reimportación puede sustituir contenido. Conserva la exportación original de entrada y usa un curso de prueba para confirmar el comportamiento. No uses como nueva base una exportación ya transformada por este generador sin comprobar compatibilidad: no es un proceso de ida y vuelta garantizado.

Los fragmentos de `pegar/` necesitan `curso.canvas_id` real, las páginas de destino y los archivos ya cargados con las rutas previstas. No son una migración completa: no crean tareas, módulos ni archivos. Los enlaces a actividades pueden apuntar a la lista de tareas y necesitar ajuste a la tarea concreta. Pide al docente que pegue el fragmento en la vista HTML y revise los enlaces guardados; no le pidas que programe. Canvas filtra las etiquetas permitidas al guardar. [Guía oficial del editor HTML](https://community.instructure.com/en/kb/articles/662912-how-do-i-use-the-html-view-in-the-rich-content-editor).

## Evidencia de cierre

Registra en `ESTADO.md`: comandos y resultados, avisos pendientes, archivo y tamaño de entrega, origen de la plantilla, si el contenido está traducido, si se importó realmente y quién comprobó la vista estudiante. No marques importado por haber generado un ZIP válido.

## Actualizar por la API de Canvas

Cuando el curso ya tiene la plantilla institucional, importar el `.imscc` duplica páginas que el docente quizá no puede borrar. `canvas/canvas_api.py` aplica el mismo paquete por la API de Canvas:

```bash
python3 canvas/canvas_api.py configurar --curso https://indoamerica.instructure.com/courses/12345
python3 canvas/canvas_api.py token        # lo ejecuta el DOCENTE en su terminal (entrada oculta)
python3 canvas/canvas_api.py comprobar    # solo lectura: permisos, conteos de inscritos, inventario → canvas/api/inventario.json
python3 canvas/canvas_api.py plan         # solo lectura → canvas/api/plan.json
python3 canvas/canvas_api.py aplicar      # respaldo privado del curso y aplicación; luego verifica
python3 canvas/canvas_api.py verificar    # solo lectura: enlaces, marcas pendientes, aula en Inicio
```

- **Emparejamiento:** archivos por carpeta, nombre y tamaño (reutiliza los iguales); páginas por `canvas/api/mapa.json`, URL o título; tareas por mapa o nombre base («Actividad 1 · …» = «Actividad 1»); módulos por mapa, título o «Momento N». Lo que no existe se crea.
- **Páginas:** al cambiar el título, Canvas puede asignar otra URL y rechazar la antigua en los módulos; la herramienta usa siempre la URL devuelta. Las nuevas se crean sin publicar y toman la publicación del paquete al final. Las del paquete sin publicar y sin uso se despublican y salen de los módulos; no se borran.
- **Inicio:** no se reemplaza. Solo se antepone (o se renueva) el bloque del aula incrustada.
- **Tareas:** las nuevas se crean sin publicar; las existentes conservan puntos y publicación. Publicar un módulo publica en Canvas lo que contiene: la herramienta retira los elementos antes de publicarlo y al final devuelve cada tarea a su estado previo (incidencia real observada en el piloto: tareas visibles unos minutos).
- **Cuestionarios:** se enlazan por título si ya existen en el curso (por ejemplo, la encuesta institucional); no se crean por API.
- **Bloqueos:** `aplicar` se niega si quedan marcas que verían los estudiantes (`[COMPLETAR…]`, `correo@indoamerica.edu.ec`, «Agregar los RA…», «Copiar pegar del sílabo»), salvo `--permitir-pendientes` con acuerdo del docente. Para los RA de los demás proyectos del PIS, usa `pis_ra` en `canvas/silabo.json`.
- **Privacidad y registro:** el token se lee de `CANVAS_TOKEN` o `~/.config/aula-uti/canvas-token` (permisos 600), nunca del aula, y no se imprime. Las inscripciones se cuentan por tipo, sin nombres. `canvas/api/operaciones.jsonl` registra método, ruta y estado de cada escritura (sin contenido). El respaldo del curso va a `canvas/api/privado/` (excluido de respaldos, git y entregas).
- **Alcance probado:** suite con un Canvas ficticio en memoria (URL que cambia al renombrar, módulos que publican su contenido, carga en tres pasos) y un curso real de Indoamérica actualizado con la versión anterior específica del piloto. Esto no certifica otras configuraciones institucionales: revisa siempre en Vista de estudiante.

## Traducción de páginas y tareas

El asistente ejecuta:

```bash
python3 canvas/traducir_paquete.py canvas/salida/ARCHIVO-canvas.imscc --inventario
# El asistente completa canvas/traducciones.en.json, no el docente.
python3 canvas/traducir_paquete.py canvas/salida/ARCHIVO-canvas.imscc
python3 canvas/verificar_paquete.py canvas/salida/ARCHIVO-canvas-bilingue.imscc
```

El inventario contiene `pages` (páginas publicadas, incluida Inicio), `assignments` (tareas incluso sin publicar) y `modules` (módulos activos). Cada entrada conserva la fuente, `source_sha256` y campos vacíos `title` y, para contenido, `html`. El asistente traduce fielmente el título y el cuerpo, conservando los enlaces especiales y datos académicos; no sustituye el español oficial. Las páginas ocultas que luego se publiquen necesitan un nuevo inventario.

La aplicación exige cobertura y hashes vigentes, crea un paquete `-bilingue.imscc` separado e integra secciones Español/English sin JavaScript. Inicio conserva su cuerpo español, ahora acompañado de inglés; el aula incrustada al comienzo (bilingüe por sí misma) queda una sola vez, encima de ambas secciones, y no se traduce. El generador base conserva byte a byte el resto de Inicio. Los títulos de módulos y recursos se acompañan en inglés; la interfaz propia de Canvas depende del idioma del usuario.

Si cambia la fuente, el inventario conserva la traducción anterior y añade `current_source`. Revisa la traducción y reemplaza conscientemente `source_sha256` por el hash actual después de cotejarla. No copies hashes para eludir la revisión. Las comprobaciones automáticas verifican cobertura, no calidad lingüística. Los fragmentos `pegar/` son la salida española del generador base; para pegado bilingüe usa el cuerpo correspondiente del paquete final y revisa enlaces en Canvas.
