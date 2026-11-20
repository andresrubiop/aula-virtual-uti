# Cambios de la skill aula-virtual-uti

La versión instalada figura en `SKILL.md` (`metadata.version`) y la muestra `python3 scripts/entorno.py`. Cada aula guarda en `control/VERSION_SKILL` la versión con la que se creó o actualizó. Para pasar un aula existente a la versión instalada: `python3 <skill>/scripts/actualizar_aula.py <aula>` (ver la guía de uso, sección 3).

## 0.12.2 · 2026-11-20

- Al inicio el asistente pregunta también cómo llevar el aula a Canvas (API con token del docente o importación del `.imscc`) y el enlace del curso; lo registra en ESTADO.md y, si es la API, configura el curso y comprueba acceso y permisos en solo lectura.
- El token de Canvas se pega en el chat (lo más sencillo para el docente): el asistente lo guarda al momento fuera del aula con `canvas_api.py token --stdin`, no lo repite ni lo escribe en archivos, y recuerda revocarlo al terminar porque queda en el historial de la conversación.

## 0.12.1 · 2026-11-20

- **Licencia CC BY 4.0** (`LICENCIA.md`, también en `SKILL.md`), con las excepciones de terceros: logos y plantilla Canvas de la UTI, KaTeX (MIT), fuentes Poppins y JetBrains Mono (SIL OFL 1.1).
- **Guía de uso y PDF al día** para compartir con otros docentes: actualización de Canvas por API con token propio, videos en inglés con subtítulos en español, revisión de calidad, accesibilidad y glosario, nuevos problemas comunes. «Problemas conocidos» actualizado.

## 0.12.0 · 2026-11-19

- **Documentación y distribución:** versión visible en `SKILL.md`, en `entorno.py` y en cada aula; este registro de cambios; `scripts/actualizar_aula.py` para llevar las herramientas de un aula a la versión instalada con vista previa y copia de lo reemplazado; la guía de uso tiene una sola fuente (la de la skill) y la del repositorio y el PDF se generan y comprueban desde ella.

## 0.11.0 · 2026-11-19

- **Glosario ES/EN:** `control/glosario.py` propone términos y revisa que cada uno se traduzca igual en el aula, los cuestionarios, `course.json`, las traducciones de Canvas y los subtítulos.
- **Videos:** el panel del docente muestra el estado de cada video (guion, en NotebookLM, descargado, en el aula, subtítulos en español).

## 0.10.0 · 2026-11-19

- **Calidad pedagógica:** `control/calidad.py` comprueba por unidad RA y evidencia, ejemplos, práctica con rúbrica de cinco niveles y desafío con IA, cuestionario con retroalimentación por opción y marcas pendientes; deja la lista de revisión para el docente.
- **Accesibilidad:** `hub/tools/accesibilidad.mjs` revisa contraste AA, alternativas, nombres de controles, foco con teclado, subtítulos y «reducir movimiento» en ES/EN y tema claro/oscuro. Contraste de la plantilla corregido (`--ink-3`, `--c2-texto`).

## 0.9 · descartada

- Pruebas automáticas en macOS y Windows: descartadas por decisión del autor.

## 0.8.0 · 2026-11-18 a 2026-11-19

- **Canvas por API:** `canvas/canvas_api.py` actualiza un curso existente sin importar el `.imscc` (plan de solo lectura, respaldo privado, sin duplicados, tareas nuevas sin publicar, verificación de enlaces).
- Aula interactiva incrustada a todo el ancho al comienzo de la página Inicio de Canvas.
- Videos: por omisión un solo video en inglés con subtítulos en español (transcripción local).
- `pis_ra` en el sílabo en datos; perfil docente sin teléfono ni ORCID ajeno.

## 0.7.1 · 2026-11-18

- Respaldos: una copia dañada se repara al crear otro respaldo y una restauración que falla a mitad devuelve todo como estaba.

## 0.7.0 · 2026-11-16

- Respaldos por hitos y recuperación del aula (`control/respaldo.py`), con restauración transaccional.

## 0.6.0 · 2026-11-14

- Panel local de avance para el docente (`control/panel.py` → `PANEL.html`).

## 0.5.0 · 2026-11-14

- Ficha del sílabo: cada dato transcrito con su página para que el docente lo coteje.

## 0.4.0 · 2026-11-14

- Cobertura curricular: matriz de RA, temas, prácticas y evaluaciones frente a las unidades.

## 0.3.0 · 2026-11-13

- Actualización por cambios: análisis de impacto y orden de actualización conservando correcciones.

## 0.2.0 · 2026-11-13

- Estado verificable: huellas de entregables y evidencias en ESTADO.md.

## 0.1.1 · 2026-11-13

- Correcciones: caché de textos extraídos, orden y notas de diapositivas PPTX, nombres repetidos de guías en Canvas.

## 0.1.0 · 2026-11-13

- Primera versión pública: aula local ES/EN con identidad UTI, PDF, animaciones, paquete Canvas, videos opcionales y guía de uso.
