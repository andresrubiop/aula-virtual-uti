# Estado público

2026-11-13 · Versión pública de Andrès Rubio Proaño; ampliación de guía docente y continuidad por fases.

Producto: skill, referencias, plantilla del aula y paquete `.skill`. Arquitectura FSO, presentaciones HTML embebidas, español/inglés, funcionamiento local, exportación Canvas y videos opcionales.

La distribución se comprobó extrayéndola, creando un aula y compilando su presentación HTML. Hash vigente en `dist/validacion.json`. Las 12 regresiones disponibles cubren extracción, protección de destino, exportación Canvas e integración de traducciones. `tests/` genera sus fixtures desde el código del repositorio.

Guía ampliada: carpeta de insumos separada de `aula/`, instalación y uso de Claude Code/Codex en Linux/macOS/Windows, carga de skill, mensajes para iniciar/reanudar, cuenta Google y videos en modo guiado o automático, importación en Canvas Indoamérica y revisión antes de publicar. Fuentes oficiales enlazadas en la guía; no se certificó acceso SAML real.

Continuidad: nuevo `references/continuidad.md` y protocolo reforzado en skill/AGENTS. El molde `ESTADO.md` incluye fase, punto de reanudación, trabajo parcial, decisiones aprobadas, pruebas, operaciones externas y relevo. Fase 0 queda pendiente de verificación para no afirmar compilación cuando se usa `--sin-compilar`.

Validación de esta ampliación: skill válida; referencias Markdown locales existentes; paquete extraído crea/compila un aula con presentación HTML; estado conserva decisiones al rechazar recreación; 12/12 regresiones PASS. Pruebas en Linux; no se ejecutaron instalaciones reales en Windows/macOS ni generación autenticada o importación Canvas.

Pendientes: tres defectos reproducidos en `KNOWN_ISSUES.md`; revisión docente y piloto con documentos reales; importación en Canvas y generación de videos autenticada; comparaciones independientes con/sin skill y otros sistemas operativos. Las escenas nuevas Three.js/anatomy tampoco están certificadas. El modelo educativo consultado contiene una contradicción sobre el umbral Crítico, documentada en las referencias.

Siguiente paso técnico propuesto: corregir los problemas conocidos, añadir regresiones y reempaquetar. La plantilla demostrativa no constituye una asignatura completa.

Guía del profesor disponible también en la raíz: `GUIA_DE_USO.md` completa y `GUIA_DE_USO.pdf` de 15 páginas. PDF con identidad UTI, índice navegable, pasos, ejemplos, comprobaciones y lista de revisión final. Generación reproducible en `tools/`; verificación de paginación, enlaces, ausencia de desbordes y revisión visual. La copia dentro de la skill se conserva para instalaciones autónomas.
