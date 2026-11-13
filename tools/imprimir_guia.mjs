// Uso: node tools/imprimir_guia.mjs entrada.html salida.pdf
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { writeFileSync } from 'node:fs';
import { launch } from '../aula-virtual-uti/assets/plantilla-aula/hub/tools/lib/browser.mjs';
const [input,output]=process.argv.slice(2);
if(!input||!output)throw new Error('Indica HTML y PDF de salida');
const browser=await launch({width:1000,height:1200});
try {
 await browser.navigate(pathToFileURL(resolve(input)).href);
 await browser.ev('document.fonts.ready.then(()=>true)');
 await browser.send('Emulation.setEmulatedMedia',{media:'print'});
 const issues=await browser.ev(`Array.from(document.querySelectorAll('.sheet')).flatMap((page,i)=>{
   const b=page.getBoundingClientRect(), footer=page.querySelector('footer').getBoundingClientRect();
   const nodes=Array.from(page.querySelectorAll('.body p,.body table,.body pre,.body li,.body .check,.body h1,.body h3,.body .index'));
   return nodes.filter(el=>{const r=el.getBoundingClientRect();return r.bottom>footer.top-5||r.right>b.right-30||r.left<b.left+30}).map(el=>({page:i+1,text:el.innerText.slice(0,90)}));
 })`);
 if(issues.length){console.error(JSON.stringify(issues,null,2));throw new Error('Contenido fuera del área de página');}
 const result=await browser.send('Page.printToPDF',{printBackground:true,preferCSSPageSize:true,displayHeaderFooter:false,generateTaggedPDF:true,generateDocumentOutline:true});
 writeFileSync(output,Buffer.from(result.result.data,'base64'));
 console.log(JSON.stringify({pages:await browser.ev('document.querySelectorAll(".sheet").length'),overflow:issues.length,pdf:output}));
} finally {browser.close();}
