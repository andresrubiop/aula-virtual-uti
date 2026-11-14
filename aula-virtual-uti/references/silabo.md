# El sílabo en datos

El usuario confirmó el 2026-11-13 que el formato/template del sílabo de FSO es básicamente común a todos los proyectos formativos. Úsalo como referencia estructural para identificar secciones y tablas; confirma la versión y las diferencias de cada documento recibido. La referencia local consultada es `Documents/FSO/canvas-fso/fuentes/Silabo_FSO_B26.pdf` (hash en `procedencia.md`), con presentación del proyecto formativo, momentos, evaluación y bibliografía. Esa ruta documenta la procedencia y no es una dependencia de instalación. Conserva el formato común y transcribe los datos académicos del sílabo vigente de cada proyecto, incluidas las guías prácticas cuando aparezcan anexas.

`canvas/silabo.json` es una transcripción estructurada del sílabo vigente, no una propuesta curricular. Usa `silabo-ejemplo.json` de esta carpeta únicamente para conocer la forma y probar el motor: sus datos son ficticios. La unidad demostrativa sobre repaso no sustituye una unidad del curso real.

## Preparación y trazabilidad

1. Conserva los documentos originales en `fuentes/`. Ejecuta el inventario y contrasta el texto extraído con el PDF o las diapositivas, especialmente tablas y rúbricas.
2. Identifica versión, período, aprobación y páginas del sílabo vigente. Usa presentaciones y sílabos antiguos para contenido complementario; documenta discrepancias sin sustituir silenciosamente el vigente.
3. Registra en `_fuente` las rutas relativas, páginas y SHA-256 de los documentos consultados. Puede ser un objeto: el motor no lo publica. No incluyas datos personales innecesarios.
4. Completa el JSON y `PLANIFICACION.md`. Registra las dudas con `[COMPLETAR: motivo]`; no inventes fechas, horas, competencias, rúbricas ni bibliografía para pasar la validación.
5. Comprueba manualmente la correspondencia sílabo → momentos/sesiones → unidades → guías → evidencias. Ejecuta después `python3 canvas/validar_silabo.py` desde la carpeta del aula. Un resultado sin errores no acredita fidelidad al documento.

## Estructura exacta

Los nombres son sensibles a mayúsculas y tildes. Las fechas son cadenas `dd/mm/aaaa`. Las listas contienen textos, salvo las tablas indicadas. No uses objetos `{es, en}` en campos que esperan texto: el esquema de Canvas conserva el español del sílabo; la traducción pedagógica del aula vive en `hub/src/content/` y `course.json`.

| Campo | Forma y uso |
|---|---|
| `_fuente` | Metadatos libres de procedencia, sin publicación automática. |
| `curso` | Objeto con `nombre`, `periodo`, `inicio`, `fin` obligatorios. `canvas_id`: número real de la URL del curso, como texto; necesario para enlaces de `salida/pegar/`, no para generar el paquete. `bienvenida`: texto o HTML mínimo revisado. `horas`: objeto numérico con `docente`, `practico`, `autonomo`. |
| `docente` | `nombre` obligatorio; `email`, `grado`, `orcid` textos opcionales y `posgrado` lista de textos. Publica solo información autorizada. |
| `competencia_perfil`, `competencia_pf`, `metacompetencia`, `contribucion`, `reto`, `producto_final` | Textos obligatorios, transcritos del sílabo. |
| `problema` | Texto o lista de párrafos. Si es lista, no puede estar vacía. |
| `habilidades` | Lista de textos; inclúyela siempre porque el generador accede al campo directamente, aunque el validador no lo exige. |
| `ejes` | Lista de pares `[nombre, descripción]`; puede estar vacía si falta información. |
| `ra` | Lista de filas `[id, texto del resultado, evidencia]`. ID estable, por ejemplo `RA1`. No usar diccionarios. |
| `pis`, `aporte_pis` | Textos cuando el documento declare PIS. Si no aparece, omite o deja vacío y registra la consulta pendiente; no inventes un PIS para evitar un aviso. |
| `metodologias` | Lista no vacía de textos: primero la metodología principal, luego las complementarias. |
| `rubrica_final` | Lista de filas de seis textos: indicador, Receptivo, Resolutivo, Reflexivo, Crítico, Cocreativo. |
| `bibliografia` | Lista de pares `[referencia APA, URL]`; URL puede ser `""`. Verifica la existencia y correspondencia de cada referencia. |
| `momentos` | Lista no vacía de objetos, numerados consecutivamente desde 1. |
| `practicas` | Lista de guías/actividades práctico-experimentales, una tarea por objeto. |
| `no_publicar` | Lista de cadenas cuya aparición en el HTML del paquete debe detener la generación. No es un detector completo de datos personales ni inspecciona PDFs. Prefiere retirar los datos privados de las fuentes públicas. |

Otros datos del sílabo —por ejemplo `curso.codigo`, `creditos`, `nivel`, `unidad`, `horario`, `correquisitos`— pueden conservarse para trazabilidad, pero no todos se renderizan automáticamente. Actualiza también los campos correspondientes de `course.json` y el contenido del aula.

### Momentos y sesiones

Cada momento contiene `n` (entero), `titulo`, `fechas` (`dd/mm/aaaa al dd/mm/aaaa`), `ra` (lista de IDs), `evidencia`, `sesiones` y, cuando existan, `rubrica`, `recursos`, `ia`, `proposito`, `entregables`, `condiciones`. Estos últimos pueden ser texto o lista de textos, salvo `rubrica`, que usa las mismas filas de seis columnas que `rubrica_final`.

Cada sesión contiene:

- `n`: número consecutivo desde 1 dentro del momento.
- `desde`, `hasta`: fechas inclusivas, cronológicas entre sesiones; el validador actual rechaza sesiones solapadas, incluso en la misma fecha.
- `tema`: texto breve.
- `docente`, `practico`, `autonomo`, `contenidos`: texto o lista de textos.
- `horas`: números en `docente`, `practico`, `autonomo`; no escribas `"2 h"`.
- `aula`: objeto opcional que vincula los recursos, con la forma siguiente.

```json
{"unidad": 1, "manual": "M1 §1–3", "anims": ["A1.1"], "videos": ["V1.1"]}
```

`unidad` admite entero o lista de enteros. Una evaluación puede usar `{"repaso": [1, 2]}` sin crear una unidad nueva. Si no hay asociación explícita, se usan `moment` y `sessions` de cada unidad en `hub/src/course.json`. `manual` es una etiqueta, no un enlace a una sección. `anims` y `videos` restringen los recursos; si se omiten, el motor toma los de la unidad. Verifica sus IDs: un ID desconocido puede ser descartado sin error.

### Guías prácticas

| Campo | Forma y efecto |
|---|---|
| `id`, `titulo` | Textos; ID único, estable y preferiblemente el de la guía (`PR1`, `GP1`, `LAB1`). |
| `momento`, `sesion` | Enteros que deben existir en `momentos`. |
| `unidad` | Entero de una unidad existente, para enlazar la práctica del aula y su PDF. |
| `ra` | Lista de IDs de resultados de aprendizaje. |
| `proposito`, `entregable`, `evaluacion` | Texto o lista de textos. La evaluación puede remitir a la rúbrica del momento; no crea una rúbrica nativa de Canvas. |
| `archivo` | Ruta relativa desde la raíz del aula a la guía original autorizada, por ejemplo `fuentes/guias-practicas/GP1.pdf`. Se adjunta al paquete y será pública. Omítela si la guía está integrada en el sílabo. |
| `puntos` | Número positivo si consta en el sílabo; omitido o 0 genera una práctica sin calificación. No inventes un puntaje. |

Si la guía está dentro del sílabo, registra sus páginas en la trazabilidad y produce el recurso del aula sin inventar un archivo original separado. Conserva propósito, procedimiento, materiales, evidencia y rúbrica de la guía, y registra cualquier complemento propuesto. Las guías pueden compartir nombre base: el empaquetado antepone el ID y una huella estable del ID original. Los IDs de práctica deben ser únicos; si dos destinos todavía coinciden, se detiene la generación en lugar de sobrescribir archivos.

## Límites de la comprobación

El validador comprueba parte de la estructura y de las correspondencias. No valida tipos exhaustivamente, la veracidad curricular, todos los rangos de fechas de los momentos, permisos de publicación ni la traducción. La suma de horas y varias ausencias son avisos. Revisa todos los avisos antes de declarar entrega final; si la información no existe, conserva el pendiente y explica su impacto.
