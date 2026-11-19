# Glosario ES/EN y revisión terminológica (mejora 11)

El aula tiene un único glosario: la vista **Recursos → Glosario** (`hub/src/content/95-recursos.html`). Cada término es una fila:

```html
<div class="gloss__item"><dt>línea base · <em>baseline</em></dt><dd><span lang="es">Medición inicial…</span><span lang="en">Initial measurement…</span></dd></div>
```

Las variantes inglesas aceptadas se separan con barra: `<em>spaced review / spaced repetition</em>`. El buscador del aula filtra el glosario; no hace falta otra lista.

```bash
python3 control/glosario.py proponer    # candidatos y revisión → control/GLOSARIO.md
python3 control/glosario.py             # solo revisión (código 1 si un término tiene dos traducciones en el glosario)
```

## Proponer términos

`proponer` toma las negritas (`<strong>`, `<dfn>`) que tienen par en el otro idioma dentro de una frase bilingüe y descarta los rótulos («**Entrega:**»). Ordena por frecuencia. Si no hay negritas de términos, el asistente propone los términos técnicos del sílabo y del manual. En ambos casos:

1. El asistente redacta la definición en los dos idiomas a partir del manual, sin inventar.
2. El docente decide qué términos entran y revisa traducción y definición.
3. El asistente los agrega a la vista Glosario y recompila.

No agregues términos sin la decisión del docente. La terminología oficial del sílabo prevalece: si el sílabo dice «evidencia de desempeño», no la cambies por un sinónimo.

## Revisión terminológica

Para cada término del glosario se buscan todos los pares español–inglés del material:

- frases bilingües del aula (`<span lang="es">…</span><span lang="en">…</span>`) y bloques JSON de los cuestionarios;
- títulos de `hub/src/course.json`;
- traducciones de Canvas (`canvas/traducciones.en.json`);
- subtítulos de los videos (`videos/subtitulos/V#.#.json` y `V#.#.es.txt`).

Si el español usa el término y el inglés no usa su traducción (ni una variante, incluido el plural), se anota en «Para revisar». Corrige el inglés, agrega la variante si es correcta o déjalo si es una paráfrasis válida. Son avisos, no errores: la decisión es lingüística. Ejecuta la revisión después de traducir Canvas, de escribir subtítulos y antes de entregar.

## Estado de los videos

El panel del docente (`python3 control/panel.py`) muestra cada video de `videos/guiones/` con su estado según los archivos: guion listo, en NotebookLM (pedido en `videos/estado.json`), descargado, en el aula, y si tiene subtítulos en español. La revisión docente de cada video se registra en ESTADO.md; el panel no la deduce.
