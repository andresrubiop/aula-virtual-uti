# Instalación y uso en Claude y Codex

Para el recorrido completo desde los documentos hasta la entrega, consulta la [Guía de uso para docentes](../GUIA_DE_USO.md), incluida en la skill.

La entrega es una carpeta `aula-virtual-uti/` con `SKILL.md`, `scripts/`, `references/` y `assets/`. Mantén la estructura completa: el generador necesita sus assets. El archivo `.skill` es un ZIP de distribución; también puede abrirse con un descompresor. No contiene cuentas ni credenciales.

## Instalación local en un proyecto

Copia la carpeta completa dentro de `.claude/skills/` para Claude Code y dentro de `.agents/skills/` para Codex, en la carpeta donde el docente vaya a iniciar su trabajo. Si ya hay una versión instalada, conserva una copia antes de actualizar. No copies solo `SKILL.md`.

En este proyecto de desarrollo ambas rutas pueden ser enlaces simbólicos a la carpeta fuente para evitar versiones divergentes. En equipos Windows sin soporte de enlaces, usa copias completas. La creación y las pruebas se verificaron en Linux; macOS y Windows requieren comprobar las dependencias con `scripts/entorno.py`.

Reinicia o vuelve a abrir la sesión para que descubra la skill. Si no aparece, indica explícitamente al asistente que lea `<ruta>/aula-virtual-uti/SKILL.md`; todas las instrucciones y herramientas funcionan también por esa vía.

## Primer mensaje del docente

> Quiero crear el aula de mi proyecto formativo para Indoamérica. Usa aula-virtual-uti. Aquí están el sílabo vigente, mis diapositivas y las guías prácticas. Guíame paso a paso y prepara el aula local y el paquete para Canvas.

No hace falta ejecutar `nuevo_aula.py` a mano: el asistente acompaña al docente y prepara los archivos. Python construye el aula; Node 22 o superior y Chrome/Edge/Chromium permiten revisar y exportar PDF. Los videos añaden dependencias opcionales.

## Retomar con Astra o Fable

Abre la carpeta del aula y escribe «Continúa desde ESTADO.md». `AGENTS.md` contiene las instrucciones comunes; `CLAUDE.md` remite a ellas. El estado conserva avances, decisiones, resultados y pendientes en texto normal, sin depender de conversaciones anteriores o memoria de un modelo.

El estado de desarrollo de esta skill está en la raíz de `skillAV`. El de cada aula se encuentra en la carpeta que se creó para ella. No los mezcles.
