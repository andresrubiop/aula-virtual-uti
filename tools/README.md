# Generar la guía PDF

**Fuente única:** edita solo `aula-virtual-uti/GUIA_DE_USO.md` (la que viaja en la skill). `python3 tools/guias.py generar` escribe la guía de la raíz (`../GUIA_DE_USO.md`, con el enlace al PDF y los enlaces con prefijo `aula-virtual-uti/`). El PDF usa la guía de la raíz, distribuida en 15 páginas con introducción visual, índice, recuadros y comprobaciones didácticas. Tras regenerarlo, `python3 tools/guias.py pdf` anota las huellas; `python3 tools/guias.py comprobar` falla si la raíz o el PDF no corresponden a la guía actual.

Requiere Python, `markdown2==2.5.5`, Node 22 o posterior y Chrome/Chromium. Usa un entorno virtual si lo prefieres. Desde la raíz del repositorio:

```bash
python3 tools/guias.py generar
python3 -m pip install markdown2==2.5.5        # o: uv run --with markdown2==2.5.5 python3 tools/generar_guia.py …
python3 tools/generar_guia.py /tmp/uti-guia.html
node tools/imprimir_guia.mjs /tmp/uti-guia.html GUIA_DE_USO.pdf
python3 tools/guias.py pdf && python3 tools/guias.py comprobar
```

En Windows sustituye `python3` por `py -3` y `/tmp/uti-guia.html` por una ruta temporal local. La generación se verificó en Linux. El HTML intermedio no requiere red: logos y fuentes se incrustan desde los recursos del proyecto.

El impresor comprueba el espacio de las páginas antes de generar; si hay desbordes detiene la exportación. Revisa visualmente el PDF tras modificar el contenido. Los textos seleccionables, los enlaces y el índice ayudan a consultar la guía en pantalla y a imprimirla. La guía documenta flujos; no constituye una sesión real de NotebookLM ni una importación Canvas.
