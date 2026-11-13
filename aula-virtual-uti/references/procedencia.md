# Procedencia y criterios de reutilización

Revisión de fuentes locales realizada el **13 de noviembre de 2026**. La skill se apoya principalmente en FSO, con patrones de MLUees y MLUnibe. Estas fuentes documentan la procedencia; sus rutas en el equipo de desarrollo no son dependencias para instalar o usar la skill.

## Qué se reutiliza y qué se adapta

| Proyecto | Evidencia consultada | Patrones aprovechados | Límites de la reutilización |
|---|---|---|---|
| FSO, UTI | `aula-fso/AGENTS.md` §§1–6; `canvas-fso/LEEME.md` | Identidad UTI, aula HTML autónoma, ES/EN, ediciones estudiante/docente, presentación vinculada a manual y práctica, animaciones con cálculos reales, PDF y guiones de videos; paquete Canvas con aula, recursos, momentos y sesiones. | La skill generaliza el curso: no fija nueve unidades, laboratorios en C, Ubuntu, número de sesiones, ID del curso ni datos del docente. FR/CA/JA quedan fuera del alcance solicitado. |
| MLUees, UEES | `AGENTS.md` §§2–5 y `README.md` | Arquitectura del motor, componentes de animación y presentaciones, contenido y salidas desde archivos reales, recursos PDF, separación de soluciones y preparación de videos. | No trasladar marca UEES, códigos MIAR, pesos de evaluación, calendario, contenidos de aprendizaje automático ni configuración de Blackboard. Los notebooks son una opción para asignaturas que los necesitan. |
| MLUnibe, UNIB.E | `AGENTS.md` y `SPEC_ML_UNIBE.md` §§1–3 | Adaptación a otra institución preservando formatos; trabajo sobre copias; separación de datos privados, fuentes, entregables y estado; trazabilidad del material reutilizado. | No trasladar identidad UNIB.E, Moodle, horas, calificaciones, requisitos de IA o decisiones particulares sobre trabajo individual. Tampoco heredar autorizaciones de publicación de aquel proyecto. |

## Decisiones del encargo actual

El usuario solicitó una skill para Claude y Codex que guíe a docentes sin experiencia técnica desde el sílabo y sus materiales hasta un aula interactiva local y un archivo importable en Canvas de Indoamérica. Añadió identidad UTI, contenidos ES/EN, guías prácticas recibidas o contenidas en el sílabo, videos con cuentas educativas y posibilidad de incorporar otras skills y Three.js para animaciones.

Por ello:

1. El sílabo vigente rige datos y evaluación. Las presentaciones, guías y sílabos antiguos son insumos trazables, no reemplazos silenciosos de requisitos aprobados.
2. Confirmación explícita del usuario, 2026-11-13: las aulas deben conservar la estructura y el stack de FSO. Se mantienen HTML/CSS/JavaScript locales, compilador Python, componentes y vistas del aula; se parametrizan título, unidades, prácticas y sesiones. Las presentaciones son HTML embebido en el aula, con PDF como exportación. El formato/template del sílabo de FSO sirve como referencia común a los proyectos formativos; los datos académicos se toman del sílabo vigente de cada uno.
3. La identidad pertenece siempre a UTI. `assets/plantilla-aula/identidad-uti/tokens.css` recoge colores extraídos de logos y derivados documentados; no constituye por sí solo un manual institucional completo de marca.
4. ES/EN y funcionamiento sin conexión son criterios de aceptación de esta skill. No se atribuyen a una normativa general de todas las instituciones revisadas.
5. Las fuentes administrativas privadas, datos de estudiantes, credenciales y solucionarios reservados no se incorporan al paquete de estudiantes. El modelo de carpetas no sustituye la revisión del contenido antes de distribuirlo.
6. El paquete local no acredita una importación efectiva: una prueba en el Canvas del docente y la revisión de los videos son pasos distintos de la generación técnica de archivos.

## Fuentes y hashes

Rutas relativas a `/home/andresrubiop/` en el equipo donde se revisaron. Los hashes identifican exactamente la versión consultada y permiten detectar cambios; no implican que las fuentes externas sigan iguales.

| Fuente | SHA-256 |
|---|---|
| `Documents/CapacitaciónB26Intersemestral/ModeloEducativo.pdf` | `07ffac7d086f2300040621e1e842a3bdeeab2bcafd2a99fbd63664c5737235ff` |
| `Documents/FSO/aula-fso/AGENTS.md` | `67e7f7d724d1f153a502d5cee115954a8fca34d9bf53abc2855ddb2cd2303dc0` |
| `Documents/FSO/canvas-fso/LEEME.md` | `27141ce8369584518b3bdb6e176f642ca7b30722330d12d3208f342e93d7d99b` |
| `Documents/FSO/canvas-fso/fuentes/Silabo_FSO_B26.pdf` | `09db45e72b60a61fb46758f535ff9055ae7386c14a998b4ab23c00869b4c90ed` |
| `Documents/MLUees/AGENTS.md` | `3973bc8a278753b55314dd20a06f2b16a42df18262270db31f7cc28ac47d99b9` |
| `Documents/MLUees/README.md` | `2f2c891217a02b27d7d32d025f3dcb2661008affc55f0521319c59ac622620a8` |
| `Documents/MLUnibe/AGENTS.md` | `5c25dbfa1f69605a1072da7be44391da2600d78512f185a84aac4bd49acde953` |
| `Documents/MLUnibe/SPEC_ML_UNIBE.md` | `ba6d8306b18a80eb73d7f9ac3e05768856af33620b9728c1832021be3224fc67` |
| `skillAV/aula-virtual-uti/assets/plantilla-aula/identidad-uti/tokens.css` | `f0aa8049f38fd4f80cb72b00114be35b90a3f28a2d5637f2c9caed24091e92bd` |

La síntesis pedagógica, con páginas y límites de interpretación de la edición 2026, está en [modelo-educativo.md](modelo-educativo.md). No se incluyen copias completas de sílabos reales ni archivos administrativos de los proyectos de origen.
