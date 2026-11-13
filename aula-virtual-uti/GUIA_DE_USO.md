# Guía de uso para docentes

Esta skill te acompaña para transformar el sílabo y tus materiales en un aula interactiva de Indoamérica. Tú aportas los documentos y validas las decisiones académicas; el asistente prepara los archivos y ejecuta las herramientas.

## 1. Instalar y empezar

Extrae `aula-virtual-uti.skill` como un ZIP y conserva su carpeta completa. Colócala en `.claude/skills/` para Claude Code o en `.agents/skills/` para Codex, dentro de tu proyecto. Abre una sesión nueva. Hay más detalles en [Instalación](references/instalacion.md).

Puedes empezar con este mensaje:

> Usa aula-virtual-uti. Quiero preparar el aula de [nombre de la materia] para [período]. Mis archivos están en [carpeta]. Aquí tienes el sílabo vigente, mis presentaciones y las guías prácticas. Guíame paso a paso y conserva la estructura y el stack de FSO, con presentaciones HTML embebidas.

El asistente comprobará las herramientas disponibles y te preguntará solo los datos que falten. También te preguntará si tienes una cuenta de NotebookLM y deseas usarla para los videos opcionales.

## 2. Preparar los documentos

Entrega el sílabo vigente e identifica su período. Puedes añadir sílabos anteriores, diapositivas, lecturas y guías prácticas. Indica si las guías están anexas al sílabo. El formato del sílabo de FSO sirve de referencia común; los contenidos y la evaluación se toman del documento vigente de tu materia.

El asistente organizará las copias, identificará lo que falta y preparará una planificación trazable. No necesitas editar JSON ni escribir código. Mantén listas de estudiantes, notas y documentos reservados fuera de los materiales que se usarán para crear o distribuir el aula.

## 3. Revisar una unidad piloto

El asistente preparará una unidad con presentación HTML, manual, práctica, autoevaluación, bibliografía y animaciones pertinentes, en español e inglés. Abre el archivo que te indique y revisa contenidos, instrucciones, evaluación y diseño antes de extender el patrón al resto.

Las presentaciones están dentro del aula interactiva: entra a la unidad y selecciona Presentación. Puedes recorrer las diapositivas, usar pantalla completa y consultar sus notas. Los PDF son exportaciones de esos contenidos HTML.

## 4. Usar tu cuenta de NotebookLM

Los videos son opcionales. Al comenzar, el asistente preguntará:

> ¿Tienes una cuenta de NotebookLM y quieres usarla para generar los videos? Puedes usar tu cuenta institucional si tiene acceso, otra cuenta propia con acceso o continuar sin videos por ahora.

Si aceptas, te acompañará para abrir NotebookLM e iniciar sesión directamente en el servicio. Cuando haya varias cuentas, tú eliges cuál usar. No entregues contraseñas, códigos de verificación, cookies ni tokens al asistente; no hace falta escribir tu correo en la conversación para preparar el aula.

Antes de enviar documentos, el asistente te mostrará los archivos concretos que propone subir, el cuaderno de destino y los videos/idiomas que desea generar. La autorización se aplica a esa operación; tener una sesión abierta no autoriza subir cualquier documento. Solo se enviarán materiales revisados para ese propósito.

Si no dispones de acceso, cuota o una herramienta compatible, el aula continúa y recibirás guiones y fuentes listos para usar después. El modo guiado permite que tú hagas la generación en NotebookLM; el modo automático requiere una herramienta compatible y una sesión iniciada por ti. Revisa los videos completos antes de incorporarlos al aula. Consulta [Videos](references/videos.md).

## 5. Abrir y entregar el aula

| Archivo o carpeta del aula | Uso |
|---|---|
| `hub/dist/index.html` | Aula de estudiantes dentro de la carpeta del proyecto. |
| `hub/dist/profesor.html` | Edición docente: puede contener material reservado. |
| `autonomo/<archivo>.html` | Aula en un solo HTML, con presentaciones y actividades; los MP4 van aparte. |
| `autonomo/paquete/` | Carpeta portátil para estudiantes con los recursos locales existentes; compártela completa. |
| `materiales/unidad-N/` | PDF de presentaciones, manuales y prácticas. |
| `canvas/salida/<archivo>-canvas.imscc` | Paquete para importar y revisar en Canvas. |

El asistente te dará enlaces concretos a tus entregables. Revisa una importación en un curso de ensayo antes de usar el paquete en un curso real. Comprueba fechas, puntajes, publicación y enlaces. La validación local no sustituye esa prueba.

## 6. Continuar otro día

Abre la carpeta del aula y escribe:

> Continúa desde ESTADO.md. Revisa lo que está terminado y sigue con el próximo paso pendiente.

Ese archivo conserva las decisiones, dudas, verificaciones y próximos pasos para retomar con Claude o Codex. Si cambias el sílabo o tus materiales, indícalo para actualizar la planificación, el aula y sus exportaciones.

La plantilla inicial es una demostración: las marcas `[COMPLETAR]` deben resolverse con información real antes de presentar una materia como terminada.
