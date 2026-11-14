"""Impacto sobre archivos ficticios. Ningún comando genera contenidos ni accede a cuentas."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL=Path(__file__).resolve().parents[1]/'aula-virtual-uti'
MODULE=SKILL/'assets/plantilla-aula/control/estado.py'
spec=importlib.util.spec_from_file_location('estado_impacto',MODULE)
estado=importlib.util.module_from_spec(spec);spec.loader.exec_module(estado)


class Impacto(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.write('ESTADO.md',(SKILL/'assets/plantilla-aula/ESTADO.md').read_text(encoding='utf-8'))
        self.files={'fuentes/lecturas/u1.txt':'original 1','fuentes/lecturas/u2.txt':'original 2',
                    'hub/src/content/u1/clase.html':'edición aprobada 1','hub/src/content/u2/clase.html':'edición aprobada 2',
                    'materiales/u1.pdf':'PDF ficticio','materiales/u1.en.html':'EN ficticio','canvas/curso.imscc':'Canvas ficticio',
                    'hub/src/course.json':'{}'}
        for name,text in self.files.items():self.write(name,text)
        self.records={'u1':(5,'hub/src/content/u1/clase.html',['fuentes/lecturas/u1.txt']),
                      'u2':(5,'hub/src/content/u2/clase.html',['fuentes/lecturas/u2.txt']),
                      'pdf':(6,'materiales/u1.pdf',['hub/src/content/u1/clase.html']),
                      'en':(5,'materiales/u1.en.html',['hub/src/content/u1/clase.html']),
                      'canvas':(8,'canvas/curso.imscc',['materiales/u1.pdf','materiales/u1.en.html'])}
        for key in self.records:
            self.write('control/'+key+'.log','PASS ficticio '+key)
            r=self.register(key);self.assertEqual(r.returncode,0,r.stderr)
    def write(self,name,text):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    def cli(self,*args):
        return subprocess.run([sys.executable,str(MODULE),'--aula',str(self.root),*args],capture_output=True,text=True,encoding='utf-8')
    def register(self,key,*extra,sources=None):
        phase,out,src=self.records[key];args=['registrar',key,'--fase',str(phase),'--entregable',out,'--prueba','control/'+key+'.log','--resultado','pasado']
        for f in src if sources is None else sources:args+=['--fuente',f]
        return self.cli(*args,*extra)
    def impact(self,*args,code=1):
        r=self.cli('impacto','--json',*args);self.assertEqual(r.returncode,code,r.stderr+r.stdout);return json.loads(r.stdout)
    def test_cadena_y_rama_independiente(self):
        self.write('fuentes/lecturas/u1.txt','cambio académico')
        report=self.impact();order=report['orden_actualizacion']
        self.assertEqual(set(order),{'u1','en','pdf','canvas'});self.assertEqual(order[0],'u1');self.assertEqual(order[-1],'canvas')
        self.assertEqual(report['sin_impacto_detectado'],['u2'])
        canvas=next(x for x in report['afectados'] if x['id']=='canvas')
        self.assertEqual(set(canvas['bloqueado_por']),{'en','pdf'})
        self.assertEqual(canvas['cambios'],[])  # Incluso con bytes de Canvas intactos.
        v=self.cli('verificar','--json');self.assertEqual(v.returncode,1)
        self.assertFalse(next(x for x in json.loads(v.stdout)['registros'] if x['id']=='canvas')['vigente'])
    def test_conserva_ediciones_y_decisiones(self):
        self.write('hub/src/content/u1/clase.html','CORRECCIÓN MANUAL APROBADA')
        original={p:p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        report=self.impact();u1=next(x for x in report['afectados'] if x['id']=='u1')
        self.assertEqual(u1['conservar_ediciones'],['hub/src/content/u1/clase.html'])
        for p,content in original.items():self.assertEqual(p.read_bytes(),content,str(p))
    def test_revisar_solo_informe_propaga_sin_reescribir_contenido(self):
        (self.root/'control/u1.log').unlink();r=self.impact()
        self.assertEqual(set(r['orden_actualizacion']),{'u1','en','pdf','canvas'})
        self.assertEqual(next(x for x in r['afectados'] if x['id']=='u1')['conservar_ediciones'],[])
    def test_no_bendice_derivado_con_origen_obsoleto(self):
        self.write('fuentes/lecturas/u1.txt','cambio');before=(self.root/'ESTADO.md').read_bytes()
        r=self.register('pdf','--reemplazar');self.assertEqual(r.returncode,2)
        self.assertIn('evidencia pendiente',r.stderr);self.assertEqual(before,(self.root/'ESTADO.md').read_bytes())
    def test_revalidar_origen_sin_cambio_de_salida_evitar_regeneracion(self):
        self.write('fuentes/lecturas/u1.txt','cambio cotejado: contenido no requiere modificación')
        self.write('control/u1.log','PASS ficticio tras nueva revisión')
        self.assertEqual(self.register('u1','--reemplazar').returncode,0)
        self.assertEqual(self.impact(code=0)['afectados'],[])
    def test_revalidar_origen_con_salida_cambiada_mantiene_derivados_pendientes(self):
        self.write('fuentes/lecturas/u1.txt','cambio');self.write('hub/src/content/u1/clase.html','actualización revisada')
        self.write('control/u1.log','PASS ficticio tras revisar');self.assertEqual(self.register('u1','--reemplazar').returncode,0)
        report=self.impact();self.assertEqual(set(report['orden_actualizacion']),{'pdf','en','canvas'})
        self.assertEqual(report['orden_actualizacion'][-1],'canvas')
    def test_rechaza_ciclo_sin_modificar_estado(self):
        before=(self.root/'ESTADO.md').read_bytes()
        r=self.register('u1','--reemplazar',sources=['materiales/u1.pdf']);self.assertEqual(r.returncode,2)
        self.assertIn('circulares',r.stderr);self.assertEqual(before,(self.root/'ESTADO.md').read_bytes())
    def test_alias_de_ruta_no_oculta_ciclo(self):
        r=self.register('u1','--reemplazar',sources=['materiales/./u1.pdf']);self.assertEqual(r.returncode,2)
        self.assertIn('circulares',r.stderr)
    def test_nueva_fuente_sin_relacion_no_se_declara_resuelta(self):
        self.write('fuentes/lecturas/nueva.txt','nuevo material')
        report=self.impact();self.assertEqual(report['sin_relacion_declarada'],['fuentes/lecturas/nueva.txt'])
        self.assertEqual(report['afectados'],[])
    def test_fuente_movida_a_privado_o_borrada(self):
        private=self.root/'fuentes/privado';private.mkdir()
        (self.root/'fuentes/lecturas/u1.txt').rename(private/'u1.txt')
        report=self.impact();self.assertEqual(set(report['orden_actualizacion']),{'u1','en','pdf','canvas'})
        self.assertNotIn('fuentes/privado/u1.txt',json.dumps(report))
    def test_ignora_cache_privados_y_enlaces_al_buscar_no_relacionadas(self):
        self.write('fuentes/privado/secreto.txt','no leer');self.write('fuentes/_texto/cache.txt','no leer')
        self.write('fuentes/lecturas/.env','no leer');self.write('fuentes/INVENTARIO.md','derivado')
        try:(self.root/'fuentes/lecturas/enlace').symlink_to(self.root/'fuentes/privado',target_is_directory=True)
        except (OSError,NotImplementedError):pass
        self.assertEqual(self.impact(code=0)['sin_relacion_declarada'],[])
    def test_cambio_declarado_es_simulacion_y_no_modifica(self):
        before=(self.root/'ESTADO.md').read_bytes();report=self.impact('--cambio','fuentes/lecturas/u1.txt')
        self.assertEqual(report['modo'],'incluye_cambios_declarados');self.assertEqual(set(report['orden_actualizacion']),{'u1','en','pdf','canvas'})
        self.assertEqual(before,(self.root/'ESTADO.md').read_bytes());self.assertEqual(self.impact(code=0)['afectados'],[])
    def test_cambio_declarado_desconocido_y_privado(self):
        r=self.impact('--cambio','fuentes/silabo/nuevo.pdf')
        self.assertIn('fuentes/silabo/nuevo.pdf',r['sin_relacion_declarada'])
        self.assertEqual(self.cli('impacto','--cambio','fuentes/privado/x.txt').returncode,2)
    def test_informe_antiguo_no_permanece_vigente_si_hay_error(self):
        self.impact(code=0);self.write('ESTADO.md','estado roto')
        # Sin tabla no impide analizar registros, pero un bloque malformado sí.
        self.write('ESTADO.md','estado roto '+estado.INICIO)
        self.assertEqual(self.cli('impacto').returncode,2)
        self.assertIn('Verificación no completada',(self.root/'control/IMPACTO.md').read_text(encoding='utf-8'))
    def test_informe_derivado_no_se_registra_como_evidencia(self):
        self.impact(code=0)
        r=self.register('u1','--reemplazar',sources=['control/IMPACTO.md']);self.assertEqual(r.returncode,2)
    def test_multiples_productores_se_tratan_conservadoramente(self):
        self.records['segunda_revision']=(5,'hub/src/content/u1/clase.html',['fuentes/lecturas/u1.txt'])
        self.write('control/segunda_revision.log','segunda prueba ficticia');self.assertEqual(self.register('segunda_revision').returncode,0)
        self.write('control/segunda_revision.log','prueba modificada')
        report=self.impact();self.assertEqual(set(report['orden_actualizacion']),{'segunda_revision','pdf','en','canvas'})
    def test_orden_determinista(self):
        self.write('fuentes/lecturas/u1.txt','cambio')
        a=self.impact();b=self.impact();self.assertEqual(a['orden_actualizacion'],b['orden_actualizacion'])

if __name__=='__main__':unittest.main()
