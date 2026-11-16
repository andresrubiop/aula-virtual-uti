# Verificación del estado

Pide a Claude Code o Codex: «Comprueba ESTADO.md con la herramienta de estado y dime cuál es la próxima acción».

El asistente ejecuta `python3 control/estado.py verificar`. El resultado está en `control/VERIFICACION_ESTADO.md`; al cambiar archivos hay que regenerarlo. `--help` muestra los comandos. En Windows puede usarse `py -3`.

Tras una comprobación real, el asistente usa `registrar` con fase, entregables, fuentes e informe de prueba. Las huellas se guardan en **ESTADO.md**. El resto del texto y las decisiones se conservan. Una evidencia modificada o borrada, una fase lista sin respaldo y una revisión pendiente producen avisos o incidencias. Las fases no se aprueban automáticamente.

Código 0: lo registrado no presenta discrepancias; no significa aula terminada. Código 1: revisar incidencias. Código 2: no se pudo comprobar. Si existe `.estado.lock`, comprobar que no haya otro registro activo antes de retirarlo tras una interrupción.

No publiques estos informes como material del estudiante. La referencia completa está en `references/estado-verificable.md` de la skill instalada. No inventes resultados ni decisiones para registrar una fase.

## Cuando cambia un material

Pide: «Analiza el impacto del cambio y actualiza solo lo necesario, conservando mis correcciones». El asistente ejecuta `python3 control/estado.py impacto` y lee `control/IMPACTO.md`. Relaciona las fuentes sin mapa, revisa los recursos afectados en orden y vuelve a analizar después de cada comprobación. Si una fuente de un registro es entregable de otro, los cambios se propagan a sus derivados. Declara todas las entradas reales.

`impacto --cambio fuentes/lecturas/u1.pdf` anticipa un cambio sin editarlo; ejecuta de nuevo sin `--cambio` para revisar el estado real. `--json` devuelve datos para herramientas. Código 1 indica recursos afectados o fuentes sin relación; 0 no certifica cobertura; 2 indica que no se pudo analizar.

El análisis no regenera archivos, fusiona ediciones ni ejecuta operaciones remotas. Conserva el contenido actual antes de actualizar, comprueba y registra la evidencia real. Si una salida revisada no cambió, sus derivados pueden conservarse. Los ciclos se rechazan y un derivado con origen obsoleto no puede registrarse como pasado. Consulta `references/actualizacion-incremental.md` en la skill instalada.

## Cobertura del sílabo

Pide: «Muéstrame qué RA, temas y prácticas del sílabo tienen recursos revisados y qué falta». El asistente crea una vez `python3 control/cobertura.py iniciar` y ejecuta `python3 control/cobertura.py verificar`. El informe `control/COBERTURA.md` muestra todos los requisitos, incluso sin vínculos. `--json` permite leer datos estructurados.

`control/cobertura.json` contiene las relaciones con secciones HTML ES/EN y registros de revisión en ESTADO.md. No es otro tablero de estado. Un HTML existente o una compilación correcta no acreditan pertinencia académica. Los cambios en contenido, sílabo, mapa o revisión dejan evidencia pendiente. Código 0: sin faltantes detectados en las declaraciones; 1: pendientes; 2: no se pudo comprobar.

El asistente prepara los vínculos y el profesor revisa su alcance. No fabriques aprobaciones, no registres este informe como prueba y no lo distribuyas como contenido estudiantil. Guía completa: `references/cobertura.md` de la skill instalada.

## Panel de avance

Pide: «Actualiza el panel del aula y ábremelo». El asistente ejecuta `python3 control/panel.py` y escribe `PANEL.html` en la carpeta del aula. Se abre con doble clic y muestra dónde vamos, lo que espera tu decisión, fases, unidades, comprobaciones y botones para abrir el aula, la ficha, los PDF y la entrega.

El panel se deriva de ESTADO.md y de las comprobaciones de esta carpeta; no las modifica ni es otro registro. Si algo no coincide, se corrige ESTADO.md y se vuelve a generar. No se actualiza solo: la fecha y la huella de ESTADO.md figuran al pie. Código 0: panel escrito; 2: no se pudo leer ESTADO.md. No es evidencia ni material del estudiante. Guía completa: `references/panel.md` de la skill instalada.

## Respaldos y volver atrás

Pide: «Haz un respaldo antes de rehacer la unidad 2», «Guarda un respaldo: aprobé la unidad 2» o «Vuelve al último resultado aprobado de la unidad 2». El asistente ejecuta `python3 control/respaldo.py crear --tipo antes|aprobado --motivo "…"`, `listar`, `comparar` y `restaurar`. Sin `--aplicar`, `restaurar` solo muestra qué cambiaría; al aplicar guarda antes un respaldo de seguridad para poder deshacerlo. `restaurar --evidencia ID` devuelve los archivos a lo registrado en ESTADO.md.

Los respaldos quedan en `respaldos/` (un manifiesto por hito y cada versión de archivo una sola vez). Los documentos de `fuentes/` no se copian ni se restauran: solo se anotan sus huellas y se avisa si cambiaron. ESTADO.md no se reemplaza salvo pedido expreso. `comprobar` revisa que las copias estén intactas; `extraer` reconstruye un respaldo en una carpeta nueva fuera del aula. Código 0: hecho o vista previa; 1: copias dañadas o ausentes; 2: no se pudo completar. Los respaldos protegen contra cambios no deseados, no contra la pérdida del equipo: para eso copia la carpeta completa del aula a otro disco. Guía completa: `references/respaldos.md` de la skill instalada.

## Ficha del sílabo

Pide: «Prepara la ficha del sílabo y ábremela para revisarla». El asistente ejecuta `python3 control/ficha_silabo.py iniciar --documento fuentes/silabo/<sílabo vigente>`, después `completar` y `verificar`. Abre `control/FICHA_SILABO.html` con doble clic: cada dato transcrito aparece con su página y una marca (✔ localizado, ◐ cotejar a la vista, ▲ o ✖ por revisar).

`control/ficha_silabo.json` guarda las páginas y las huellas del documento y de cada dato; si cambian, la ficha lo indica. `completar` no cambia referencias existentes. Tu confirmación se registra en ESTADO.md como revisión docente; la ficha no la deduce. Código 0: todo localizado o declarado y revisión vigente; 1: pendientes; 2: no se pudo comprobar. Necesita el texto extraído por `scripts/fuentes.py` de la skill. Guía completa: `references/ficha-silabo.md` de la skill instalada.
