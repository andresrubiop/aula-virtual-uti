"""Matriz con sílabo y revisiones ficticios: no certifica contenidos ni cuentas remotas."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]/'aula-virtual-uti'
CONTROL = SKILL/'assets/plantilla-aula/control'


class Cobertura(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = json.loads((SKILL/'references/silabo-ejemplo.json').read_text(encoding='utf-8'))
        self.course = {'units':[{'n':1,'id':'u1','moment':1,'sessions':[1]}]}
        self.write('canvas/silabo.json',self.data); self.write('hub/src/course.json',self.course)
        self.write('ESTADO.md',(SKILL/'assets/plantilla-aula/ESTADO.md').read_text(encoding='utf-8'))
        self.html = '<section id="tema"><p lang="es">Contenido ficticio para comprobar enlaces.</p><p lang="en">Fictitious content for link checks.</p></section>'
        self.resource = 'hub/src/content/u1/50-manual.html'
        self.write(self.resource,self.html);self.write('hub/src/content/u1/30-presentacion.html',self.html)
        self.write('control/revision.txt','Revisión ficticia del escenario de prueba; no es aprobación docente real.')
        self.assertEqual(self.cli('iniciar').returncode,0)
        report = self.report()
        self.links = [{'elemento':r['id'],'archivo':self.resource,'seccion':'tema','idioma':lang,'registro':'revision','nota':'Relación declarada ficticia para esta prueba.'}
                      for r in report['filas'] for lang in ('es','en')]
        self.save_map(); self.register()
    def write(self,name,value):
        p = self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(value,ensure_ascii=False,indent=2) if isinstance(value,(dict,list)) else value,encoding='utf-8')
    def cli(self,*args):
        return subprocess.run([sys.executable,str(CONTROL/'cobertura.py'),'--aula',str(self.root),*args],capture_output=True,text=True,encoding='utf-8')
    def state(self,*args):
        return subprocess.run([sys.executable,str(CONTROL/'estado.py'),'--aula',str(self.root),*args],capture_output=True,text=True,encoding='utf-8')
    def save_map(self): self.write('control/cobertura.json',{'version':1,'vinculos':self.links})
    def register(self,kind='docente'):
        r = self.state('registrar','revision','--fase','5','--entregable',self.resource,'--fuente','canvas/silabo.json','--fuente','hub/src/course.json','--fuente','control/cobertura.json','--prueba','control/revision.txt','--resultado','pasado','--tipo',kind,'--reemplazar')
        self.assertEqual(r.returncode,0,r.stderr)
    def report(self,code=1):
        r=self.cli('verificar','--json');self.assertEqual(r.returncode,code,r.stderr+r.stdout)
        return json.loads(r.stdout)
    def test_cubre_todos_los_elementos_con_revision_declarada(self):
        r=self.report(0)
        self.assertEqual({x['id'] for x in r['filas']},{'RA/RA1','M1/S1','M1/S1/C1','M1/S1/C2','EV/M1','PR/PR1','EV/FINAL'})
        self.assertEqual(r['resumen']['revision_declarada_vigente'],7)
        self.assertIn('no certifican',r['avisos'][0])
    def test_no_sobrescribe_mapa_existente(self):
        p=self.root/'control/cobertura.json';before=p.read_bytes()
        self.assertEqual(self.cli('iniciar').returncode,2);self.assertEqual(p.read_bytes(),before)
    def test_sin_mapa_o_registros_no_declara_cobertura_por_existencia(self):
        (self.root/'control/cobertura.json').unlink();r=self.report()
        self.assertEqual(r['resumen']['revision_declarada_vigente'],0)
        self.assertTrue(any('Falta control/cobertura' in s for s in r['hallazgos']))
    def test_vinculo_sin_revision_no_basta(self):
        self.links[0]['registro']='ausente';self.save_map();self.register()
        r=self.report();self.assertIn('Registro de revisión inexistente',json.dumps(r,ensure_ascii=False))
    def test_prueba_local_no_suplanta_revision_academica(self):
        self.register('local');r=self.report();self.assertEqual(r['resumen']['revision_declarada_vigente'],0)
    def test_recurso_modificado_invalida_revision(self):
        self.write(self.resource,self.html+'<p>Edición posterior</p>');r=self.report()
        self.assertEqual(r['resumen']['revision_declarada_vigente'],0)
    def test_cambio_silabo_y_contenido_nuevo_no_quedan_ocultos(self):
        self.data['momentos'][0]['sesiones'][0]['contenidos'].append('Contenido añadido')
        self.write('canvas/silabo.json',self.data);r=self.report()
        new=next(x for x in r['filas'] if x['id']=='M1/S1/C3')
        self.assertEqual(new['vinculos'],[]);self.assertEqual(r['resumen']['revision_declarada_vigente'],0)
    def test_mapa_modificado_invalida_registro(self):
        self.links[0]['nota']='Relación distinta';self.save_map()
        self.assertEqual(self.report()['resumen']['revision_declarada_vigente'],0)
    def test_ra_huerfano_y_referencia_desconocida(self):
        self.data['ra'].append(['RA2','Nuevo resultado','Nueva evidencia'])
        self.data['momentos'][0]['ra']=['RA9'];self.write('canvas/silabo.json',self.data);self.register()
        r=self.report();s=json.dumps(r,ensure_ascii=False)
        self.assertIn('RA sin sesión asociada',s);self.assertIn('RA inexistente: RA9',s)
    def test_unidad_huerfana_y_practica_desvinculada(self):
        self.course['units'].append({'n':2,'id':'u2','moment':9,'sessions':[9]})
        self.write('hub/src/course.json',self.course)
        self.data['practicas'][0]['unidad']=2;self.write('canvas/silabo.json',self.data);self.register()
        s=json.dumps(self.report(),ensure_ascii=False)
        self.assertIn('ninguna sesión',s);self.assertIn('no vinculada a su sesión',s);self.assertIn('momento/sesión inexistente',s)
    def test_sesion_repaso_no_requiere_unidad_nueva(self):
        self.data['momentos'][0]['sesiones'][0]['aula']={'repaso':[1]}
        self.write('canvas/silabo.json',self.data);self.register()
        r=self.report(0);self.assertEqual(next(x for x in r['filas'] if x['id']=='M1/S1')['unidades'],[1])
    def test_asociacion_implicitita_course_json(self):
        del self.data['momentos'][0]['sesiones'][0]['aula'];self.write('canvas/silabo.json',self.data);self.register();self.report(0)
    def test_practica_sin_rubrica_y_guia_ausente(self):
        self.data['momentos'][0]['rubrica']=[];self.data['practicas'][0]['archivo']='fuentes/guias-practicas/no.pdf'
        self.write('canvas/silabo.json',self.data);self.register();s=json.dumps(self.report(),ensure_ascii=False)
        self.assertIn('Falta rúbrica',s);self.assertIn('Guía original',s)
    def test_recurso_o_seccion_inexistente(self):
        self.links[0]['seccion']='no-existe';self.save_map();self.register()
        self.assertIn('Sección HTML ausente',json.dumps(self.report(),ensure_ascii=False))
        (self.root/self.resource).unlink();self.assertIn('Recurso no comprobable',json.dumps(self.report(),ensure_ascii=False))
    def test_ingles_ausente_y_plantilla_incompleta(self):
        self.write(self.resource,'<section id="tema"><p lang="es">[COMPLETAR: contenido]</p></section>');self.register()
        r=self.report();self.assertEqual(r['resumen']['revision_declarada_vigente'],0)
    def test_texto_docente_oculto_y_scripts_no_cuentan(self):
        for content in ['<noscript>'+self.html+'</noscript>', '<!--docente-->'+self.html+'<!--/docente-->', '<section id="tema" hidden><p lang="es">Oculto</p><p lang="en">Hidden</p></section>', '<script id="tema" lang="es">texto</script>']:
            self.write(self.resource,content);self.register();self.assertEqual(self.report()['resumen']['revision_declarada_vigente'],0)
    def test_ids_html_duplicados_no_cuentan(self):
        self.write(self.resource,self.html+self.html);self.register()
        self.assertIn('ID duplicado',json.dumps(self.report(),ensure_ascii=False))
    def test_rutas_privadas_y_externas_rechazadas(self):
        for path in ['fuentes/privado/secreto.html','../afuera.html','/tmp/externo.html']:
            self.links[0]['archivo']=path;self.save_map();self.register()
            self.assertIn('Recurso no comprobable',json.dumps(self.report(),ensure_ascii=False))
    def test_no_sigue_enlaces(self):
        p=self.root/self.resource;p.unlink()
        try: p.symlink_to(self.root/'control/revision.txt')
        except (OSError,NotImplementedError): self.skipTest('Enlaces no disponibles')
        self.assertIn('Recurso no comprobable',json.dumps(self.report(),ensure_ascii=False))
    def test_formato_erroneo_invalida_informe_anterior(self):
        self.report(0);self.write('control/cobertura.json',{'version':1,'vinculos':'incorrecto'})
        r=self.cli('verificar');self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
        self.assertIn('Cobertura no comprobada',(self.root/'control/COBERTURA.md').read_text(encoding='utf-8'))
    def test_ids_curriculares_duplicados_y_tipos_erroneos(self):
        self.data['ra']*=2;self.write('canvas/silabo.json',self.data)
        self.assertEqual(self.cli('verificar').returncode,2)
        self.data['ra']={'RA1':'texto'};self.write('canvas/silabo.json',self.data)
        self.assertEqual(self.cli('verificar').returncode,2)
    def test_enlace_extra_desconocido_no_se_ignora(self):
        self.links.append({**self.links[0],'elemento':'RA/INVENTADO'});self.save_map();self.register()
        self.assertTrue(any('elemento inexistente' in s for s in self.report()['hallazgos']))
    def test_ra_practica_debe_corresponder_a_sesion(self):
        self.data['ra'].append(['RA2','Resultado distinto','Otra evidencia'])
        self.data['practicas'][0]['ra']=['RA2'];self.write('canvas/silabo.json',self.data);self.register()
        row=next(r for r in self.report()['filas'] if r['id']=='PR/PR1')
        self.assertIn('RA de práctica no asociado a su sesión.',row['pendientes'])
    def test_guia_original_exige_vinculo_y_cambio_invalida_revision(self):
        guide='fuentes/guias-practicas/PR1.txt';self.write(guide,'Guía ficticia original')
        self.data['practicas'][0]['archivo']=guide;self.write('canvas/silabo.json',self.data);self.register()
        row=next(r for r in self.report()['filas'] if r['id']=='PR/PR1')
        self.assertEqual(row['estado'],'pendiente')
        r=self.state('registrar','revision','--fase','5','--entregable',self.resource,'--fuente','canvas/silabo.json','--fuente','hub/src/course.json','--fuente','control/cobertura.json','--fuente',guide,'--prueba','control/revision.txt','--resultado','pasado','--tipo','docente','--reemplazar')
        self.assertEqual(r.returncode,0,r.stderr);self.report(0)
        self.write(guide,'Guía ficticia modificada')
        row=next(r for r in self.report()['filas'] if r['id']=='PR/PR1')
        self.assertEqual(row['estado'],'pendiente')
    def test_no_modifica_estado_silabo_recursos_ni_mapa(self):
        originals={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.name!='COBERTURA.md'}
        self.report(0)
        for p,b in originals.items():self.assertEqual(p.read_bytes(),b,str(p))
    def test_matriz_derivada_no_se_registra_como_prueba(self):
        self.report(0)
        r=self.state('registrar','circular','--fase','5','--entregable',self.resource,'--fuente','canvas/silabo.json','--prueba','control/COBERTURA.md','--resultado','pasado')
        self.assertEqual(r.returncode,2)


if __name__=='__main__':unittest.main()
