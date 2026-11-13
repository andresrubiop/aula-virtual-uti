# AGENTS.md — Aula virtual de {{NOMBRE}} (UTI)

Instrucciones permanentes para cualquier agente (Claude Code, Codex u otro) que trabaje en esta carpeta.
**Antes de hacer nada, lee `ESTADO.md`** (qué está hecho, qué sigue, qué espera respuesta del docente). **Al terminar tu sesión, actualízalo** (§8).
Qué se construye está en `PLANIFICACION.md`. El proceso completo y el modelo educativo están en la skill `aula-virtual-uti`.

Quien usa esta carpeta es un **docente**, no un programador: háblale en español llano, sin jerga, dile siempre qué archivo abrir con doble clic para ver el resultado y nunca le pidas editar código.

## 1. Qué es este proyecto

El aula virtual de un proyecto formativo de la Universidad Tecnológica Indoamérica, en dos entregas que salen de la misma fuente:

| Entrega | Dónde queda | Para qué |
|---|---|---|
| Aula interactiva (un solo HTML, sin conexión) | `hub/dist/index.html` (estudiantes) y `hub/dist/profesor.html` (docente, privado) | Dar la clase y estudiar: presentaciones, animaciones, manuales, prácticas, cuestionarios |
| Aula para llevar | `autonomo/` (`<archivo>.html` y `paquete/`) | Copiar a una memoria, enviar o subir a Canvas |
| PDF por unidad | `materiales/unidad-N/` | Lectura, impresión y fuente de los videos |
| Videos | `videos/unidad-N/` | «Antes de clase» y Recursos de aprendizaje de Canvas |
| Paquete de Canvas | `canvas/salida/<archivo>-canvas.imscc` | Importar en Canvas (indoamerica.instructure.com) |

Insumos del docente (solo lectura): `fuentes/` (sílabo vigente, sílabos anteriores, presentaciones, guías de prácticas, lecturas). `fuentes/privado/` no se lee nunca.

## 2. Reglas de oro

1. **Manda el sílabo vigente.** Resultados de aprendizaje, momentos, sesiones, evidencias, rúbricas, fechas y bibliografía se copian de él, no se inventan ni se «mejoran». Si algo falta o es ambiguo, se marca `[COMPLETAR: …]` y se le pregunta al docente. Los sílabos anteriores y las presentaciones viejas son materia prima, no autoridad.
2. **Modelo educativo socioformativo.** Cada unidad parte de un problema del contexto, aporta a una evidencia de desempeño y se evalúa con rúbrica conocida desde el inicio (niveles Receptivo, Resolutivo, Reflexivo, Crítico, Cocreativo), con retroalimentación y mejora. Nada de «temas» sueltos sin producto.
3. **Español e inglés siempre.** Todo texto visible existe en los dos idiomas (§5.1). Español por defecto, trato de «tú».
4. **Identidad UTI.** Colores **solo** de `identidad-uti/tokens.css` (morado `#3C235F`, naranja `#EA600A` y derivados). Logos oficiales sin alterar.
5. **Un solo archivo HTML por edición**, autocontenido y funcional **sin conexión**. Nada de CDN en tiempo de ejecución.
6. **Nada inventado.** Ni cifras, ni citas, ni referencias, ni datos del docente. Las cifras «reales» salen de ejecutar o calcular algo (y se dice qué); las ilustrativas se rotulan como tales. Cada referencia bibliográfica debe existir: la del sílabo, o una que el docente entregó.
7. **Animaciones que calculan de verdad** (§4): simulaciones o cálculos reales con controles, nunca un video disfrazado.
8. **Lo real se incrusta, no se copia.** El código y las salidas que muestra el aula vienen de `practicas/` con marcadores (§5.3).
9. **Privacidad.** Nunca listas de estudiantes, notas, cédulas ni teléfonos en el aula, en Canvas o en memorias. El teléfono del docente no se publica salvo pedido expreso.
10. **Nada sale del equipo sin pedido del docente:** no publicar en GitHub ni en servicios externos, no subir a Canvas por él, no enviar correos. Los videos se generan con *su* cuenta institucional y solo cuando lo aprueba.

## 3. Estructura

Conserva la estructura y el stack de FSO: HTML/CSS/JavaScript locales, compilador Python y verificaciones con Node/navegador. Las presentaciones son `hub/src/content/uN/30-presentacion.html` con el componente `deck`/`slide`, embebidas en el aula por `hub/build.py`; los PDF se exportan desde ese HTML. Mantén vistas por unidad, navegación, notas, pantalla completa, ES/EN y animaciones integradas. El formato del sílabo de FSO es la referencia institucional común; los datos y contenidos corresponden al sílabo vigente de este proyecto formativo.

```
AGENTS.md · CLAUDE.md · ESTADO.md · PLANIFICACION.md · README.md
fuentes/                 insumos del docente (silabo/, silabos-anteriores/, presentaciones/, guias-practicas/, lecturas/, otros/, privado/)
identidad-uti/           logos oficiales y tokens.css (fuente única de colores)
hub/
  build.py               compila → hub/dist/index.html y profesor.html (solo Python)
  config.json · VERSION
  src/course.json        datos del curso y de sus unidades (menú, cabecera, tarjetas)
  src/content/           00-inicio.html · u1/ … uN/ · 95-recursos.html
  src/js/anim/           una animación por archivo (a2-1-nombre.js)
  src/figuras/           figuras autónomas hechas con otra skill (anatomy, three.js…)
  src/data/              datos reales para las animaciones (csv, json)
  tools/                 check.mjs (verificación) · pdfs.py · autonomo.py · anim-e2e.mjs · anim-shots.mjs · deck_overflow.py · videos.py · video_cards.py · vendor.py
practicas/               archivos reales de las prácticas (código, datos, plantillas), salidas/ y desafios_ia.json
materiales/unidad-N/     PDF generados (M# manual, P# presentación, <ID> práctica; .en.pdf en inglés)
videos/                  guiones/ (guia.md, V#.#.md) · generar_videos.py · bruto/ · unidad-N/ · videos.js
canvas/                  silabo.json · validar_silabo.py · generar_canvas.py · verificar_paquete.py · plantilla/ · exportado/ · fuentes/ · salida/
```

Cada unidad (`hub/src/content/uN/`) tiene las mismas subvistas, una por archivo: `10-resumen`, `20-preparacion`, `30-presentacion`, `50-manual`, `60-practica`, `80-quiz`, `90-bibliografia` (`40-animaciones` se genera sola desde `course.json`). Cada archivo es un `<article class="sub" data-sub="…">`. La unidad 1 de la plantilla es el modelo de cada pieza.

## 4. Animaciones (componente `Stage`)

API completa en la cabecera de `hub/src/js/components/10-stage.js`; modelo mínimo: `hub/src/js/anim/a1-1-olvido.js`.

```js
(function () {
  'use strict';
  const L = Hub.i18n.L;
  Hub.anim.define({
    id: 'A2.1', title: L('Título', 'Title'), subtitle: L('…', '…'),
    theory: { label: 'M2 §2', href: '#/u2/manual/m2-2' }, practice: { label: 'PR2 · 1', href: '#/u2/practica/pr2-1' },
    controls: [{ id: 'tasa', type: 'range', label: L('Tasa', 'Rate'), min: 0, max: 10, step: 0.5, value: 5 }],
    scenes: [{ title: L('Paso 1', 'Step 1'), text: (S, api) => api.L(`… ${S.x} …`, `… ${S.x} …`), dur: 6 }],
    observe: [L('…', '…')],
    init(S, api) {}, scene(S, i, api) {}, tick(S, dt, api) {}, control(S, id, v, api) {}, draw(S, g, api) {},
  });
})();
```

**Vara de calidad** (para dar una animación por terminada): 4–8 escenas, cada una con una nota que explica lo que se ve con los valores reales del estado (es lo que lee el recorrido guiado); cálculo o simulación real (con `Hub.rng(semilla)` si hay azar); 2–6 métricas en vivo; ≥ 2 controles que rehacen el cálculo; «Qué observar»; enlaces Teoría ↔ Práctica; colores solo de `api.c`; textos en los dos idiomas; cifras con `Hub.i18n.num(x, d, idioma)`, nunca `toFixed` a secas. Funciona en claro, oscuro, dentro de una diapositiva (`data-compact`), en móvil y a pantalla completa.
En una presentación: `<div class="anim" data-anim="A2.1" data-compact data-aspect="2.85" data-print="2:4"></div>` (`data-print="escena:segundos"` es la foto que sale en el PDF; elígela con `node hub/tools/anim-shots.mjs A2.1 --slide --scenes all`).

**3D y otras skills.** Para un objeto en 3D dentro de una animación: `python3 hub/tools/vendor.py three`, `"vendor": ["three"]` en `course.json`, y en `draw` se renderiza la escena de three.js en un lienzo propio y se copia con `g.drawImage(...)` (así conserva escenas, controles y PDF). Una figura hecha completa con otra skill (por ejemplo `anatomy`: figuras isométricas interactivas) se guarda como HTML autónomo en `hub/src/figuras/F2.1.html` y se incrusta con `<!--@@figura:F2.1 alto=520 titulo="…"@@-->`. Mismas reglas: sin internet, colores UTI, cifras del mismo modelo que mueve la figura, y versión en cada idioma si tiene texto.

## 5. Convenciones de contenido

### 5.1 Idiomas
- Frases: `<span lang="es">…</span><span lang="en">…</span>`. Bloques: `<div lang="es">…</div><div lang="en">…</div>`.
- Atributos: `data-i18n='{"title": ["es", "en"]}'`. JavaScript: `L('es', 'en')`.
- Los `id` y los `data-*` de estado van en contenedores neutros, nunca dentro de un bloque de idioma (se duplicarían).
- Cuestionarios: `{"q": {"es": "…", "en": "…"}, "opts": [{"es": "…", "en": "…"}], "ans": 1, "why": [...], "tag": "M1 §1", "ref": "#/u1/manual/m1-1"}`. Cada opción lleva su «por qué».
- El build avisa si un archivo tiene distinto número de bloques `lang="es"` y `lang="en"`.

### 5.2 Rutas e identificadores
- Enlaces internos siempre `#/vista/subvista/ancla`: `#/u2/manual/m2-3`, `#/u2/practica/pr2-1`, `#/u2/animaciones/anim-A2-1`. Nunca `href="#algo"`.
- Recursos: `P#` presentación, `A#.#` animación, `M#` manual, `V#.#` video, `Q#` cuestionario, y la práctica con el identificador de `course.json` (`PR#`, o el que use el sílabo: `LAB#`, `GP#`…).
- Progreso: `<label class="check"><input type="checkbox" data-check="u2-pr2">…</label>`.

### 5.3 Bloques y marcadores
`.callout--concepto|error|practica|ia`, `.practice-link`, `.card`, `.grid--2|3|4`, `.table-wrap > table.table`, `details.fold`, `.status--listo|produccion|planificado`. Fórmulas con KaTeX (`\( … \)`, `$$ … $$`).
`<!--@@code:pr1/archivo.py@@-->` (archivo real de `practicas/`, opcional `#10-40`), `<!--@@out:pr1/archivo@@-->` (`practicas/salidas/pr1/archivo.txt`), `<!--@@desafio:PR1@@-->` (de `practicas/desafios_ia.json`), `<!--@@figura:F1.1@@-->`, `href="@@datos:ruta@@"` (archivo pequeño descargable), `<a data-material="unidad-1/M1_manual.pdf">` (PDF de `materiales/`).
Solo para la edición docente: `<!--docente--> … <!--/docente-->` (solucionarios, notas de mediación, respuestas).

### 5.4 Presentaciones
`<div class="deck" data-deck="P2" …>` con `<section class="slide">`; cada una con `<aside class="notes">` (qué decir, qué preguntar). Si vienen de una presentación del docente: mismo recorrido y ejemplos, mejorada (bilingüe, animaciones en vivo en vez de figuras estáticas), y la nota dice qué diapositiva original cubre («Original: diapositiva 12»). Lo que se omita del original se anota en `ESTADO.md`.

### 5.5 Prácticas (componente práctico-experimental)
Una guía por práctica del sílabo o de `fuentes/guias-practicas/`: propósito ligado al reto, resultado de aprendizaje, pasos, qué entregar (evidencia), rúbrica con los cinco niveles, y un **desafío con IA** declarado y verificable. Si el docente entregó la guía, se respeta su contenido y su numeración; se completa lo que falte y se le dice qué se añadió.

## 6. Compilar y verificar (obligatorio antes de dar algo por hecho)

```bash
python3 hub/build.py                       # aula → hub/dist/ (avisa de HTML o idiomas desbalanceados y de [COMPLETAR])
node hub/tools/check.mjs --slides          # recorre todas las rutas en ES y EN; falla con errores de consola o diapositivas desbordadas
node hub/tools/anim-e2e.mjs                # las animaciones: recorrido guiado, de corrido y libre
python3 hub/tools/pdfs.py [N …]            # PDF de manual, presentación y práctica (ES y EN)
python3 hub/tools/deck_overflow.py materiales/unidad-*/P*_presentacion*.pdf
python3 hub/tools/autonomo.py              # aula de un solo archivo y carpeta para llevar → autonomo/
python3 canvas/validar_silabo.py           # el sílabo en datos: errores y avisos
python3 canvas/generar_canvas.py           # paquete de Canvas → canvas/salida/   (--sin-videos · --solo-es)
python3 canvas/verificar_paquete.py        # el paquete, antes de subirlo
node hub/tools/check.mjs --routes "#/u2/animaciones" --shots     # captura en hub/tools/shots/ para mirar el resultado
```

Requisitos: Python ≥ 3.10; Node ≥ 22 y Chrome/Edge/Chromium para verificar y exportar (`CHROME=/ruta` si no lo encuentra); ffmpeg para los videos.

## 7. Estilo de código

JS sin frameworks, cada archivo un IIFE sobre `window.Hub`, `'use strict'`, sin `eval`, sin `innerHTML` con datos del usuario. CSS solo con tokens (`var(--…)`). Accesibilidad: foco visible, `aria-label` en controles icónicos, `prefers-reduced-motion`, contraste AA, `alt` en imágenes.

## 8. Protocolo de sesión

**Al empezar:** lee `ESTADO.md` y comprueba que `python3 hub/build.py` y `node hub/tools/check.mjs` pasan.
**Al terminar (siempre, aunque quede a medias):** compila y verifica; actualiza `ESTADO.md` (tablero, próximos pasos, preguntas pendientes para el docente y una entrada breve en la bitácora: fecha, agente, qué se hizo, cómo retomar). Dile al docente, en dos o tres frases, qué quedó listo, qué archivo abrir y qué necesitas de él.
