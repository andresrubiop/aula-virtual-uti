/* Hub.pdf · escritura de PDF sin dependencias: anota un PDF existente mediante una
 * ACTUALIZACIÓN INCREMENTAL (los bytes originales no se tocan; se añaden objetos al final).
 *
 * Se usa para exportar la presentación anotada a mano en clase:
 *   Hub.pdf.anotar(bytes, { capas, hojas, espacio: [1600, 900], titulo })
 *     capas  [{pagina, ops, inkList, color}]   tinta sobre una página existente (anotación /Ink con /AP)
 *     hojas  [{tras, ops, etiqueta}]           página nueva en blanco después de la página `tras`
 *   Las coordenadas de `ops` e `inkList` van en el espacio de la diapositiva (`espacio`, con la Y hacia
 *   abajo); aquí se aplica la transformación al sistema del PDF (Y hacia arriba).
 *
 * Solo admite PDF con tabla xref clásica, que es lo que genera Chrome (y por tanto todos los PDF del curso).
 */
(function () {
  'use strict';
  const Hub = window.Hub;

  // ---- texto ↔ bytes en Latin-1: un carácter = un byte, imprescindible para los desplazamientos del xref
  function texto(bytes) {
    let s = '';
    for (let i = 0; i < bytes.length; i += 8192) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
    return s;
  }
  function crudo(s) {
    const b = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) b[i] = s.charCodeAt(i) & 0xff;
    return b;
  }

  const BLANCO = ' \t\r\n\f\0';
  const DELIM = '()<>[]{}/%';

  function salta(t, i) {
    while (i < t.length) {
      if (BLANCO.includes(t[i])) i++;
      else if (t[i] === '%') { while (i < t.length && t[i] !== '\n' && t[i] !== '\r') i++; }
      else break;
    }
    return i;
  }

  function finCadena(t, i) {          // (…) con paréntesis anidados y escapes
    let d = 0;
    for (; i < t.length; i++) {
      if (t[i] === '\\') { i++; continue; }
      if (t[i] === '(') d++;
      else if (t[i] === ')') { d--; if (!d) return i + 1; }
    }
    return i;
  }

  /** Lee un objeto PDF desde la posición i. Devuelve [texto del valor, posición final]. */
  function valor(t, i) {
    i = salta(t, i);
    const c = t[i];
    if (c === '<' && t[i + 1] === '<') {
      let d = 0, j = i;
      while (j < t.length) {
        if (t[j] === '(') j = finCadena(t, j);
        else if (t[j] === '<' && t[j + 1] === '<') { d++; j += 2; }
        else if (t[j] === '>' && t[j + 1] === '>') { d--; j += 2; if (!d) break; }
        else j++;
      }
      return [t.slice(i, j), j];
    }
    if (c === '[') {
      let d = 0, j = i;
      while (j < t.length) {
        if (t[j] === '(') j = finCadena(t, j);
        else if (t[j] === '[') { d++; j++; }
        else if (t[j] === ']') { d--; j++; if (!d) break; }
        else j++;
      }
      return [t.slice(i, j), j];
    }
    if (c === '(') { const j = finCadena(t, i); return [t.slice(i, j), j]; }
    if (c === '<') { const j = t.indexOf('>', i) + 1; return [t.slice(i, j), j]; }
    if (c === '/') {
      let j = i + 1;
      while (j < t.length && !BLANCO.includes(t[j]) && !DELIM.includes(t[j])) j++;
      return [t.slice(i, j), j];
    }
    const m = /^[+-]?[\d.]+(?:[ \t\r\n]+\d+[ \t\r\n]+R)?/.exec(t.slice(i, i + 48));
    if (m && m[0]) return [m[0], i + m[0].length];
    let j = i;
    while (j < t.length && /[A-Za-z]/.test(t[j])) j++;
    return [t.slice(i, j), Math.max(j, i + 1)];
  }

  /** Claves del primer nivel de un diccionario: {clave: {v, ini, fin}} (posiciones dentro del texto dado). */
  function dicc(t) {
    const out = {};
    let i = t.indexOf('<<');
    if (i < 0) return out;
    i += 2;
    while (i < t.length) {
      i = salta(t, i);
      if (t[i] === '>' && t[i + 1] === '>') break;
      if (t[i] !== '/') { const [, j] = valor(t, i); if (j <= i) break; i = j; continue; }
      const [clave, j] = valor(t, i);
      const ini = salta(t, j);
      const [v, k] = valor(t, ini);
      out[clave.slice(1)] = { v, ini, fin: k };
      i = k;
    }
    return out;
  }

  /** Devuelve el diccionario con la clave puesta en `nuevo` (la añade si no existía). */
  function conClave(cuerpo, clave, nuevo) {
    const d = dicc(cuerpo);
    if (d[clave]) return cuerpo.slice(0, d[clave].ini) + nuevo + cuerpo.slice(d[clave].fin);
    const i = cuerpo.indexOf('<<') + 2;
    return cuerpo.slice(0, i) + `/${clave} ${nuevo}` + cuerpo.slice(i);
  }

  const numRef = s => { const m = /(\d+)\s+\d+\s+R/.exec(s || ''); return m ? +m[1] : null; };
  const numRefs = s => Array.from(String(s).matchAll(/(\d+)\s+\d+\s+R/g), m => +m[1]);

  /** Índice del PDF: desplazamiento de cada objeto + tráiler (sigue la cadena /Prev). */
  function indice(t) {
    const m = /startxref\s+(\d+)\s*%%EOF\s*$/.exec(t.slice(-2048)) || /startxref\s+(\d+)/.exec(t.slice(-2048));
    if (!m) throw new Error('El PDF no tiene índice (startxref).');
    const inicial = +m[1];
    const offsets = new Map();
    let trailer = null, pos = inicial;
    const vistos = new Set();
    while (Number.isFinite(pos) && pos > 0 && !vistos.has(pos)) {
      vistos.add(pos);
      let i = salta(t, pos);
      if (!t.startsWith('xref', i)) {
        throw new Error('Este PDF usa un índice comprimido (xref stream) que el exportador del hub no lee.');
      }
      i += 4;
      const ent = /(\d{10})[ ](\d{5})[ ]([nf])/y;
      for (;;) {
        i = salta(t, i);
        if (t.startsWith('trailer', i)) { i += 7; break; }
        const cab = /^(\d+)[ \t]+(\d+)/.exec(t.slice(i, i + 48));
        if (!cab) break;
        const desde = +cab[1], n = +cab[2];
        i += cab[0].length;
        for (let k = 0; k < n; k++) {
          i = salta(t, i);
          ent.lastIndex = i;
          const e = ent.exec(t);
          if (!e) throw new Error('Tabla xref ilegible en el PDF de origen.');
          if (e[3] === 'n' && !offsets.has(desde + k)) offsets.set(desde + k, +e[1]);
          i = ent.lastIndex;
        }
      }
      const tr = {};
      const d = dicc(valor(t, i)[0]);
      for (const [k, v] of Object.entries(d)) tr[k] = v.v;
      if (!trailer) trailer = tr;
      else for (const [k, v] of Object.entries(tr)) if (!(k in trailer)) trailer[k] = v;
      pos = tr.Prev ? parseInt(tr.Prev, 10) : NaN;
    }
    if (!trailer || !trailer.Root) throw new Error('El PDF no tiene catálogo (/Root).');
    return { offsets, trailer, inicial };
  }

  function cuerpoObjeto(t, offsets, num) {
    const off = offsets.get(num);
    if (off == null) throw new Error(`El PDF no contiene el objeto ${num}.`);
    const m = /^\s*(\d+)\s+(\d+)\s+obj/.exec(t.slice(off, off + 48));
    if (!m) throw new Error(`Desplazamiento inválido para el objeto ${num}.`);
    return valor(t, off + m[0].length)[0];
  }

  /** Páginas en orden: {num, cuerpo, padre, mediaBox}. */
  function paginas(t, offsets, trailer) {
    const cat = dicc(cuerpoObjeto(t, offsets, numRef(trailer.Root)));
    if (!cat.Pages) throw new Error('El catálogo del PDF no tiene /Pages.');
    const out = [];
    const caja = (d, padres) => {
      if (d.MediaBox) return d.MediaBox.v;
      for (let k = padres.length - 1; k >= 0; k--) if (padres[k].MediaBox) return padres[k].MediaBox.v;
      return '[0 0 612 792]';
    };
    (function rec(num, padre, padres, vistos) {
      if (vistos.has(num)) return;
      vistos.add(num);
      const cuerpo = cuerpoObjeto(t, offsets, num);
      const d = dicc(cuerpo);
      if (d.Kids) {
        const pila = padres.concat([d]);
        numRefs(d.Kids.v).forEach(hijo => rec(hijo, num, pila, vistos));
      } else {
        out.push({ num, cuerpo, padre, mediaBox: caja(d, padres) });
      }
    })(numRef(cat.Pages.v), null, [], new Set());
    return out;
  }

  const num = x => (Math.round(x * 1000) / 1000).toString();
  const cadena = s => '(' + String(s).replace(/([\\()])/g, '\\$1').replace(/[^\x20-\xff]/g, ' ') + ')';
  const fecha = d => 'D:' + [d.getFullYear(), d.getMonth() + 1, d.getDate(), d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((v, i) => String(v).padStart(i ? 2 : 4, '0')).join('') + 'Z';

  Hub.pdf = {
    /** Número de páginas del PDF (para avisar si no coincide con la presentación). */
    contar(origen) {
      const t = texto(origen);
      const { offsets, trailer } = indice(t);
      return paginas(t, offsets, trailer).length;
    },

    /** Añade tinta (y hojas de notas) a un PDF existente. Devuelve un Uint8Array nuevo. */
    anotar(origen, opciones) {
      const o = opciones || {};
      const capas = o.capas || [], hojas = o.hojas || [];
      const [EW, EH] = o.espacio || [1600, 900];
      const alfa = o.alfaMarcador == null ? 0.32 : o.alfaMarcador;
      const t = texto(origen);
      const { offsets, trailer, inicial } = indice(t);
      const pags = paginas(t, offsets, trailer);
      if (!pags.length) throw new Error('El PDF no tiene páginas.');

      let siguiente = Math.max(parseInt(trailer.Size, 10) || 0, ...offsets.keys()) + 1;
      const nuevos = new Map();                                   // número de objeto → cuerpo completo
      const cuerpoDe = n => (nuevos.has(n) ? nuevos.get(n) : cuerpoObjeto(t, offsets, n));
      const crea = cuerpo => { const n = siguiente++; nuevos.set(n, cuerpo); return n; };
      const flujo = (dict, datos) => `<<${dict}/Length ${datos.length}>>\nstream\n${datos}\nendstream`;
      const gs = `/ExtGState<</GM<</Type/ExtGState/ca ${alfa}/BM/Multiply>>/GN<</Type/ExtGState/ca 1/BM/Normal>>>>`;
      const hoy = new Date();
      const marca = fecha(hoy);
      const titulo = o.titulo || 'Anotaciones de clase';

      // Transformación espacio de la diapositiva (Y hacia abajo) → espacio del PDF (Y hacia arriba).
      const marco = pag => {
        const [x0, y0, x1, y1] = (pag.mediaBox.match(/[-\d.]+/g) || [0, 0, 612, 792]).map(Number);
        const w = Math.abs(x1 - x0), hh = Math.abs(y1 - y0);
        return { x0: Math.min(x0, x1), y0: Math.min(y0, y1), x1: Math.max(x0, x1), y1: Math.max(y0, y1), w, h: hh };
      };
      const cm = m => `${num(m.w / EW)} 0 0 ${num(-m.h / EH)} ${num(m.x0)} ${num(m.y1)} cm`;

      // ---- 1. tinta sobre las diapositivas: anotación /Ink con su propia apariencia
      for (const capa of capas) {
        const pag = pags[capa.pagina];
        if (!pag || !capa.ops) continue;
        const m = marco(pag);
        const datos = `q ${cm(m)}\n${capa.ops}\nQ\n`;
        const ap = crea(flujo(`/Type/XObject/Subtype/Form/FormType 1/BBox[${num(m.x0)} ${num(m.y0)} ${num(m.x1)} ${num(m.y1)}]` +
          `/Resources<</ProcSet[/PDF]${gs}>>`, datos));
        const tinta = (capa.inkList || []).map(l => {
          const p = [];
          for (let i = 0; i + 1 < l.length; i += 2) p.push(num(m.x0 + (l[i] / EW) * m.w), num(m.y1 - (l[i + 1] / EH) * m.h));
          return '[' + p.join(' ') + ']';
        }).join('');
        const c = capa.color || [0.51, 0.08, 0.21];
        const anot = crea(`<</Type/Annot/Subtype/Ink/Rect[${num(m.x0)} ${num(m.y0)} ${num(m.x1)} ${num(m.y1)}]` +
          `/F 4/CA 1/C[${c.map(num).join(' ')}]/T${cadena(titulo)}/Contents${cadena('Anotación manuscrita de la clase')}` +
          `/M(${marca})/InkList[${tinta}]/BS<</W 0>>/AP<</N ${ap} 0 R>>>>`);
        const previas = dicc(cuerpoDe(pag.num)).Annots;
        const lista = previas && previas.v.trim().startsWith('[')
          ? previas.v.replace(/\]\s*$/, ` ${anot} 0 R]`)
          : `[${anot} 0 R]`;
        nuevos.set(pag.num, conClave(cuerpoDe(pag.num), 'Annots', lista));
      }

      // ---- 2. hojas de notas: páginas nuevas insertadas entre las diapositivas
      let fuente = null;
      const inserciones = [];
      for (const hoja of hojas) {
        const base = pags[Math.min(Math.max(hoja.tras, 0), pags.length - 1)];
        if (!base) continue;
        const m = marco(base);
        // Rejilla en el espacio de la diapositiva: idéntica a la que se ve en el hub (patrón de 80 × 80 bajo la cabecera).
        const y0 = o.rejillaDesde == null ? 81 : o.rejillaDesde;
        const rejilla = [];
        for (let x = 0; x <= EW; x += 80) rejilla.push(`${x} ${y0} m ${x} ${EH} l`);
        for (let y = y0; y <= EH; y += 80) rejilla.push(`0 ${num(y)} m ${EW} ${num(y)} l`);
        const cabecera = hoja.etiqueta
          ? `BT /F1 ${num(m.h * 0.026)} Tf 0.46 0.47 0.48 rg ${num(m.x0 + m.w * 0.05)} ${num(m.y1 - m.h * 0.058)} Td ${cadena(hoja.etiqueta)} Tj ET\n` +
            `0.51 0.08 0.21 RG ${num(m.h * 0.003)} w ${num(m.x0 + m.w * 0.05)} ${num(m.y1 - m.h * 0.076)} m ${num(m.x1 - m.w * 0.05)} ${num(m.y1 - m.h * 0.076)} l S\n`
          : '';
        const datos = `q ${cm(m)}\n1 1 1 rg 0 0 ${EW} ${EH} re f\n` +
          `q 0.925 0.906 0.914 RG 1.2 w\n${rejilla.join('\n')}\nS Q\n` +
          (hoja.ops || '') + `\nQ\n${cabecera}`;
        const cont = crea(flujo('', datos));
        if (!fuente) fuente = crea('<</Type/Font/Subtype/Type1/BaseFont/Helvetica/Encoding/WinAnsiEncoding>>');
        const pag = crea(`<</Type/Page/MediaBox[${num(m.x0)} ${num(m.y0)} ${num(m.x1)} ${num(m.y1)}]` +
          `/Resources<</ProcSet[/PDF/Text]/Font<</F1 ${fuente} 0 R>>${gs}>>/Contents ${cont} 0 R/Parent ${base.padre} 0 R>>`);
        inserciones.push({ padre: base.padre, tras: base.num, num: pag });
      }

      if (inserciones.length) {
        const ultima = new Map();                 // varias hojas seguidas conservan su orden
        for (const ins of inserciones) {
          const cuerpo = cuerpoDe(ins.padre);
          const kids = dicc(cuerpo).Kids;
          if (!kids) throw new Error('No se pudo insertar la hoja: el árbol de páginas es inesperado.');
          const anterior = ultima.get(ins.tras) || ins.tras;
          const marcaRef = new RegExp(`${anterior}\\s+\\d+\\s+R`);
          const lista = kids.v.replace(marcaRef, r => `${r} ${ins.num} 0 R`);
          ultima.set(ins.tras, ins.num);
          nuevos.set(ins.padre, conClave(cuerpo, 'Kids', lista));
          // /Count de ese nodo y de todos sus ascendientes
          let nodo = ins.padre;
          const vistos = new Set();
          while (nodo != null && !vistos.has(nodo)) {
            vistos.add(nodo);
            const c = cuerpoDe(nodo);
            const d = dicc(c);
            if (d.Count) nuevos.set(nodo, conClave(c, 'Count', String(parseInt(d.Count.v, 10) + 1)));
            nodo = d.Parent ? numRef(d.Parent.v) : null;
          }
        }
      }

      // ---- 3. actualización incremental: objetos nuevos + xref + tráiler
      const base = origen.length;
      let extra = /[\r\n]$/.test(t) ? '' : '\n';
      const pos = new Map();
      const orden = [...nuevos.keys()].sort((a, b) => a - b);
      for (const n of orden) {
        pos.set(n, base + extra.length);
        extra += `${n} 0 obj\n${nuevos.get(n)}\nendobj\n`;
      }
      const inicioXref = base + extra.length;
      extra += 'xref\n';
      for (let k = 0; k < orden.length;) {
        let j = k;
        while (j + 1 < orden.length && orden[j + 1] === orden[j] + 1) j++;
        extra += `${orden[k]} ${j - k + 1}\n`;
        for (let i = k; i <= j; i++) extra += String(pos.get(orden[i])).padStart(10, '0') + ' 00000 n\r\n';
        k = j + 1;
      }
      extra += `trailer\n<</Size ${siguiente}/Root ${trailer.Root}` +
        (trailer.Info ? `/Info ${trailer.Info}` : '') + (trailer.ID ? `/ID ${trailer.ID}` : '') +
        `/Prev ${inicial}>>\nstartxref\n${inicioXref}\n%%EOF\n`;

      const salida = new Uint8Array(base + extra.length);
      salida.set(origen, 0);
      salida.set(crudo(extra), base);
      return salida;
    },
  };
})();
