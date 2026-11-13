# Videos con cuenta educativa

La implementación usa NotebookLM mediante la herramienta `nlm`, o acompaña al docente en la web. La documentación actual de Google también lo denomina Gemini Notebook. Tener Gemini educativo no demuestra por sí solo disponibilidad del servicio ni de una función concreta: comprueba cuenta, acceso institucional y cuota. [Ayuda de cuentas educativas](https://support.google.com/gemininotebook/answer/16337734?hl=en).

## Preparar sin iniciar sesión

Al iniciar el aula, pregunta si el docente dispone de una cuenta de NotebookLM y desea usarla para los videos, salvo que ya lo haya respondido. Ofrece cuenta institucional con acceso, otra cuenta propia o seguir sin videos. Registra la preferencia y acompaña el inicio de sesión directo cuando corresponda; no solicites secretos ni hagas obligatorio proporcionar el correo. Antes de subir fuentes o generar, concreta perfil, cuaderno, archivos y videos/idiomas y comprueba la autorización del docente.

1. Completa manual y práctica ES/EN, exporta sus PDF y escribe `videos/guiones/V#.#.md`, con título ES | EN y apartados `## prompt es` y `## prompt en`.
2. Revisa las fuentes que se van a subir: solo guía de producción y PDF de la unidad. No incluyas el directorio de documentos originales, datos personales o edición docente.
3. `python3 videos/generar_videos.py --lista` muestra lo que existe.
4. `python3 videos/generar_videos.py --manual V1.1` imprime los pasos sin enviar nada.

## Modo guiado

El docente entra en su cuenta institucional, crea un cuaderno con esas fuentes, abre Studio y el resumen de video, elige idioma y personalización, y genera. La ubicación de controles puede variar. No prometas tiempo fijo: Google advierte que puede superar 30 minutos. Revisa el resultado completo porque puede contener errores. [Guía oficial de videos](https://support.google.com/gemininotebook/answer/16454555?hl=en).

Descarga a `videos/bruto/V1.1.es.mp4` y `V1.1.en.mp4`. El asistente procesa la identidad visual con `python3 hub/tools/video_cards.py videos/bruto/V1.1.es.mp4`, repite en EN y recompila. El prompt de color no garantiza fidelidad visual; las portadas UTI y la revisión siguen siendo necesarias.

## Modo automático opcional

La CLI de terceros `notebooklm-mcp-cli` no es una API oficial de Google. El adaptador se revisó contra `nlm 0.11.4` y la ayuda local de `nlm video create`; no se hizo una generación autenticada al preparar esta skill. Antes de usar otra versión comprueba `nlm --version` y la ayuda de los comandos. [Repositorio y guía del proveedor de la CLI](https://github.com/jacob-bd/gemini-notebook-mcp-cli).

El docente inicia sesión por el mecanismo de la CLI en su equipo. Nunca le pidas contraseñas, tokens o cookies en la conversación. Tras su autorización para subir las fuentes y generar:

```bash
nlm login --profile uti
python3 videos/generar_videos.py V1.1 --perfil uti --idiomas es,en --una-vez
```

El estado local está en `videos/estado.json`. Revisa el cuaderno antes de repetir una solicitud que haya quedado en estado incierto: podría seguir generándose y un reintento crearía otro video. Si hay fallo de autenticación, cuota o respuesta inesperada, detén los intentos y usa modo guiado; no prometas acceso ilimitado ni cambies a una cuenta ajena.

## Cierre

Registra por video idioma, fuentes, revisión docente y archivo final. Mantén los videos no generados como pendientes y entrega los guiones. El HTML autónomo de un solo archivo no transporta MP4; la carpeta `autonomo/paquete/` sí incluye los videos locales existentes. El paquete Canvas puede excluirlos con `--sin-videos` cuando convenga subirlos aparte.
