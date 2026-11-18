# Respaldos por hitos y recuperación (mejora 7)

`control/respaldo.py` guarda versiones recuperables del aula y permite volver a un respaldo o al último resultado revisado. **Los documentos originales del docente nunca se sobrescriben ni se retiran.**

Los respaldos se guardan en `respaldos/`, dentro de la carpeta del aula. Cada hito es un manifiesto en `respaldos/hitos/` que contiene la fecha, el tipo, el motivo, la unidad, las huellas de cada archivo y la vigencia de las evidencias en ese momento. Cada versión de archivo se guarda comprimida una sola vez en `respaldos/objetos/`. Así, el primer respaldo ocupa lo que ocupa el aula comprimida, unos 10 MB en la plantilla, y los siguientes solo suman lo que cambió.

## Cuándo crear un respaldo

| Momento | Comando |
|---|---|
| Antes de un cambio amplio: rehacer o reorganizar una unidad, aplicar un plan de `impacto` que afecta varias entregas, cambiar la estructura de `course.json` o del sílabo en datos, o transformar la plantilla con los documentos reales | `crear --tipo antes --motivo "…"` |
| Justo después de registrar la aprobación docente de una unidad, de la planificación o de la ficha | `crear --tipo aprobado --unidad U2 --motivo "…"` |
| Cuando el docente lo pide | `crear --motivo "…"` (tipo `manual`) |

El respaldo de tipo `aprobado` se crea **después** de `estado.py registrar`, para que guarde exactamente los archivos con las huellas aprobadas. Si no hay ninguna evidencia vigente con aprobación, la herramienta lo avisa, porque el rótulo solo expresa lo que indicó el docente.

```bash
python3 control/respaldo.py crear --tipo antes --motivo "Antes de rehacer la unidad 2"
python3 control/respaldo.py crear --tipo aprobado --unidad U2 --motivo "Unidad 2 aprobada por el docente"
python3 control/respaldo.py listar
```

## Volver atrás

Primero mira qué cambió y después restaura. Sin `--aplicar`, `restaurar` solo muestra el plan.

```bash
python3 control/respaldo.py comparar ultimo-aprobado --ruta hub/src/content/u2
python3 control/respaldo.py restaurar ultimo-aprobado --ruta hub/src/content/u2            # vista previa
python3 control/respaldo.py restaurar ultimo-aprobado --ruta hub/src/content/u2 --aplicar
```

- **A qué respaldo volver:** a uno por su nombre, a `ultimo` o a `ultimo-aprobado`.
- **Hasta dónde:** `--ruta` limita la restauración a un archivo o una carpeta y se puede repetir. Sin `--ruta`, abarca todo el aula.
- **Qué hace al restaurar:** vuelve a dejar los archivos que cambiaron o se borraron como estaban en el respaldo. También retira los archivos de trabajo creados después dentro del alcance, como una unidad nueva.
- **Qué no toca:** las salidas generadas que no tienen copia en el respaldo, como `hub/dist/`, `autonomo/` o el `.imscc`. Esas se regeneran.
- **Respaldo de seguridad:** antes de aplicar, se crea automáticamente un respaldo de tipo `seguridad` con el estado actual. Para deshacer la restauración, se restaura ese respaldo; su nombre aparece en la salida.

### Volver al último resultado revisado

```bash
python3 control/respaldo.py restaurar --evidencia u2-revision            # vista previa
python3 control/respaldo.py restaurar --evidencia u2-revision --aplicar
```

Devuelve los entregables, los informes de prueba y los archivos de aprobación de ese registro de `ESTADO.md` a las huellas que se registraron. Busca cada versión por su huella en cualquier respaldo. Si falta alguna copia, no aplica nada y lo indica; por eso conviene crear el respaldo `aprobado` justo después de registrar. Las fuentes del registro no se restauran. Si cambiaron, la evidencia seguirá pendiente hasta revisarla con las fuentes actuales.

## Qué se guarda y qué no

| Clase | Rutas | En el respaldo | Al restaurar |
|---|---|---|---|
| Trabajo | `hub/src/`, `hub/tools/`, `practicas/`, `materiales/`, `videos/guiones/`, `canvas/silabo.json`, `control/` (mapas, informes de prueba), `PLANIFICACION.md`, `ESTADO.md`, `fuentes/INVENTARIO.md`, etc. | Copia completa | Se restaura; los nuevos se retiran |
| Originales del docente | `fuentes/`, `canvas/fuentes/`, `canvas/exportado/` | Solo la huella | **Nunca** se tocan; se avisa si cambiaron |
| Salidas generadas | `hub/dist/`, `autonomo/`, `canvas/salida/`, `videos/bruto/`, videos y audio | Solo si una evidencia de ESTADO.md las cita | Se restauran si tienen copia; si no, se regeneran |
| Excluido | `fuentes/privado/` y toda carpeta `privado`, archivos y carpetas ocultos (salvo `.gitignore`), `.env*`, credenciales conocidas, enlaces simbólicos, cachés, `fuentes/_texto/`, informes derivados (`control/VERIFICACION_ESTADO.md`, `IMPACTO.md`, `COBERTURA.md`, `FICHA_SILABO.*`, `PANEL.html`) | No | No |

`ESTADO.md` se guarda en cada respaldo, pero `restaurar` no lo reemplaza, para no perder fases, decisiones ni evidencias posteriores. Solo con `--incluir-estado`, y únicamente si el docente pide volver también al registro de entonces. Después de restaurar, el asistente anota en `ESTADO.md` qué se restauró, desde qué respaldo y por qué (Decisiones y Punto de reanudación). Luego ejecuta `estado.py verificar` y regenera el panel. Si se restauró `hub/src/`, recompila y regenera las entregas afectadas.

## Mantenimiento y pérdida del equipo

```bash
python3 control/respaldo.py comprobar                          # descomprime y verifica cada copia
python3 control/respaldo.py extraer NOMBRE --destino <carpeta nueva fuera del aula>
```

`comprobar` devuelve 1 si falta o está dañada alguna copia. También informa de las copias que ningún manifiesto usa, que quedan cuando se borra a mano un archivo de `respaldos/hitos/`.

`extraer` reconstruye un respaldo completo en una carpeta nueva o vacía **fuera** del aula, con `RESPALDO.json` como descripción. Sirve para revisar una versión antigua o para rehacer el aula en otro equipo. En ese caso hay que copiar aparte los documentos de `fuentes/`.

Los respaldos viven dentro del aula. Protegen contra cambios no deseados, no contra la pérdida o avería del equipo. Para eso, el docente copia la carpeta completa del aula, que incluye `respaldos/` y `fuentes/`, a otro disco o a su almacenamiento institucional.

## Códigos y garantías

- **Códigos de salida:**
  - **0:** operación hecha, o vista previa mostrada.
  - **1:** `comprobar` encontró problemas, o `restaurar --evidencia` no encontró alguna copia.
  - **2:** no se pudo completar; por ejemplo, el respaldo no existe, la ruta no está permitida o hay otro proceso en curso.
- **Escritura segura:** antes de cambiar nada se comprueban todas las copias y los destinos (por ejemplo, una carpeta que ocupa el lugar de un archivo). Cada archivo se descomprime en un temporal y se verifica su huella. Si una escritura falla a mitad de camino, los archivos ya reemplazados vuelven a su contenido anterior: no quedan restauraciones a medias.
- **Reparación:** al crear un respaldo, una copia guardada que esté dañada se reemplaza por la del original íntegro, en lugar de reutilizarla.
- **Bloqueo:** un candado (`respaldos/.respaldo.lock`) impide dos respaldos o restauraciones a la vez. No se opera mientras exista `.estado.lock`.
- **Privacidad:** las carpetas de `respaldos/` y sus copias se crean solo para el usuario del equipo, donde el sistema lo permite. `respaldos/` está en `.gitignore`, no entra en `autonomo/` ni en el paquete de Canvas, y `estado.py` no lo acepta como evidencia.

## Qué no hace

- No sube nada a la nube ni a otro equipo, y no programa respaldos automáticos. El asistente los crea en los momentos indicados.
- No fusiona ediciones: restaura archivos completos. Para conservar una parte de lo nuevo, compara antes con `comparar` y limita el alcance con `--ruta`.
- No borra respaldos antiguos. Si ocupan demasiado, el docente puede borrar manifiestos de `respaldos/hitos/` que ya no necesite. Las copias huérfanas se informan, pero no se eliminan.
- No aprueba fases ni certifica que un respaldo «aprobado» corresponda a una revisión real. Eso lo acredita la evidencia registrada en `ESTADO.md`.
