# Problemas conocidos

Revisión local del 2026-11-13. Estos defectos están pendientes en la versión inicial.

1. **Caché de extracción:** después de extraer un documento y moverlo a `fuentes/privado`, `scripts/fuentes.py` conserva su copia textual anterior en `fuentes/_texto`. Retira esa copia antes de continuar; el script debe reconciliar su caché con las fuentes actuales.
2. **Orden de PowerPoint:** el extractor ordena `slideN.xml` por nombre físico, en vez de seguir las relaciones y el orden declarado por la presentación. Una presentación reordenada puede recibir numeración incorrecta. La asociación de notas también debe resolver las relaciones.
3. **Colisión de guías Canvas:** IDs distintos como `PR 1` y `PR-1`, con documentos llamados `guia.txt`, generan el mismo nombre de destino. La segunda guía reemplaza la primera. Usa IDs alfanuméricos diferenciados como `PR1` y `PR2` hasta corregir la comprobación de colisiones.

Las 12 regresiones existentes no cubren estos tres casos. La validación local tampoco certifica una importación efectiva en Canvas ni la calidad pedagógica de las traducciones.
