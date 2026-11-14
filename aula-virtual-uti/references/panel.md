# Panel local de avance para el profesor (mejora 6)

`PANEL.html`, en la carpeta del aula, resume en una sola página dónde va el trabajo. Muestra la fase actual y la próxima acción, lo que espera al docente, las fases, las unidades, las comprobaciones automáticas, los accesos a lo ya generado, los próximos pasos, las decisiones y las operaciones externas. El profesor la abre con doble clic, sin conexión y sin leer Markdown.

**No es otro registro.** El panel se deriva de `ESTADO.md` y de las comprobaciones existentes, y nunca las modifica. Si algo no coincide, manda `ESTADO.md`: corrígelo ahí y vuelve a generar el panel.

## Cómo pedirlo

> Actualiza el panel del aula y ábremelo.

Genéralo al cerrar cada sesión, después de guardar `ESTADO.md` y ejecutar `control/estado.py verificar`. Genéralo también cuando el profesor quiera ver el avance o antes de pedirle una revisión.

```bash
python3 control/panel.py            # escribe PANEL.html
python3 control/panel.py --json     # además imprime los datos del panel
```

En un aula creada antes de esta mejora, usa la herramienta de la skill sin recrear la carpeta:

```bash
python3 <skill>/assets/plantilla-aula/control/panel.py --aula <carpeta-del-aula>
```

Códigos de salida: **0**, panel escrito; **2**, `ESTADO.md` no existe o no se pudo leer. En ese caso `PANEL.html` se reemplaza por un aviso, para que nadie use un panel anterior como vigente. Si solo falla una parte (por ejemplo, el bloque de evidencias o la ficha), el panel se genera igual y esa tarjeta muestra «No se pudo comprobar» con el motivo.

## De dónde sale cada parte

| Parte del panel | Origen |
|---|---|
| Dónde vamos | «Punto de reanudación» de `ESTADO.md` (fase actual, próxima acción, objetivo) y la cuenta de fases marcadas ✅ |
| Lo que necesita de ti | «Preguntas pendientes para el docente», «Bloqueos o respuestas necesarias», fases ⛔ y la ficha del sílabo sin revisión docente vigente |
| Fases y Unidades | Tablas de `ESTADO.md`, con sus iconos y notas; se omiten las filas de ejemplo vacías de la plantilla |
| Comprobaciones automáticas | `estado.py verificar` e `impacto`, `ficha_silabo.py` y `cobertura.py`, en modo lectura; número de archivos MP4 en `videos/` |
| Accesos | Archivos que existen: `hub/dist/index.html` y `profesor.html`, una entrada por unidad de `hub/src/course.json` (`#/u1`…), ficha, planificación, cobertura, PDF de `materiales/`, `autonomo/`, `canvas/salida/*.imscc` y `canvas/LEEME.md` |
| Próximos pasos, Decisiones, Operaciones externas | Secciones homónimas de `ESTADO.md` |

En cada acceso, el panel indica si el archivo figura como entregable de una evidencia registrada y si esa evidencia sigue vigente. También avisa cuando un archivo es anterior a lo que lo origina: el aula compilada frente a `hub/src/`, los PDF y el aula portátil frente a la compilación, el paquete de Canvas frente al aula y al sílabo, y la ficha frente al sílabo en datos. Estos avisos comparan fechas de modificación y solo sugieren regenerar; la vigencia la dan las evidencias de `ESTADO.md`.

## Qué no hace

- No cambia `ESTADO.md`, las fases, las evidencias, la ficha, la cobertura ni ningún entregable. Solo escribe `PANEL.html`.
- No compila, no ejecuta pruebas ni generadores y no accede a Canvas, NotebookLM ni a internet. La página no carga recursos externos ni contiene scripts.
- No aprueba fases ni certifica calidad académica. Que haya un botón solo indica que el archivo existe.
- No se actualiza solo: refleja el momento en que se generó, con fecha y huella de `ESTADO.md` al pie.
- No enlaza `fuentes/` ni carpetas privadas, archivos vacíos o enlaces simbólicos. `PANEL.html` no se acepta como evidencia en `estado.py` y no forma parte del aula portátil ni del paquete de Canvas.

## Para el asistente

- Escribe en `ESTADO.md` lo que el profesor debe ver: preguntas concretas en «Preguntas pendientes», bloqueos reales en el punto de reanudación y fases ⛔ con una nota que diga qué decisión falta. El panel no inventa ni resume nada que no esté ahí.
- Mantén la tabla de unidades con los iconos de la leyenda, para que el profesor vea el avance por recurso.
- Después de generarlo, dile al profesor qué revisar primero, normalmente lo que aparece en «Lo que necesita de ti».
- El texto de `ESTADO.md` se escapa al generar la página. Solo se da formato a `código` y **negrita**.
