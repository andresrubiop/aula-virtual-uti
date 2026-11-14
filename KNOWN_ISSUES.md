# Problemas conocidos y correcciones

Actualizado el 2026-11-13. La mejora 1 corrige los tres defectos reproducidos en la revisión inicial:

1. **Caché de extracción:** `scripts/fuentes.py` reconstruye `fuentes/_texto/` y el inventario. Retira textos de archivos borrados, movidos a privado o que ya no se pueden extraer. La caché es una salida regenerable; conserva las anotaciones en otro archivo. Los originales no se modifican.
2. **Orden y notas de PowerPoint:** utiliza `ppt/presentation.xml` y sus relaciones para el orden; cada diapositiva resuelve sus notas mediante relaciones. Los archivos huérfanos no se presentan como diapositivas del curso. Una presentación sin relaciones válidas produce un aviso de extracción fallida, sin inventar su orden.
3. **Colisión de guías Canvas:** el nombre de distribución incluye una huella estable del ID original. `PR 1` y `PR-1` conservan sus documentos aunque ambos se llamen `guia.txt`. Una comprobación adicional detiene la generación si encuentra destinos distintos que colisionan, incluso sin distinguir mayúsculas.

Las regresiones comprueban estos casos con documentos ficticios. El cambio de nombre interno de las guías puede hacer que Canvas cree archivos nuevos al importar una actualización; prueba primero en un curso de ensayo. No se garantiza una reimportación sin duplicados.

Continúan pendientes la importación real en Canvas, la generación autenticada de videos, la revisión pedagógica y las pruebas completas en Windows/macOS. Las mejoras 2–12 se abordarán por separado; no forman parte de esta entrega.
