# Estado público

2026-11-13 · Primera versión preparada para publicación por Andrès Rubio Proaño.

Producto: skill, referencias, plantilla del aula y paquete `.skill`. Arquitectura FSO, presentaciones HTML embebidas, español/inglés, funcionamiento local, exportación Canvas y videos opcionales.

La distribución se comprobó extrayéndola, creando un aula y compilando su presentación HTML. Hash vigente en `dist/validacion.json`. Las 12 regresiones disponibles cubren extracción, protección de destino, exportación Canvas e integración de traducciones. `tests/` genera sus fixtures desde el código del repositorio.

Pendientes: tres defectos reproducidos en `KNOWN_ISSUES.md`; revisión docente y piloto con documentos reales; importación en Canvas y generación de videos autenticada; comparaciones independientes con/sin skill y otros sistemas operativos. Las escenas nuevas Three.js/anatomy tampoco están certificadas. El modelo educativo consultado contiene una contradicción sobre el umbral Crítico, documentada en las referencias.

Siguiente paso técnico propuesto: corregir los problemas conocidos, añadir regresiones y reempaquetar. La plantilla demostrativa no constituye una asignatura completa.
