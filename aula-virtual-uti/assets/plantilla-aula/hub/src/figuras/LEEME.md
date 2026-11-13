# Figuras interactivas autónomas

Aquí van figuras hechas fuera del motor de animaciones: un **HTML completo y sin dependencias de internet**
(por ejemplo, una figura isométrica de la skill `anatomy`, una escena de three.js o un simulador propio).

- `F2.1.html` → una sola versión. `F2.1.es.html` + `F2.1.en.html` → versión en cada idioma.
- En el contenido: `<!--@@figura:F2.1 alto=520 titulo="Motor en corte"@@-->`. `build.py` la incrusta en un
  `<iframe srcdoc>`: el aula sigue siendo un solo archivo y los estilos no chocan.
- Colores de la UTI (morado `#3C235F`, naranja `#EA600A`) y fondo claro, para que no desentone.
- Cada cifra que muestre debe salir del mismo modelo que mueve la figura (nada inventado).
