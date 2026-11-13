# Videos del aula

Los videos opcionales se preparan para **NotebookLM** con una cuenta propia del docente que tenga acceso, preferentemente institucional, a partir del manual y la práctica de cada unidad. Duración orientativa del guion: 5 a 8 minutos por idea, en español y en inglés; el resultado requiere revisión.

Pregunta al inicio si el docente tiene cuenta y desea usarla. El docente inicia sesión directamente en el servicio; no solicites contraseñas, códigos, cookies ni tokens. Antes de subir archivos o generar, presenta las fuentes concretas, cuaderno y videos/idiomas y comprueba autorización. Si falta acceso o cuota, entrega los guiones y continúa con el aula.

1. **Guion:** `videos/guiones/V#.#.md` (título `# V1.1 · Título | Title`, y los apartados `## prompt es` y `## prompt en`). La guía común es `guiones/guia.md`.
2. **Fuentes:** los PDF de la unidad (`python3 hub/build.py && python3 hub/tools/pdfs.py N`).
3. **Generar:**
   - Sin instalar nada: `python3 videos/generar_videos.py --manual V1.1` imprime los pasos para hacerlo en notebooklm.google.com.
   - Automático: `python3 videos/generar_videos.py V1.1` (necesita la herramienta `nlm` con la sesión del docente: `nlm login`).
4. **Revisar:** el docente mira el video completo y coteja cifras, nombres y conceptos con el manual. Si hay un error, se regenera añadiendo al final del prompt: `Corrige: no digas X; según el manual, lo correcto es Y.`
5. **Al aula:** `python3 hub/tools/video_cards.py videos/bruto/V1.1.es.mp4` (portada y cierre UTI, póster, registro) y `python3 hub/build.py`.

Los MP4 no se versionan. `videos/unidad-N/V#.#.es.mp4` y `.en.mp4` son los que usan el aula y Canvas; `bruto/` guarda las descargas.
