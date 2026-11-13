# Animaciones, Three.js y otras skills

El modelo mínimo está en `hub/src/js/anim/a1-1-olvido.js`; el contrato completo de `Stage` está en `hub/src/js/components/10-stage.js`. Usa esa API para conservar escenas, controles, recorrido guiado, impresión y cambio de idioma. Sigue `AGENTS.md` del aula.

## Elegir la herramienta

Usa 2D para gráficos, procesos y relaciones cuando sea suficiente. Para geometría espacial, agrega Three.js con `python3 hub/tools/vendor.py three` y `"vendor": ["three"]` en `hub/src/course.json`. El script descarga una versión fija y el compilador la incrusta; esa descarga inicial requiere internet. No uses CDN, modelos, texturas o fuentes remotas en el aula terminada. Conserva las licencias de las bibliotecas.

Dentro de Stage, renderiza Three.js en un lienzo propio y copia su imagen al contexto 2D en `draw`; mantén el tamaño, libera recursos al reconstruir y contempla equipos sin WebGL con un esquema estático explicativo. No llames al modelo 3D verificado solo porque carga la biblioteca: prueba la escena, controles y captura PDF.

Si otra skill, como `anatomy`, ayuda a producir una figura, descubre si está instalada y lee sus instrucciones antes de usarla. No presupongas sus herramientas ni la instales silenciosamente. Si falta, puedes construir una figura equivalente con las herramientas disponibles y registrar la elección. Mantén la identidad UTI y las exigencias de accesibilidad aunque la otra skill tenga otro estilo predeterminado.

## Figura autónoma

Guarda el HTML completo en `hub/src/figuras/F2.1.html`; si contiene texto, usa `F2.1.es.html` y `F2.1.en.html`. Incrústalo con `<!--@@figura:F2.1 alto=520 titulo="Figura"@@-->`. El compilador usa `srcdoc`: incluye dentro de cada figura sus dependencias. Revisa el título accesible en ambos idiomas y verifica que no dependa de rutas relativas internas al iframe.

## Criterio de terminación

- Cálculo o simulación reproducible; unidades, parámetros y límites declarados.
- Valores de escena, métricas y explicaciones derivados del mismo estado, sin cifras decorativas.
- Escenas con explicación, controles útiles, reinicio y enlaces a teoría y práctica.
- Texto ES/EN, tokens UTI, teclado, contraste y reducción de movimiento.
- Prueba en presentación compacta, página completa, móvil y PDF. Una figura externa puede necesitar una captura estática específica para impresión.
- `node hub/tools/check.mjs --slides` y `node hub/tools/anim-e2e.mjs`, más inspección de capturas. Los tests Stage no certifican por sí solos figuras arbitrarias en iframes.
