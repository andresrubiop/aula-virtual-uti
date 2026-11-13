# Generar la guía PDF

La guía completa para leer en GitHub está en `../GUIA_DE_USO.md`. El PDF usa su contenido, distribuido en 15 páginas con introducción visual, índice, recuadros y comprobaciones didácticas. La copia de la guía dentro de `aula-virtual-uti/` se conserva para la skill instalable; cuando cambie el contenido, actualiza ambas y adapta los enlaces relativos.

Requiere Python, `markdown2==2.5.5`, Node 22 o posterior y Chrome/Chromium. Usa un entorno virtual si lo prefieres. Desde la raíz del repositorio:

```bash
python3 -m pip install markdown2==2.5.5
python3 tools/generar_guia.py /tmp/uti-guia.html
node tools/imprimir_guia.mjs /tmp/uti-guia.html GUIA_DE_USO.pdf
```

En Windows sustituye `python3` por `py -3` y `/tmp/uti-guia.html` por una ruta temporal local. La generación se verificó en Linux. El HTML intermedio no requiere red: logos y fuentes se incrustan desde los recursos del proyecto.

El impresor comprueba el espacio de las páginas antes de generar; si hay desbordes detiene la exportación. Revisa visualmente el PDF tras modificar el contenido. Los textos seleccionables, los enlaces y el índice ayudan a consultar la guía en pantalla y a imprimirla. La guía documenta flujos; no constituye una sesión real de NotebookLM ni una importación Canvas.
