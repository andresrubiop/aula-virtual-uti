# Estado público

2026-11-13 · Versión pública de Andrès Rubio Proaño; ampliación de guía docente y continuidad por fases.

Producto: skill, referencias, plantilla del aula y paquete `.skill`. Arquitectura FSO, presentaciones HTML embebidas, español/inglés, funcionamiento local, exportación Canvas y videos opcionales.

La distribución se comprobó extrayéndola, creando un aula y compilando su presentación HTML. Hash vigente en `dist/validacion.json`. Las regresiones disponibles cubren extracción, protección de destino, exportación Canvas e integración de traducciones. `tests/` genera sus fixtures desde el código del repositorio.

Guía ampliada: carpeta de insumos separada de `aula/`, instalación y uso de Claude Code/Codex en Linux/macOS/Windows, carga de skill, mensajes para iniciar/reanudar, cuenta Google y videos en modo guiado o automático, importación en Canvas Indoamérica y revisión antes de publicar. Fuentes oficiales enlazadas en la guía; no se certificó acceso SAML real.

Continuidad: nuevo `references/continuidad.md` y protocolo reforzado en skill/AGENTS. El molde `ESTADO.md` incluye fase, punto de reanudación, trabajo parcial, decisiones aprobadas, pruebas, operaciones externas y relevo. Fase 0 queda pendiente de verificación para no afirmar compilación cuando se usa `--sin-compilar`.

Validación de esta ampliación: skill válida; referencias Markdown locales existentes; paquete extraído crea/compila un aula con presentación HTML; estado conserva decisiones al rechazar recreación; 12/12 regresiones PASS. Pruebas en Linux; no se ejecutaron instalaciones reales en Windows/macOS ni generación autenticada o importación Canvas.

Pendientes: revisión docente y piloto con documentos reales; importación en Canvas y generación de videos autenticada; comparaciones independientes con/sin skill y otros sistemas operativos. Las escenas nuevas Three.js/anatomy tampoco están certificadas. El modelo educativo consultado contiene una contradicción sobre el umbral Crítico, documentada en las referencias.

Siguiente mejora propuesta: analizar cambios y entregables afectados (mejora 3), en una entrega separada a petición del usuario. La plantilla demostrativa no constituye una asignatura completa.

Guía del profesor disponible también en la raíz: `GUIA_DE_USO.md` completa y `GUIA_DE_USO.pdf` de 15 páginas. PDF con identidad UTI, índice navegable, pasos, ejemplos, comprobaciones y lista de revisión final. Generación reproducible en `tools/`; verificación de paginación, enlaces, ausencia de desbordes y revisión visual. La copia dentro de la skill se conserva para instalaciones autónomas.

Mejora 1: reparadas la caché que conservaba textos retirados, la lectura de orden/notas PPTX y las colisiones de guías Canvas. Regresiones nuevas en `tests/test_scripts.py` y `tests/test_canvas.py`: suite actual 15/15 PASS. Paquete extraído crea/compila, conserva el estado de aulas existentes y coincide con la fuente. Comparación local independiente reproduce los fallos en la versión anterior y confirma los tres escenarios corregidos; no mide calidad pedagógica general. La arquitectura FSO y las presentaciones HTML se conservan. Aquella entrega no incluyó las mejoras 2–12. Detalles y límites de actualización en `KNOWN_ISSUES.md`.

Mejora 2: herramienta `control/estado.py` para registrar evidencia en el propio ESTADO.md y contrastar archivos, fuentes, informes de pruebas, fases declaradas listas y punto de reanudación. Escritura atómica del registro y protección ante registros simultáneos; verificación sin cambiar decisiones. El informe se invalida si falla la lectura del estado. Tipos local/docente/remota son declaraciones, no acceso a servicios ni autenticación de aprobaciones.

Validación vigente: 35/35 regresiones PASS, 19/19 escenarios de revisión independiente PASS; paquete extraído crea/compila y verifica aulas nuevas y anteriores; preservación de decisiones y detección de evidencia modificada comprobadas. Guía Markdown/PDF actualizada: 15 páginas, sin desbordes, página de continuidad revisada visualmente. `dist/validacion.json` contiene el hash vigente. La herramienta exige el formato de fases 0–9 del molde y verifica solo las evidencias registradas. No incluye propagación de dependencias, matriz de sílabo, panel o respaldos (mejoras 3–12).
