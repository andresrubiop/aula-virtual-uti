# Trabajo por fases y continuidad entre días

Un aula puede requerir varias jornadas y varios asistentes. Su continuidad depende de los archivos del proyecto, especialmente `ESTADO.md`, no del historial del chat ni de memorias privadas.

## Ubicación y arranque

Cuando el docente ya reunió documentos en una carpeta de trabajo, conserva esos insumos y crea el producto en una subcarpeta nueva o vacía, por ejemplo `aula/`. Nunca ejecutes `nuevo_aula.py` sobre la carpeta no vacía de insumos o de instalación de skills.

Antes de crear el aula, registra lo necesario en un `ESTADO.md` provisional de la carpeta de trabajo. Después de crearla, transfiere las decisiones confirmadas a `aula/ESTADO.md` y deja en el provisional un enlace al estado principal. No mantengas dos tableros divergentes. No sobrescribas el estado de otra aula o del desarrollo de la skill.

## Al iniciar una sesión

1. Localiza el aula existente y lee su `ESTADO.md`, `AGENTS.md` y `PLANIFICACION.md`. Usa `course.json` para comprobar su identidad.
2. Revisa fase, punto de reanudación, decisiones y pendientes. Comprueba los archivos y evidencias del último hito; si no coinciden, registra la discrepancia y recupera el avance real sin inventarlo.
3. Identifica cambios de sílabo o insumos desde la sesión anterior y qué entregables invalidan. Conserva las versiones necesarias para comparar.
4. Propón un objetivo acotado para la sesión y continúa el trabajo autorizado. No repitas preguntas resueltas ni regeneres un aula existente. Si hay aprobaciones académicas pendientes, avanza con tareas independientes.

## Hitos y criterio de cierre

Mantén las fases 0–9 del molde `ESTADO.md`. Una fase está terminada cuando existe su entregable y se verificó lo que le corresponde. Las fases con revisión docente requieren registrar la decisión real; el silencio no es aprobación. Videos pueden quedar como «omitidos por decisión docente» con guiones entregados. Una importación Canvas permanece pendiente hasta que haya evidencia del curso real o de ensayo.

Actualiza el estado al terminar cada unidad o hito, al cambiar de fase, antes de una operación remota y antes de finalizar o agotar el contexto. Para tareas largas, guarda puntos intermedios que permitan retomar aun si se corta la sesión.

## Información mínima en el estado

- Fecha/agente, fase actual y objetivo de la sesión.
- Entregables terminados con rutas relativas y evidencia; trabajo parcial separado.
- Decisiones confirmadas y aprobaciones con fecha y alcance; preguntas sin resolver.
- Archivos modificados y pruebas con comando, fecha, resultado y ruta de informe. Si no se ejecutaron, escribe «no ejecutado» y motivo.
- Próxima acción concreta: archivo, unidad/recurso, tarea y verificación esperada.
- Para servicios externos: operación autorizada, destino, estado e identificador necesario para verificarla. Usa alias de cuenta; no contraseñas, cookies, tokens ni códigos.
- Para entregas: versión/fecha, ruta y hash del paquete. Distingue generado, revisado, importado y publicado.

`videos/estado.json` conserva el detalle de automatización; `ESTADO.md` resume el progreso y lo enlaza. Antes de repetir un trabajo remoto de estado incierto, consulta el resultado: no generes otro video o importación a ciegas.

## Cierre y relevo

Ejecuta las comprobaciones pertinentes a lo cambiado, anota sus límites y guarda los archivos. Deja un punto de reanudación que otro asistente pueda ejecutar sin leer la conversación. Indica al docente qué abrir, qué se completó y qué queda pendiente. No prometas continuar en segundo plano después de cerrar la sesión.

Si cambia de equipo, debe trasladar la carpeta completa y conservar rutas relativas. Si cambia de asistente, primero guarda el estado y evita ediciones simultáneas del mismo aula. La copia de seguridad de cada jornada debe conservar también los archivos fuente, no solo `hub/dist/`.

## Comprobación automatizada del estado

Usa `python3 control/estado.py verificar` al retomar y cerrar; registra huellas tras comprobaciones reales con `registrar`. La evidencia permanece dentro de ESTADO.md; el informe derivado es `control/VERIFICACION_ESTADO.md`. Consulta [Estado verificable](estado-verificable.md) para comandos, fases, migración de aulas anteriores y límites. No conviertas el código 0 en una afirmación de curso terminado.
