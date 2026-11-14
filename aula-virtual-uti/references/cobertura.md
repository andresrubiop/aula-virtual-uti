# Matriz de cobertura del sílabo (mejora 4)

La matriz permite revisar qué exige el sílabo y dónde se trabaja en el aula. Distingue relaciones planificadas, archivos existentes y **revisión declarada vigente**. Ninguna de ellas, por sí sola, certifica calidad pedagógica. El asistente ejecuta los comandos y prepara las relaciones; el profesor revisa lo académico sin editar JSON.

## Cómo pedirla

> Revisa la cobertura del sílabo: muestra los RA, sesiones, contenidos, prácticas y evaluaciones con sus recursos en español e inglés. Señala los faltantes y las revisiones pendientes. Conserva mis decisiones y guarda por dónde continuar.

Usa la matriz después de transcribir y validar el sílabo, al revisar la planificación, tras completar cada unidad y antes de entregar Canvas. No esperes a tener el aula completa para mostrar los vacíos.

## Preparar y consultar

Desde la carpeta del aula:

```bash
python3 canvas/validar_silabo.py
python3 control/cobertura.py iniciar
python3 control/cobertura.py verificar
```

`iniciar` crea `control/cobertura.json` con una lista vacía de vínculos y **rechaza sobrescribir** un mapa existente. Ejecútalo solo una vez. Necesita `canvas/silabo.json` y `hub/src/course.json`; no utiliza `silabo.ejemplo.json` como documento oficial. Los primeros resultados tendrán pendientes: todavía no se han declarado ni revisado recursos.

`verificar` regenera `control/COBERTURA.md`. No altera el mapa, el sílabo, los recursos ni ESTADO.md. Añade `--json` para leer el resultado estructurado. Códigos: **0** sin vacíos estructurales ni vínculos pendientes detectados; **1** faltantes o revisiones pendientes; **2** formato/rutas no comprobables. Si falla, invalida el informe anterior cuando puede escribir en su ruta. Un código 0 significa que las declaraciones pasan estas comprobaciones, no que el curso esté aprobado.

En Windows usa el ejecutable disponible, por ejemplo `py -3`. En un aula anterior ejecuta el script desde la skill instalada, sin recrear la carpeta:

```bash
python3 <skill>/assets/plantilla-aula/control/cobertura.py --aula <carpeta-del-aula> verificar
```

## Qué contiene cada fila

El catálogo se deriva del sílabo actual, aunque no haya ningún vínculo declarado:

| ID del elemento | Qué debe relacionarse |
|---|---|
| `RA/RA1` | Resultado de aprendizaje, su evidencia y las sesiones que lo trabajan. |
| `M1/S1` | Tema de la sesión 1 del momento 1. |
| `M1/S1/C1` | Primer contenido declarado de esa sesión; se genera una fila por contenido. |
| `PR/PR1` | Práctica, sesión, unidad, RA, propósito, entregable y evaluación. |
| `EV/M1` | Evidencia del momento y su rúbrica de cinco niveles. |
| `EV/FINAL` | Producto final y rúbrica final. |

Los IDs de RA/prácticas con espacios o signos se codifican en el informe; copia el ID exacto generado. Las posiciones de contenidos cambian si se reordena el sílabo, lo que obliga a revisar sus vínculos. El sílabo conserva los nombres originales.

Las unidades se toman de `sesion.aula.unidad` o `repaso`; si no se declara ninguna de esas claves, se usan `moment` y `sessions` de `course.json`. Una sesión de evaluación puede usar repaso sin crear una unidad nueva. Los RA de sesión se toman del momento, salvo lista explícita `sesion.ra`. Revisa esa excepción y conserva su correspondencia con el documento vigente.

La matriz señala RA sin sesiones, referencias a RA/unidades/sesiones inexistentes, unidades sin uso, prácticas sin relación coherente, propósitos/evidencias faltantes, rúbricas incompletas y guías originales declaradas que faltan. Para cada unidad comprueba la existencia de `30-presentacion.html` y `50-manual.html`, siguiendo FSO. **Encontrarlos no marca temas como cubiertos.**

## Relacionar contenido que se pueda revisar

El asistente edita `control/cobertura.json`, cuya forma es:

```json
{
  "version": 1,
  "vinculos": [
    {
      "elemento": "M1/S1/C1",
      "archivo": "hub/src/content/u1/50-manual.html",
      "seccion": "concepto-principal",
      "idioma": "es",
      "registro": "revision-u1",
      "nota": "La sección desarrolla el concepto con un ejemplo y una actividad revisados."
    }
  ]
}
```

Este ejemplo **no declara cobertura completa**. Cada elemento requiere vínculos revisados para **es** y **en**. Puede ser el mismo HTML bilingüe, con un vínculo por idioma, o secciones distintas. El mismo recurso puede contribuir a varios elementos si la nota explica cada relación; no copies relaciones por coincidencia de títulos.

- `archivo`: HTML estudiantil dentro de `hub/src/content/`, en una unidad asociada al elemento. El producto final puede usar contenido transversal de esa carpeta. Los PDF son exportaciones, no sustituyen el HTML del aula FSO.
- `seccion`: `id` HTML exacto de la sección, sin `#`; vacío permite revisar todo el archivo. Se rechazan IDs ausentes o repetidos. Prefiere secciones concretas para facilitar el cotejo.
- `idioma`: `es` o `en`. Se busca texto dentro del idioma correspondiente, sin contar scripts, estilos, `noscript`, bloques ocultos, plantillas HTML ni bloques `<!--docente-->`. Una marca `[COMPLETAR: …]` en ese texto deja el vínculo pendiente. Esto no detecta una traducción semánticamente incorrecta ni toda forma de ocultación CSS.
- `registro`: ID de la evidencia real de revisión en ESTADO.md. Debe incluir este HTML como entregable, el sílabo, `course.json` y el mapa de cobertura como fuentes; para prácticas con `archivo`, incluye además esa guía original como fuente. Añade el informe real de revisión como prueba. Debe declarar `--tipo docente` o incluir evidencia de aprobación; una compilación local no demuestra pertinencia académica.
- `nota`: explica qué parte del requisito respalda ese recurso. No inventes una decisión docente para llenar el campo.

Primero prepara y muestra los vínculos junto con el contenido; después registra el resultado de la revisión efectivamente realizada. Una aprobación anterior puede reutilizarse si conserva su alcance: no pidas confirmaciones ya resueltas ni atribuyas una revisión nueva al profesor. Si está pendiente, conserva el vínculo con el ID previsto: el informe lo señalará sin impedir avanzar en recursos independientes.

Ejemplo tras una revisión docente real, con archivos existentes:

```bash
python3 control/estado.py registrar revision-u1 --fase 5 --entregable hub/src/content/u1/50-manual.html --fuente canvas/silabo.json --fuente hub/src/course.json --fuente control/cobertura.json --prueba control/revision-u1.md --tipo docente --resultado pasado
python3 control/cobertura.py verificar
```

Incluye los demás recursos y fuentes realmente revisados repitiendo opciones. Para una práctica con guía original declarada añade `--fuente fuentes/guias-practicas/PR1.pdf` (su ruta real); así un cambio de la guía invalida la revisión. Para renovar un registro usa `--reemplazar` solo después de repetir la revisión pertinente. Una sola revisión puede cubrir varios recursos y elementos; su informe debe detallar alcance y pendientes. El comando guarda huellas, no solicita ni autentica la aprobación.

## Cambios y continuidad

Las huellas y dependencias se comprueban con el registro existente de **ESTADO.md**. Si cambia un recurso, el sílabo, `course.json`, el mapa o la evidencia de revisión, la declaración deja de estar vigente. Un cambio del mapa completo invalida conservadoramente las revisiones que lo usen: revisa el alcance antes de registrarlas de nuevo. No se copian estados «aprobado» dentro del mapa.

Ejecuta también `control/estado.py impacto` para ordenar las actualizaciones y `control/estado.py verificar` para contrastar fases. Guarda en ESTADO.md qué filas faltan, qué revisión necesita el profesor y el siguiente archivo/acción. El informe incluye las huellas de lo consultado; debe regenerarse tras los cambios.

No registres `control/COBERTURA.md` como prueba o fuente: se deriva del estado y produciría una referencia circular. Conserva informes reales de revisión en archivos separados. La matriz es material de trabajo docente; no se incorpora automáticamente al HTML estudiantil ni a Canvas.

## Límites

El programa no lee el PDF oficial para certificar su transcripción, no interpreta la calidad del contenido, no confirma que una rúbrica esté bien aplicada y no autentica al autor de una aprobación. La fidelidad curricular se coteja con las fuentes; las páginas de cada dato, incluidas las guías integradas en el sílabo, se cotejan en la [ficha del sílabo](ficha-silabo.md). Los recursos sin vínculos no cuentan como cobertura; las filas omitidas del mapa siguen apareciendo pendientes. No hay operaciones remotas en esta mejora.
