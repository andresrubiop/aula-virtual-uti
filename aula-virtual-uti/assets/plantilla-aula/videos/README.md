# Videos del aula

Los videos opcionales se preparan para **NotebookLM** con una cuenta propia del docente que tenga acceso, preferentemente institucional, a partir del manual y la práctica de cada unidad. Duración orientativa del guion: 5 a 8 minutos por idea; el resultado requiere revisión.

**Idioma:** cada video se genera **una sola vez, en inglés**, y lleva **subtítulos en español** (y en inglés). Así se usa una sola generación de la cuota por video y el estudiante practica el inglés técnico. Solo si el docente lo pide se genera además el audio en español (`--idiomas es,en`).

Pregunta al inicio si el docente tiene cuenta y desea usarla. El docente inicia sesión directamente en el servicio; no solicites contraseñas, códigos, cookies ni tokens. Antes de subir archivos o generar, presenta las fuentes concretas, cuaderno y videos/idiomas y comprueba autorización. Si falta acceso o cuota, entrega los guiones y continúa con el aula.

1. **Guion:** `videos/guiones/V#.#.md` (título `# V1.1 · Título | Title`, y los apartados `## prompt es` y `## prompt en`). La guía común es `guiones/guia.md`.
2. **Fuentes:** los PDF de la unidad (`python3 hub/build.py && python3 hub/tools/pdfs.py N`).
3. **Generar:**
   - Sin instalar nada: `python3 videos/generar_videos.py --manual V1.1` imprime los pasos para hacerlo en notebooklm.google.com.
   - Automático: `python3 videos/generar_videos.py V1.1` (solo inglés; necesita la herramienta `nlm` con la sesión del docente: `nlm login`).
4. **Revisar:** el docente mira el video completo y coteja cifras, nombres y conceptos con el manual. Si hay un error, se regenera añadiendo al final del prompt: `Corrige: no digas X; según el manual, lo correcto es Y.`
5. **Subtítulos:** `python3 hub/tools/subtitulos.py transcribir V1.1` (o `uv run --with faster-whisper python3 hub/tools/subtitulos.py transcribir V1.1`) transcribe el audio inglés en el equipo (faster-whisper) y arma las frases con sus tiempos. `python3 hub/tools/subtitulos.py ver V1.1` las lista como «N|texto»: el asistente las traduce fielmente al español en `videos/subtitulos/V1.1.es.txt` (misma numeración) y corrige el inglés en `V1.1.json` si la transcripción falló. El docente revisa la traducción.
6. **Al aula:** `python3 hub/tools/video_cards.py videos/bruto/V1.1.en.mp4` (portada y cierre UTI, póster, registro), `python3 hub/tools/subtitulos.py vtt V1.1` y `python3 hub/build.py`. Con el aula en español, el reproductor muestra el video inglés con los subtítulos en español activados.

Los MP4 no se versionan. `videos/unidad-N/V#.#.en.mp4` (y `.es.mp4` si se pidió audio en español) es el que usan el aula y Canvas, con `V#.#.en.es.vtt`, `V#.#.en.en.vtt` y `V#.#.en.subs.js`; `bruto/` guarda las descargas. `videos/subtitulos/` (frases y traducciones) sí se versiona.
