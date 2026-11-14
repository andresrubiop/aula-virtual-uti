# Aula virtual UTI

Skill para Claude y Codex que acompaña a docentes de la Universidad Tecnológica Indoamérica desde el sílabo y sus materiales hasta un aula interactiva ES/EN y un paquete para Canvas.

Autor: **Andrès Rubio Proaño** · [@andresrubiop](https://github.com/andresrubiop).

## Empieza aquí

**[Guía del profesor en PDF](GUIA_DE_USO.pdf)** · **[Leer la guía completa](GUIA_DE_USO.md)**

Ambas están en la carpeta principal. El PDF incluye 15 páginas con mapa del proceso, instrucciones por sistema, mensajes listos para copiar y comprobaciones para avanzar por fases.

## Qué produce

- Aula local sin conexión, con ediciones de estudiante y docente.
- Presentaciones **HTML embebidas en el aula**, manuales, prácticas, cuestionarios y animaciones interactivas.
- PDF exportados desde el HTML y carpeta portátil.
- Paquete Canvas `.imscc`, con preparación bilingüe y validación local.
- Guiones y flujo opcional de videos con la cuenta autorizada del docente.

La estructura y el stack conservan el patrón de **FSO**: HTML/CSS/JavaScript locales, compilación Python y herramientas de comprobación con Node/navegador. El formato del sílabo de FSO es la referencia común; los datos académicos siempre proceden del sílabo vigente de cada proyecto formativo.

## Instalar

Descarga [aula-virtual-uti.skill](dist/aula-virtual-uti.skill), que es un ZIP, y extrae su carpeta completa. También puedes clonar este repositorio y copiar `aula-virtual-uti/` a:

- `.claude/skills/` dentro de tu proyecto para Claude Code.
- `.agents/skills/` dentro de tu proyecto para Codex.

Abre una nueva sesión y escribe:

> Usa aula-virtual-uti para crear el aula de mi proyecto formativo. Aquí están el sílabo vigente, mis presentaciones y las guías prácticas. Prepara el aula local ES/EN y el paquete Canvas.

Consulta la [guía de uso para docentes](GUIA_DE_USO.md), la [guía de instalación](aula-virtual-uti/references/instalacion.md) y el [flujo de trabajo](aula-virtual-uti/SKILL.md). La skill pregunta por tu cuenta de NotebookLM y tu interés en videos opcionales; tú inicias sesión directamente y autorizas las fuentes que se subirán.

La guía acompaña al profesor desde crear la carpeta y reunir el sílabo/documentos, instalar Claude Code o Codex en Linux/macOS/Windows y cargar la skill, hasta producir videos y realizar la importación en [Canvas Indoamérica](https://indoamerica.instructure.com/login/saml). Incluye mensajes listos para iniciar, cerrar una jornada y retomar al día siguiente.

El desarrollo se organiza en fases. Cada aula mantiene `ESTADO.md` con fase actual, decisiones, evidencias, pendientes y próxima acción; permite continuar durante varios días y cambiar de asistente sin recrear el aula. Consulta el [protocolo de continuidad](aula-virtual-uti/references/continuidad.md).

## Probar localmente

Python 3.10 o superior permite crear y compilar el aula. Node 22 o superior y Chrome/Chromium permiten comprobarla y producir PDF. Videos y extracción de PDF añaden dependencias opcionales, descritas por el diagnóstico:

```bash
python3 aula-virtual-uti/scripts/entorno.py
python3 aula-virtual-uti/scripts/nuevo_aula.py /tmp/aula-demo --nombre "Proyecto formativo de demostración" --periodo B26
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Abre `/tmp/aula-demo/hub/dist/index.html`. Es una unidad demostrativa con marcas por completar; debe adaptarse a documentos reales. Las pruebas usan datos ficticios y crean sus fixtures en carpetas temporales.

## Estado y límites

Versión inicial para revisión docente. La mejora 1 corrige la caché de fuentes retiradas, el orden y las notas de PowerPoint y las colisiones de guías Canvas; 15 pruebas locales pasan. La compilación local y las regresiones están comprobadas. La importación real en Canvas y la generación autenticada de videos siguen pendientes; la validación del ZIP no certifica esas integraciones. Consulta [ESTADO.md](ESTADO.md) y los [problemas conocidos](KNOWN_ISSUES.md).

La identidad gráfica UTI y las dependencias de terceros conservan sus respectivos derechos. La publicación del código no otorga derechos sobre las marcas institucionales.
