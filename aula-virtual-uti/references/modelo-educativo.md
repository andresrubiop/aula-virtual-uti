# Modelo educativo UTI: aplicación al aula

Lee esta referencia al interpretar el sílabo y preparar `PLANIFICACION.md`. Es una síntesis de la edición institucional **2026** disponible al construir la skill; no sustituye al sílabo aprobado, a sus rúbricas ni a instrucciones institucionales posteriores que entregue el docente.

## Fuente y alcance

**Universidad Tecnológica Indoamérica, Modelo Educativo, segunda edición, 2026**, ISBN 978-9942-693-22-8. Copia consultada: `Documents/CapacitaciónB26Intersemestral/ModeloEducativo.pdf` en el equipo de desarrollo. SHA-256: `07ffac7d086f2300040621e1e842a3bdeeab2bcafd2a99fbd63664c5737235ff`.

El PDF presenta dos páginas impresas por página digital. Las referencias siguientes dan primero la numeración impresa y luego la página del PDF, contada desde 1. No hace falta tener esa ruta local para usar la skill: esta síntesis viaja con ella. Si el docente proporciona otra edición, verifica sus diferencias y registra qué fuente rige el curso.

## Principios institucionales y su aplicación

| Fundamento comprobado | Fuente | Cómo aplicarlo al aula |
|---|---|---|
| El proyecto formativo (PF) articula competencia profesional, resultados de aprendizaje, créditos, horas, contenidos y perfil de egreso. | pp. 56–57; PDF 29 | Extrae esos datos del sílabo sin modificarlos; relaciona cada unidad y práctica con los RA que le corresponden. |
| Los resultados de aprendizaje expresan actuaciones profesionales, con verbo de desempeño, proceso profesional y condición de pertinencia o impacto. | pp. 57–58; PDF 29–30 | Conserva el texto oficial. Si el docente pide formular nuevos RA, distingue la propuesta de los RA aprobados; no los reemplaces por listas de temas. |
| Los PIS integran varios PF alrededor de problemas del territorio, dentro de las cargas existentes y sin sumar créditos por sí mismos. | pp. 58–59; PDF 30 | Explica el aporte del PF al PIS que conste en el sílabo. No inventes un PIS ni agregues trabajo duplicado para “cumplir” el modelo. |
| Aprendizaje activo, investigación con evidencia, colaboración y actuación frente a problemas reales o contextualizados. | pp. 81–83; PDF 41–42 | Parte de una pregunta o reto significativo; enlaza explicación, demostración y práctica con la evidencia que el estudiante elaborará. Adapta la colaboración a la modalidad del curso. |
| La evaluación valora desempeño contextualizado, reflexión, autoevaluación, coevaluación y mejora continua. | pp. 86–89; PDF 44–45 | Presenta criterios y evidencia antes de la actividad; incluye un momento de revisión y mejora. Un cuestionario de autoevaluación acompaña el proceso, pero no reemplaza por sí solo la evidencia profesional. |
| Las evidencias permiten verificar la participación del estudiante en análisis, argumentación, diseño, implementación y mejora. | pp. 88–89; PDF 45 | Solicita trazas apropiadas al campo: decisiones justificadas, cálculos, bitácora, versiones, observaciones, pruebas o defensa del producto. No exijas código en materias que no lo requieren. |
| Uso de IA con autonomía cognitiva, transparencia, análisis crítico, responsabilidad y supervisión humana. | pp. 78–80 y 88; PDF 40–41 y 45 | En las actividades con IA, pide declarar su uso y contrastar los resultados con fuentes o pruebas. Evalúa las decisiones del estudiante y la evidencia; no aceptes la salida de IA como autoridad. |

La concreción de estos principios en secciones de HTML, controles de animación o archivos de Canvas es una **decisión de diseño de la skill**, no una disposición del Modelo Educativo.

## Rúbricas y límites de interpretación

La Tabla 4, p. 90 (PDF 46), usa cinco niveles: **Receptivo, Resolutivo, Reflexivo, Crítico y Cocreativo**. En síntesis, progresan desde reconocer conceptos hasta aplicar procedimientos, relacionar teoría y práctica, analizar causas sistémicas y cocrear soluciones contextualizadas. Usa descriptores observables para la evidencia concreta, evitando cinco adjetivos genéricos que no permitan evaluar.

Si la guía o el sílabo ya incluye una rúbrica, respeta sus criterios, pesos, niveles y escala. Si falta, redacta una propuesta identificada como tal y deja pendiente su aprobación docente. No inventes ponderaciones oficiales.

**Inconsistencia de la fuente que debe conservarse como pendiente cuando afecte al curso:** la Tabla 4 sitúa “Crítico” en 8.0–8.9, pero el párrafo inmediatamente posterior menciona “nivel crítico (7/10)” para una credencial. Esta síntesis no resuelve esa contradicción. No automatices umbrales de acreditación ni cambies notas basándote en una interpretación; consulta el sílabo y, si sigue siendo necesario, pide confirmación institucional. La skill produce recursos didácticos, no concede credenciales.

## Guías prácticas del docente

Las guías pueden estar en `fuentes/guias-practicas/` o dentro del sílabo. Inventaría ambas ubicaciones para evitar omisiones o prácticas duplicadas. Conserva el identificador, propósito, procedimiento, entregable y rúbrica originales; registra su archivo y página de origen. Los sílabos antiguos aportan material, pero no sustituyen requisitos del vigente.

Vincula cada práctica con su RA, momento y sesión, el manual y las animaciones que la preparan. Genera su versión ES/EN, PDF y tarea de Canvas a partir de la misma definición. Si la guía trae criterios sin ponderación, conserva esa ausencia y solicita el dato necesario; no asignes puntos de manera automática. Señala al docente cualquier adaptación o nuevo desafío con IA y no lo presentes como parte del documento original.

Esta organización del componente práctico-experimental es una **decisión de implementación** que materializa el enfoque de evidencias; el número, horas y requisitos de las prácticas proceden del sílabo y de las guías recibidas.

## Requisitos propios de esta skill

- **Identidad UTI y ES/EN:** requisitos expresos del encargo, no una afirmación de que el Modelo Educativo exija traducir todo material al inglés. Usa `identidad-uti/tokens.css` y los logos incluidos; no heredes marcas de UEES o UNIB.E.
- **Aula sin conexión:** HTML autónomo por edición, con fuentes y dependencias incrustadas. Videos y archivos grandes acompañan la carpeta para llevar; un enlace externo no se vuelve offline por estar en el aula.
- **Animaciones:** cálculos o simulaciones explicables con controles, valores coherentes y límites declarados. Los ejemplos ilustrativos se identifican como tales. `anatomy` o Three.js pueden apoyar una figura cuando sean pertinentes; su uso no es requisito pedagógico universal.
- **Videos:** recurso complementario con guion y fuentes verificables; revisión docente antes de considerarlos terminados. Una cuenta educativa de Gemini no garantiza por sí sola acceso, cuota o automatización de NotebookLM.

## Revisión antes de producir el resto del curso

Comprueba una unidad piloto: problema y producto reconocibles; RA del sílabo trazables; material previo utilizado o descarte explicado; práctica completa y rúbrica conocida; evidencia del trabajo propio y declaración de IA; retroalimentación y oportunidad de mejora; mismos contenidos esenciales en ES/EN; identidad UTI; ausencia de datos personales innecesarios. Registra decisiones y dudas en `PLANIFICACION.md` y `ESTADO.md`.
