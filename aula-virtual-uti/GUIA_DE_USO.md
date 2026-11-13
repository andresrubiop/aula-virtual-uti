# Guía del profesor: del sílabo al aula en Canvas

Esta guía explica cómo trabajar con **Claude Code o Codex en tu computadora**. Elige uno; puedes cambiar después porque ambos retoman el mismo `ESTADO.md`. No necesitas programar. El asistente realiza los comandos de construcción y tú revisas las decisiones académicas.

El aula conserva la estructura y el stack de FSO: presentaciones HTML embebidas, manuales, prácticas y actividades ES/EN. Los PDF se exportan desde el HTML. El formato del sílabo de FSO sirve de referencia; manda el sílabo vigente de tu materia.

## Recorrido

1. [Crear la carpeta y reunir documentos](#1-crear-la-carpeta-y-reunir-documentos).
2. [Instalar Claude Code o Codex](#2-instalar-claude-code-o-codex).
3. [Descargar y cargar la skill](#3-descargar-y-cargar-la-skill).
4. [Pedir el trabajo](#4-pedir-el-trabajo).
5. [Trabajar por fases durante varios días](#5-trabajar-por-fases-durante-varios-días).
6. [Conectar Google y producir videos](#6-conectar-google-y-producir-videos).
7. [Revisar la entrega](#7-revisar-la-entrega).
8. [Importar en Canvas Indoamérica](#8-importar-en-canvas-indoamérica).
9. [Resolver problemas comunes](#9-resolver-problemas-comunes).

## 1. Crear la carpeta y reunir documentos

Con el explorador de archivos de Linux, Finder de macOS o Explorador de Windows, crea una carpeta como **MiAula-B26** dentro de Documentos. Dentro, crea `insumos` y las siguientes subcarpetas. Puedes copiar y pegar archivos normalmente.

```text
MiAula-B26/
  insumos/
    silabo-vigente/
    silabos-anteriores/
    presentaciones/
    guias-practicas/
    lecturas/
    otros/
  requisitos-del-aula.md
```

Coloca el sílabo actual en `silabo-vigente`, claramente identificado. Añade presentaciones PPTX/PDF, guías, lecturas, bibliografía, imágenes propias y documentación que consideres importante. Conserva los originales en su ubicación habitual. Aclara si las guías están dentro del sílabo, si hay varias versiones y cuál prevalece.

`requisitos-del-aula.md` es una nota opcional de texto: nombre de materia, período, público, qué quieres lograr, materiales indispensables, necesidades de accesibilidad y preferencias para videos. Puedes usar un `.txt` si te resulta más cómodo. No incluyas contraseñas, listas de estudiantes ni notas privadas en los insumos. Los asistentes pueden procesar documentos mediante sus servicios en línea: usa materiales autorizados para ese fin.

**No crees ni llenes todavía la subcarpeta `aula`.** El asistente la generará dentro de `MiAula-B26`, separada de tus insumos. El generador necesita un destino nuevo o vacío y no debe sobrescribir documentos.

## 2. Instalar Claude Code o Codex

Necesitas conexión para trabajar con el asistente y una cuenta con acceso al producto elegido. La cuenta de Claude/ChatGPT es distinta de la de Google para videos y de la cuenta institucional de Canvas. El aula terminada podrá usarse localmente sin conexión; crearla con IA requiere el servicio correspondiente.

### Opción A: Claude Code

Abre Terminal en Linux/macOS o PowerShell en Windows y usa el instalador oficial:

Linux o macOS:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Windows, PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

También puedes seguir la [instalación oficial de Claude Code](https://code.claude.com/docs/en/setup). En Windows se recomienda Git for Windows para las herramientas Bash. Si el equipo está administrado, sigue el procedimiento de instalación de soporte institucional.

Cierra y vuelve a abrir la terminal. Escribe `claude --version` para verificar y luego `claude` desde tu carpeta de trabajo. Completa el inicio de sesión que te muestre el programa en el navegador. No compartas la contraseña con el asistente.

### Opción B: Codex

Instala [Node.js](https://nodejs.org/en/download), versión 22 o posterior para las herramientas de este proyecto. En Terminal o PowerShell ejecuta:

```text
npm install -g @openai/codex
codex --version
```

Abre Codex con `codex` desde tu carpeta de trabajo y elige el inicio de sesión con ChatGPT cuando se ofrezca. La [guía oficial de Codex CLI](https://learn.chatgpt.com/docs/codex/cli) incluye también instaladores independientes para Linux, macOS y Windows.

### Herramientas del aula

El asistente comprobará Python 3.10 o posterior, Node 22 o posterior y Chrome/Chromium para las comprobaciones y PDF. Si falta Python, usa [python.org](https://www.python.org/downloads/) o el gestor habitual de tu sistema. En Windows comprueba con `py -3 --version`; en Linux/macOS, con `python3 --version`. El asistente adaptará los comandos al ejecutable disponible. La extracción de PDF y los videos pueden necesitar herramientas adicionales; instala solo las que se vayan a usar.

La implementación se probó en Linux. Estas instrucciones contemplan macOS y Windows, pero el asistente debe comprobar compilación, rutas y PDF en tu equipo antes de declararlos validados. Si usas WSL en Windows, abre el asistente y mantén los archivos y dependencias en ese mismo entorno.

## 3. Descargar y cargar la skill

1. Abre el [repositorio público](https://github.com/andresrubiop/aula-virtual-uti).
2. Descarga [aula-virtual-uti.skill](https://github.com/andresrubiop/aula-virtual-uti/raw/refs/heads/main/dist/aula-virtual-uti.skill). Es un ZIP: si tu descompresor no reconoce `.skill`, renombra una **copia** a `.zip` y extráela. En Windows activa la vista de extensiones para no crear por error un nombre terminado en `.zip.skill`.
3. Localiza la carpeta extraída que contiene `SKILL.md`, `GUIA_DE_USO.md`, `scripts`, `references` y `assets`. Copia esa carpeta completa, no solo el Markdown.
4. Crea las carpetas de instalación dentro de `MiAula-B26` según el asistente elegido:

| Asistente | Ubicación final que debes comprobar |
|---|---|
| Claude Code | `MiAula-B26/.claude/skills/aula-virtual-uti/SKILL.md` |
| Codex | `MiAula-B26/.agents/skills/aula-virtual-uti/SKILL.md` |

Puedes instalar ambas copias si vas a alternar. Actualízalas juntas cuando descargues otra versión. Las carpetas que comienzan con punto pueden estar ocultas: Linux suele mostrarlas con `Ctrl+H`, macOS con `Cmd+Shift+.`. En Windows puedes crearlas desde PowerShell con `New-Item -ItemType Directory -Force .claude/skills` o `.agents/skills`, estando dentro de `MiAula-B26`.

No anides dos veces `aula-virtual-uti`. Si descargaste **Code → Download ZIP**, entra primero en la carpeta del repositorio y busca dentro la carpeta de la skill.

Las ubicaciones siguen la documentación de [skills de Claude Code](https://code.claude.com/docs/en/skills) y [skills de Codex](https://learn.chatgpt.com/docs/build-skills). Reinicia el asistente después de instalar para comprobar que la reconoce.

## 4. Pedir el trabajo

Abre una terminal **en MiAula-B26**. Puedes escribir `cd `, arrastrar la carpeta a la terminal y pulsar Enter, o usar una ruta entre comillas:

```text
cd "/ruta/a/MiAula-B26"
```

En Windows, por ejemplo: `cd "C:\Users\TuUsuario\Documents\MiAula-B26"`. Sustituye la ruta por la real; Documentos puede estar en otra ubicación. Ejecuta **uno** de estos programas:

```text
claude
```

```text
codex
```

Acepta el acceso a la carpeta del proyecto que has elegido. En Claude Code puedes invocar `/aula-virtual-uti`. En Codex puedes mencionar `$aula-virtual-uti` en el mensaje; la petición en lenguaje natural de abajo también identifica la skill. Escribe el mensaje **dentro del asistente**, no como comando del sistema.

> Usa la skill aula-virtual-uti instalada en esta carpeta. Quiero crear el aula de [materia], período [período]. Lee insumos/ y requisitos-del-aula.md si existe. El sílabo vigente está en insumos/silabo-vigente/; revisa también las guías y documentos complementarios. Crea el producto en la subcarpeta nueva aula/. Conserva estructura y stack FSO, presentaciones HTML embebidas y contenidos ES/EN. Trabaja por fases: hoy verifica el entorno, inventaría los insumos y señala dudas. Registra avances y el próximo paso en aula/ESTADO.md cuando crees el aula; antes usa un estado provisional en esta carpeta. Pregúntame por NotebookLM y prepara después una unidad piloto para mi revisión. No subas fuentes ni publiques el curso hasta que revisemos la operación concreta.

Si no reconoce la skill, indica: «Lee `.claude/skills/aula-virtual-uti/SKILL.md` y sigue sus instrucciones» o la ruta equivalente `.agents/skills/...`.

Para revisar la propuesta puedes responder: «Apruebo la planificación de las unidades 1 y 2; cambia la práctica de la unidad 3 según esta guía». El asistente debe conservar esa decisión, las dudas restantes y sus fuentes. Los datos ambiguos se marcan para completar; no se inventan para avanzar.

## 5. Trabajar por fases durante varios días

No es necesario terminar todo en una conversación. El siguiente orden permite revisar el aula progresivamente; cada fase puede ocupar más de una sesión.

| Fase | Qué realiza el asistente | Qué revisas tú |
|---|---|---|
| 0. Entorno y carpeta | Comprueba herramientas y crea `aula/`. | Materia, período y ubicación. |
| 1. Insumos | Inventario, versiones, guías incluidas y faltantes. | Documento vigente y dudas. |
| 2. Sílabo | Transcripción trazable, RA, sesiones y evaluación. | Fidelidad al documento. |
| 3. Planificación | Mapa de unidades, actividades y evidencias. | Propuesta académica. |
| 4. Piloto | Una unidad completa HTML ES/EN. | Diseño, contenido y práctica. |
| 5. Desarrollo | Completa las unidades con el patrón aprobado. | Avances por unidad. |
| 6. Verificación | Aula local, presentación, PDF y carpeta portátil. | Recorrido y materiales. |
| 7. Videos opcionales | Fuentes, guiones, generación y montaje. | Fuentes a enviar y resultado. |
| 8. Canvas | Paquete final bilingüe y comprobaciones locales. | Entregable y curso de destino. |
| 9. Importación | Acompaña la prueba y registra lo observado. | Curso de ensayo y vista estudiante. |

**`aula/ESTADO.md` es el registro principal.** El asistente lo actualiza al completar un hito, antes de una operación externa y antes de cerrar o agotar la sesión. Guarda fase actual, trabajo terminado con evidencia, unidad en curso, decisiones aprobadas, archivos modificados, dudas, pruebas y siguiente acción exacta. `PLANIFICACION.md` guarda el diseño académico; `ESTADO.md` guarda el avance real.

Antes de cerrar escribe:

> Guarda el avance en aula/ESTADO.md: qué completaste, qué falta, decisiones, pruebas realizadas, trabajo en curso y el primer paso concreto para continuar mañana. No marques como terminado lo que todavía no revisamos.

Al día siguiente, abre de nuevo **MiAula-B26**, ejecuta `claude` o `codex` y escribe:

> Retoma el aula existente. Lee aula/ESTADO.md, aula/AGENTS.md y aula/PLANIFICACION.md. Comprueba los archivos del último hito y continúa desde el punto de reanudación. Conserva los avances y no recrees el aula ni repitas decisiones ya resueltas.

No ejecutes dos asistentes modificando el mismo aula a la vez. Para cambiar de Claude a Codex, pide guardar el estado, cierra la sesión y abre el otro en la misma carpeta. Haz una copia de seguridad de `MiAula-B26` al terminar cada jornada. Si se interrumpió inesperadamente, pide contrastar los archivos con el último estado antes de continuar. El cierre del chat no deja al asistente trabajando por sí solo.

## 6. Conectar Google y producir videos

El asistente preguntará si tienes cuenta de NotebookLM y quieres videos. Usa una cuenta propia con acceso, preferentemente institucional. La documentación de Google puede mostrar el nombre **Gemini Notebook**. Iniciar sesión en Google no conecta automáticamente esa cuenta con Claude Code o Codex, y una conexión de Drive no acredita acceso a generar videos.

### Camino guiado: iniciar sesión tú en el navegador

1. Abre [NotebookLM](https://notebooklm.google.com/) y entra con tu cuenta de Google. Si hay varias, comprueba el perfil seleccionado; completa tú la verificación de acceso. Si tu institución no habilitó el servicio, consulta a soporte o continúa sin videos.
2. El asistente preparará PDF públicos de la unidad y guiones ES/EN. Revisa la lista exacta de fuentes y acuerda cuáles pueden enviarse.
3. Crea un cuaderno para la materia o unidad y añade esas fuentes. En **Studio**, selecciona **Resumen de video**, personaliza idioma e instrucciones con el guion preparado y genera.
4. Revisa el resultado completo, descarga el video y colócalo en `aula/videos/bruto/` con el nombre que indique el asistente, por ejemplo `V1.1.es.mp4`. Repite para inglés si corresponde.
5. Pide integrar los archivos, añadir identidad UTI, recompilar y registrar el resultado.

Consulta las guías oficiales de [crear un cuaderno](https://support.google.com/notebooklm/answer/16206563?hl=es) y [generar videos](https://support.google.com/notebooklm/answer/16454555?hl=es). Los controles, acceso y cuota pueden variar; una generación puede tardar y requiere revisión.

### Automatización opcional con el asistente

Pide: «Comprueba si hay una herramienta NotebookLM compatible en este equipo; si la hay, acompáñame a iniciar sesión y muéstrame fuentes, cuaderno y videos antes de generar».

La skill incluye un adaptador para la CLI de terceros `nlm`. El asistente comprobará versión y ayuda antes de instalarla o usarla. Para la versión compatible, el docente inicia sesión mediante `nlm login --profile uti`; luego el asistente puede ejecutar el adaptador con ese perfil y autorización. No hay un botón universal de conexión Google común a ambos asistentes. Si una integración ofrece OAuth, inicia sesión y acepta sus permisos en la página del proveedor; no pegues contraseñas, cookies, tokens ni códigos en el chat.

El modo autenticado aún requiere validación real. Si falla, usa el camino guiado. Los trabajos pendientes se registran en `videos/estado.json` y se resumen en `ESTADO.md`; antes de reintentar una generación incierta hay que comprobar si ya terminó. Puedes completar el aula con guiones y dejar videos pendientes. Consulta [la referencia técnica de videos](references/videos.md).

## 7. Revisar la entrega

Pide al asistente enlaces a los archivos reales y un resumen de lo probado y pendiente.

| Dentro de `aula/` | Para qué sirve |
|---|---|
| `hub/dist/index.html` | Edición estudiantil; ábrela dentro del proyecto. |
| `hub/dist/profesor.html` | Edición docente, que puede contener material reservado. |
| `autonomo/<archivo>.html` | Aula en un solo HTML, sin MP4 incrustados. |
| `autonomo/paquete/` | Carpeta portátil de estudiantes; se comparte completa. |
| `materiales/unidad-N/` | PDF exportados desde las presentaciones y contenidos HTML. |
| `canvas/salida/<archivo>-canvas-bilingue.imscc` | Paquete final cuando se completó el paso de traducción Canvas. |
| `ESTADO.md` | Estado real, evidencias, pendientes y versión entregada. |

Comprueba español e inglés, navegación, presentaciones, animaciones, manuales, prácticas, fechas, puntajes y vínculos. Un paquete que conserve `[COMPLETAR]` o traducciones faltantes sigue siendo un borrador. El asistente debe indicar exactamente qué `.imscc` entregar; no elijas uno solo por su fecha.

## 8. Importar en Canvas Indoamérica

### Preparar la operación

Entra al [acceso institucional de Canvas](https://indoamerica.instructure.com/login/saml) y completa tú el acceso institucional. Ese enlace fue proporcionado para este proyecto; no se ha certificado una sesión SAML ni una importación real desde esta skill. Selecciona el curso y período correctos, con permisos de profesor. Usa primero un curso de ensayo; si no lo tienes o no aparecen las opciones, solicita apoyo institucional.

Si el curso ya tiene material, conserva un export original antes de importar y comparte con el asistente únicamente el paquete autorizado que necesita como base. Revisa con él qué contenido se incorporará y el efecto sobre lo existente. No hagas importaciones repetidas suponiendo que evitarán duplicados.

### Importar el paquete

1. En el curso abre **Configuración / Settings → Importar contenido del curso / Import Course Content**.
2. Selecciona **Paquete de exportación de curso Canvas / Canvas Course Export Package**.
3. Elige el `.imscc` final indicado por el asistente. No lo descomprimas ni subas el archivo `.skill`.
4. Decide entre todo el contenido o contenido específico. En un curso existente, revisa la selección; si eliges contenido específico, completa la selección cuando Canvas la solicite.
5. Revisa las opciones de fechas antes de importar; confirma el calendario del período.
6. Inicia la importación, espera su resultado y revisa los avisos o incidencias.

Los nombres de los controles dependen del idioma y la configuración. Consulta la [guía oficial de importación](https://community.instructure.com/en/kb/articles/660728-how-do-i-import-a-canvas-course-export-package).

### Revisar antes de publicar

Abre Inicio, módulos, sesiones, tareas, PDF, videos y enlaces al aula. Comprueba fechas y puntajes, y usa Vista del estudiante para detectar recursos inaccesibles. Las tareas pueden quedar sin publicar para revisión. Las rúbricas HTML no son rúbricas nativas del libro de calificaciones.

El aula HTML contiene JavaScript: pegarla en una página de Canvas puede alterar su funcionamiento. Usa los recursos y enlaces que prepara el paquete; verifica el archivo descargado en un navegador y la experiencia dentro de Canvas. Si Canvas limita la previsualización, conserva la descarga de la edición estudiantil; no publiques en un alojamiento externo sin decidirlo expresamente.

Publica solo los elementos aprobados y comunica al asistente el resultado. Pídele registrar curso, fecha, nombre/hash del paquete, problemas encontrados y comprobaciones reales en `ESTADO.md`. El paquete local validado y la importación verificada son hitos distintos. Si deseas automatizar la importación, autoriza antes el curso y la operación concreta; esta guía no presupone acceso automático.

## 9. Resolver problemas comunes

| Situación | Qué hacer o pedir |
|---|---|
| No aparece la skill | Comprueba ruta, carpeta completa y `SKILL.md`; reinicia y pide leerlo explícitamente. |
| «Destino no vacío» | Conserva los insumos en `insumos/` y usa una subcarpeta nueva `aula/`; no borres documentos para resolverlo. |
| Falta Python, Node o navegador | Pide el diagnóstico y la instalación adecuada a tu sistema; no declares PDF comprobados antes de producirlos. |
| No está el estado después de cambiar de asistente | Abre la misma carpeta y busca `aula/ESTADO.md`; si falta, reconstruye desde archivos verificados. |
| NotebookLM no permite generar | Comprueba cuenta, acceso y cuota; conserva guiones y sigue con el aula. |
| Canvas muestra errores o duplicados | Detén nuevas importaciones, conserva el informe y revisa con el asistente o soporte. |

Instrucciones contrastadas con documentación oficial el 2026-11-13. La guía no sustituye las políticas de acceso de tu institución. Para límites técnicos de esta versión consulta [problemas conocidos del proyecto](https://github.com/andresrubiop/aula-virtual-uti/blob/main/KNOWN_ISSUES.md).
