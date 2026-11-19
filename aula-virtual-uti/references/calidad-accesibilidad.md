# Calidad pedagógica y accesibilidad (mejora 10)

Dos revisiones complementarias antes de dar una unidad por terminada y antes de entregar el aula. Las dos son locales: no envían nada fuera del equipo.

```bash
python3 control/calidad.py                 # piezas del modelo socioformativo por unidad → control/CALIDAD.md
node hub/tools/accesibilidad.mjs           # aula compilada, ES/EN, tema claro y oscuro → control/ACCESIBILIDAD.md
```

## Calidad pedagógica (`control/calidad.py`)

Comprueba en `hub/src/content/uN/` que cada unidad tenga lo que exige el modelo:

| Área | Comprobación | Tipo |
|---|---|---|
| Ruta | RA visibles y evidencia o producto en el resumen | obligatoria |
| Manual | ejemplos (`callout--concepto`/`practica` o «Ejemplo») | obligatoria |
| Manual | errores frecuentes (`callout--error`) | aviso |
| Práctica | pasos, qué entregar, rúbrica con Receptivo, Resolutivo, Reflexivo, Crítico y Cocreativo, desafío con IA | obligatoria |
| Evaluación | retroalimentación («por qué») en cada opción, en ES y EN, y respuesta válida | obligatoria |
| Evaluación | al menos 5 preguntas; cada una remite a la teoría | aviso |
| Presentación | nota para el docente en cada diapositiva | aviso |
| Animaciones | 4–8 escenas, «Qué observar», teoría ↔ práctica, ≥ 2 controles | aviso |
| General | sin marcas `[COMPLETAR]` | obligatoria |

Devuelve 1 si falta algo obligatorio. Es una revisión de **presencia y estructura**: no decide si un ejemplo es bueno ni si el nivel es el adecuado. Para eso, `CALIDAD.md` incluye por unidad una lista de cinco preguntas para el docente (RA y evidencia del sílabo, pertinencia de los ejemplos, alineación práctica–rúbrica–RA, preguntas que evalúan comprensión y retroalimentación útil, carga realista). El asistente le muestra la lista, corrige lo que el docente indique y registra su conformidad:

```bash
python3 control/estado.py registrar u1-calidad --fase 4 --entregable hub/src/content/u1/50-manual.html … \
  --prueba control/CALIDAD.md --aprobacion control/aprobacion-u1.txt --resultado pasado --tipo docente
```

No marques la lista por el docente ni registres una aprobación que no dio.

## Accesibilidad (`hub/tools/accesibilidad.mjs`)

Abre `hub/dist/index.html` (o `--profesor`) en el navegador y revisa cada vista en español e inglés, con tema claro y oscuro:

- **Contraste** WCAG AA de cada texto visible con su fondo real (4,5:1; 3:1 desde 24 px o 18,7 px en negrita). Los textos sobre degradados o imágenes se cuentan como «sin medir».
- **Alternativas:** imágenes con `alt` (`alt=""` solo si son decorativas); lienzos de animación con `role="img"` y `aria-label` (el componente `Stage` lo pone con `alt` o el título); SVG con nombre; iframes con `title`.
- **Nombres:** botones, enlaces y campos con nombre accesible.
- **Estructura:** un único `h1` visible por vista y sin saltos de nivel (aviso).
- **Teclado:** recorre la vista con Tab (`--tabs 40`) y exige foco visible (contorno o sombra) en cada elemento; avisa si el foco cae en algo oculto.
- **Videos:** con subtítulos (aviso).
- **Movimiento:** con «reducir movimiento» activado en el sistema, ninguna animación CSS infinita (aviso).

Opciones: `--routes "#/u1/manual,#/u1/quiz"`, `--lang es`, `--tema claro`. Devuelve 1 si hay errores. Corrige en el contenido (`alt`, `aria-label`, `title`) o en los estilos; los colores salen solo de `identidad-uti/tokens.css`:

- `--ink-3` (#6B6674) es el gris más claro admitido para texto pequeño (5,1:1 sobre el fondo).
- El naranja UTI (#EA600A, 3,4:1) es para gráficos, bordes y texto grande. Para texto pequeño sobre claro usa `--c2-texto` (#B04806, 5,6:1).

La revisión automática no sustituye probar el aula con un lector de pantalla (NVDA en Windows, VoiceOver en macOS, Orca en Linux) ni la valoración del docente. El aviso de dos `h1` en la vista de presentación corresponde a la portada de la diapositiva y no impide la lectura.

## Cuándo ejecutarlas

- Al terminar la unidad piloto y cada unidad, después de compilar: primero `calidad.py`, después `accesibilidad.mjs`.
- Antes de generar el paquete de Canvas o el aula para llevar.
- Registra el resultado técnico en `ESTADO.md` (Verificaciones) y la conformidad docente como evidencia de tipo docente. Un informe sin errores no aprueba la unidad.
