# Ficha de extracción y revisión del sílabo (mejora 5)

La ficha muestra cada dato transcrito en `canvas/silabo.json` junto al documento y la página de donde salió, y comprueba en local que ese texto aparezca allí. Sirve para que el profesor coteje la transcripción antes de planificar, construir el aula y exportar a Canvas. El asistente ejecuta los comandos y ubica las páginas; el profesor revisa sin editar JSON.

Sustituye la recomendación anterior de llevar la trazabilidad a mano en `fuentes/TRAZABILIDAD.md`. Un archivo así puede conservarse como nota, pero la ficha es la que se verifica.

## Cómo pedirla

> Prepara la ficha del sílabo: cada dato con su página, lo que no encuentres en el documento y las dudas. Ábreme la ficha para revisarla.

Úsala en la fase 2, después de transcribir el sílabo y antes de aprobar la planificación. Vuelve a ejecutarla si cambia el sílabo vigente, si se corrige un dato o antes de generar el paquete de Canvas.

## Preparar y consultar

Desde la carpeta del aula, con el sílabo vigente ya copiado en `fuentes/silabo/`:

```bash
python3 <skill>/scripts/fuentes.py .                # texto por página en fuentes/_texto/
python3 canvas/validar_silabo.py
python3 control/ficha_silabo.py iniciar --documento fuentes/silabo/<sílabo vigente>.pdf
python3 control/ficha_silabo.py completar
python3 control/ficha_silabo.py verificar
```

- `iniciar` crea `control/ficha_silabo.json` con el documento principal y su huella SHA-256. **No sobrescribe** una ficha existente. Rechaza documentos fuera de `fuentes/`, en `fuentes/privado/` o en la caché `_texto/`, y exige que el texto extraído sea posterior al documento.
- `completar` propone una página **solo para los datos que todavía no tienen referencia** y cuyo texto aparece en el documento. Si un dato aparece en varias páginas, elige la más cercana en el orden de lectura del sílabo y anota las demás («También aparece en p. 6, 9»). Nunca cambia una referencia existente. Los datos que no encuentra quedan para ubicarlos a mano.
- `verificar` escribe `control/FICHA_SILABO.md` y `control/FICHA_SILABO.html`. El HTML se abre con doble clic, usa la identidad UTI, agrupa los datos por sección y se puede imprimir. No modifica el sílabo, la ficha ni `ESTADO.md`. `--json` devuelve el resultado estructurado.

Códigos: **0**, todos los datos están localizados o declarados y hay una revisión docente vigente; **1**, hay pendientes; **2**, la ficha o sus rutas no se pudieron comprobar. Si falla, el informe anterior se reemplaza por un aviso para que no se use como vigente.

En un aula anterior a esta mejora, ejecuta la herramienta desde la skill sin recrear la carpeta:

```bash
python3 <skill>/assets/plantilla-aula/control/ficha_silabo.py --aula <carpeta-del-aula> verificar
```

PDF: la página es la del PDF (salto de página del texto extraído). PowerPoint: el número de diapositiva. Word y texto: el documento completo (`"pagina": null`).

## Qué comprueba cada estado

| Estado | Significado | Qué hacer |
|---|---|---|
| ✔ Texto localizado | El dato aparece literalmente en la página (sin distinguir mayúsculas, tildes ni puntuación; fechas `dd/mm/aaaa` también como `aaaa-mm-dd`). | Cotejo rápido. |
| ✔ Palabras localizadas | Al menos el 90 % de sus palabras están en la página, en otro orden: típico de tablas en columnas. | Mirar la tabla. |
| ◐ Dato breve | Una cifra o código presente en la página. Su presencia no lo identifica. | Lo confirma la revisión docente. |
| ◐ Cotejo declarado | No coincide del todo, pero el asistente lo cotejó a la vista y dejó una nota concreta (celda partida entre páginas, guion de corte, sigla). | Leer la nota. |
| ▲ Parcial | Entre el 60 % y el 90 % de las palabras. | Cotejar: puede ser una reformulación o un error. |
| ✖ No localizado | No aparece en la página indicada; si está en otra, se sugiere. | Corregir la página o el dato. |
| ✖ Sin referencia | Falta documento o página. | Ubicarlo. |
| ▲ Dato cambiado | El dato se editó después de asignarle la página. | Volver a cotejar. |
| ✖ Documento cambiado | El sílabo cambió después de crear la ficha (otra versión). | Revisar todas las referencias. |
| ✖ COMPLETAR | El dato está vacío o marcado `[COMPLETAR]`. | Preguntar al profesor. |

Los datos que no se transcriben del sílabo no aparecen: identificadores y numeración internos, vínculos con el aula (`aula`), `canvas_id`, `bienvenida`, `no_publicar`, `_fuente`, los archivos de guías y las URL de la bibliografía.

## Ubicar o corregir a mano

El asistente edita `control/ficha_silabo.json`; el profesor no. Cada referencia tiene esta forma:

```json
{"campo": "/momentos/1/rubrica/2/4", "archivo": "fuentes/silabo/vigente.pdf", "pagina": 9,
 "valor_sha256": "<huella del dato>", "nota": "Celda que continúa en la página 10; cotejada a la vista.", "origen": "asistente"}
```

- `campo` es la ruta del dato en `canvas/silabo.json` (formato JSON Pointer).
- `valor_sha256` es el SHA-256 del texto del dato al asignar la página: si el dato cambia, la ficha lo marca.
- `origen` vale `sugerida` (la propuso `completar`), `asistente` o `docente`. Solo una nota con origen distinto de `sugerida` convierte una coincidencia parcial en «cotejo declarado». Escribe una nota concreta y verdadera; no la uses para silenciar diferencias.
- Si una guía práctica u otro dato procede de otro archivo, añade ese archivo con su huella en `documentos` y usa su ruta en `archivo`.

Corrige primero `canvas/silabo.json` cuando el dato no coincide con el documento. No copies al sílabo los textos de sílabos anteriores, presentaciones o del aula para que la ficha pase.

## Registrar la revisión docente

La ficha nunca da por revisado el sílabo por sí sola. Cuando el profesor la haya revisado y confirmado (o pedido cambios que ya aplicaste), guarda su confirmación en una nota y regístrala:

```bash
python3 control/estado.py registrar revision-silabo --fase 2 --tipo docente \
    --entregable canvas/silabo.json --fuente fuentes/silabo/<sílabo vigente>.pdf --fuente control/ficha_silabo.json \
    --prueba control/revision-silabo.md --resultado pasado
```

La revisión vale si es de tipo `docente` o trae `--aprobacion`, incluye como fuentes todos los documentos de la ficha y `control/ficha_silabo.json`, y sigue vigente. Si cambia el sílabo, el documento o la ficha, deja de valer y hay que revisar de nuevo. Los informes `FICHA_SILABO.md` y `.html` no se aceptan como evidencia porque se regeneran.

Con la revisión vigente, los datos breves presentes en su página cuentan como cotejados.

## Prueba con un sílabo real

Se probó en local con el sílabo vigente de Fundamentos de los Sistemas Operativos (PDF de 11 páginas) y su transcripción a JSON. `completar` propuso página para 304 de 328 datos; 87 aparecían en varias páginas. Otros 16 eran temas vacíos marcados COMPLETAR. Los 8 datos por ubicar a mano fueron:

- celdas de rúbrica partidas entre páginas;
- reformulaciones, como «4.º nivel» frente a «4TO NIVEL»;
- una palabra de la transcripción que no figura en el documento oficial («Pthreads»).

Esa prueba no se publica porque el documento es del docente.

## Límites

La comprobación compara palabras con el texto extraído; no lee el PDF visualmente, no hace OCR, no reconstruye tablas y no entiende el sentido del texto. Un PDF escaneado necesita una versión con texto o una transcripción revisada antes de usar la ficha. Que un dato esté «localizado» indica que sus palabras aparecen en esa página, no que pertenezca a la celda correcta. La revisión docente se declara y no se autentica. La ficha no aprueba fases, no reemplaza `validar_silabo.py` ni la matriz de cobertura, y no realiza operaciones remotas.
