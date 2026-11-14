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
