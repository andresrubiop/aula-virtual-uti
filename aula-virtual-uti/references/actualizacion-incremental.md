# Actualizar el aula cuando cambian los materiales (mejora 3)

El asistente identifica qué entregables deben revisarse y los actualiza en orden, conservando correcciones aprobadas. El mapa utiliza las evidencias del propio **ESTADO.md**; no hay un segundo registro que mantener. `control/estado.py impacto` prepara el plan, pero no edita contenido ni ejecuta generadores.

## Pedido del profesor

> Cambié la lectura de la unidad 1. Analiza qué partes del aula, traducciones, PDF y paquete Canvas quedan afectadas. Conserva mis correcciones y actualiza solo lo necesario. Guarda el avance para continuar mañana.

Al retomar, lee las decisiones y ejecuta desde el aula:

```bash
python3 control/estado.py impacto
python3 control/estado.py verificar
```

Lee `control/IMPACTO.md`: causas, orden de revisión, entregables sin impacto detectado y fuentes sin relación declarada. El informe contiene fecha y huella del estado; se regenera después de cada cambio. `verificar` comprueba además fases y punto de reanudación. Ninguno cambia las decisiones ni aprueba fases.

En Windows adapta a `py -3`. En aulas anteriores ejecuta la herramienta actual sin recrear la carpeta:

```bash
python3 <skill>/assets/plantilla-aula/control/estado.py --aula <carpeta-del-aula> impacto
```

## Declarar las relaciones con archivos reales

Un registro depende de otro cuando una de sus **fuentes** es un **entregable** del otro. Incluye todas las entradas relevantes: documentos originales, contenido HTML, traducciones, configuración, código y recursos compartidos que realmente utiliza la entrega. No basta con citar solo el sílabo para cada salida. Usa registros por recurso o unidad cuando puedan revisarse por separado; agrupa únicamente resultados que deban producirse juntos.

Ejemplo de relación, después de generar y comprobar de verdad la presentación y su PDF:

```bash
python3 control/estado.py registrar u1-presentacion --fase 5 --entregable hub/src/content/u1/30-presentacion.html --fuente fuentes/lecturas/u1.pdf --prueba control/revision-u1.txt --resultado pasado
python3 control/estado.py registrar u1-pdf --fase 6 --entregable materiales/u1.pdf --fuente hub/src/content/u1/30-presentacion.html --prueba control/revision-pdf-u1.txt --resultado pasado
```

Las rutas son ilustrativas: sustitúyelas por archivos existentes y añade los demás insumos con opciones repetidas. Los comandos guardan huellas; no crean documentos ni hacen las revisiones. Sigue [estado verificable](estado-verificable.md) para registrar decisiones docentes, pruebas remotas y fases.

Si cambia la lectura, la presentación queda pendiente y su PDF también, aunque todavía conserve sus bytes. El mismo criterio se aplica a traducciones, aula compilada y Canvas **cuando sus entradas estén registradas**. Una unidad independiente queda sin impacto detectado. Una configuración compartida afecta a todos los recursos que la declaren como fuente.

Los ciclos se rechazan antes de guardar. Revisa fuentes incorrectas o agrupa la producción conjunta; no elimines relaciones reales para ocultar una alerta. Si varios registros verifican el mismo entregable, sus consumidores dependen de todos: hay que renovar todas las comprobaciones obsoletas.

## Ejecutar el plan sin perder el trabajo

1. Lee las causas y revisa las fuentes sin relación. Una fuente nueva o no registrada exige decidir qué afecta; la herramienta no adivina su unidad ni su contenido. Registra el resultado de esa revisión con la fuente correspondiente, incluso si se decide no incorporarla, conservando el motivo en Markdown.
2. Comienza por el primer recurso pendiente cuyos orígenes ya estén revisados. Si el propio entregable cambió, compara su contenido actual con las decisiones aprobadas **antes de regenerar**. El análisis señala esas ediciones y las conserva; no identifica automáticamente quién las hizo ni las fusiona.
3. Actualiza solo el contenido necesario, respetando estructura FSO, presentaciones HTML embebidas y ES/EN. Repite las pruebas pertinentes y guarda su resultado real. Si una decisión académica cambia de alcance, obtén la revisión necesaria; reutiliza autorizaciones vigentes sin pedirlas de nuevo.
4. Renueva el registro con `registrar <id> ... --reemplazar` solo después de comprobarlo. No puede registrarse como `pasado` un derivado cuyo origen registrado siga obsoleto. Vuelve a ejecutar `impacto`: si la salida revisada no cambió, sus consumidores pueden seguir vigentes y evitar una regeneración innecesaria.
5. Cuando cambie HTML fuente, recompila el aula con `hub/build.py`. El compilador produce un HTML conjunto; actualizar selectivamente contenidos no convierte esa compilación en un motor incremental. Exporta los PDF afectados con las opciones de unidad disponibles en `hub/tools/pdfs.py --help`. Regenera y valida el paquete final si sus entradas cambiaron.
6. Repite `impacto` y `verificar`, revisa resultados y actualiza fases y punto de reanudación en ESTADO.md. Si se interrumpe la sesión, deja recurso actual, causa, prueba pendiente y siguiente acción concreta. Conservar un paquete anterior no significa que ya esté actualizado.

El plan no envía fuentes, genera videos ni importa en Canvas. Mantén esas operaciones pendientes hasta contar con la autorización correspondiente y evidencia real. Una revisión local no acredita una importación.

## Analizar un cambio antes de hacerlo

```bash
python3 control/estado.py impacto --cambio fuentes/lecturas/u1.pdf --json
```

`--cambio` puede repetirse. Simula que esas rutas cambian, además de analizar los cambios reales; no modifica archivos ni registra nuevas huellas. El informe indica el modo simulado. Una ruta propuesta sin relación se muestra como tal. Después ejecuta `impacto` sin `--cambio` para volver a la situación real.

Código **0**: no se detectó impacto ni fuentes sin relación dentro del alcance analizado; **1**: hay recursos afectados o fuentes por relacionar; **2**: no se pudo analizar por formato, ciclo o rutas. Sin registros no hay mapa: un resultado 0 no demuestra cobertura ni curso terminado. Si falla el análisis, se invalida el informe anterior cuando su ruta permite escribirlo.

No registres `control/IMPACTO.md`, `control/VERIFICACION_ESTADO.md` ni ESTADO.md como evidencia: son salidas derivadas o el propio registro. La exploración de fuentes excluye carpetas privadas, ocultas, enlaces y caché `_texto`; no lee contenido de las fuentes sin relación. Los informes son material de trabajo docente, no entregables estudiantiles.

## Límites

Se comparan archivos y relaciones declaradas, no el significado de un cambio. Una corrección de espacios también cambia la huella. Los archivos fuera de `fuentes/` no registrados requieren declararse explícitamente o revisarse por el asistente. Las dependencias omitidas no pueden detectarse; «sin impacto detectado» no certifica independencia académica. La matriz de cobertura del sílabo y la ficha de configuración pertenecen a mejoras posteriores.
