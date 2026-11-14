# Verificación del estado

Pide a Claude Code o Codex: «Comprueba ESTADO.md con la herramienta de estado y dime cuál es la próxima acción».

El asistente ejecuta `python3 control/estado.py verificar`. El resultado está en `control/VERIFICACION_ESTADO.md`; al cambiar archivos hay que regenerarlo. `--help` muestra los comandos. En Windows puede usarse `py -3`.

Tras una comprobación real, el asistente usa `registrar` con fase, entregables, fuentes e informe de prueba. Las huellas se guardan en **ESTADO.md**. El resto del texto y las decisiones se conservan. Una evidencia modificada o borrada, una fase lista sin respaldo y una revisión pendiente producen avisos o incidencias. Las fases no se aprueban automáticamente.

Código 0: lo registrado no presenta discrepancias; no significa aula terminada. Código 1: revisar incidencias. Código 2: no se pudo comprobar. Si existe `.estado.lock`, comprobar que no haya otro registro activo antes de retirarlo tras una interrupción.

No publiques estos informes como material del estudiante. La referencia completa está en `references/estado-verificable.md` de la skill instalada. No inventes resultados ni decisiones para registrar una fase.
