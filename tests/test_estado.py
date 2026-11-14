"""Evidencias ficticias: no se conectan servicios ni se ejecutan comandos del Markdown."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / 'aula-virtual-uti'
MODULE = SKILL / 'assets/plantilla-aula/control/estado.py'
spec = importlib.util.spec_from_file_location('estado_uti', MODULE)
estado = importlib.util.module_from_spec(spec)
spec.loader.exec_module(estado)


class Estado(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = (SKILL/'assets/plantilla-aula/ESTADO.md').read_text(encoding='utf-8')
        for name, text in {'ESTADO.md': self.original, 'canvas/silabo.json':'{"curso":"ejemplo"}',
                           'fuentes/silabo/vigente.txt':'Sílabo ficticio', 'control/prueba.txt':'PASS: caso ficticio',
                           'control/aprobacion.md':'Decisión ficticia del docente para el caso de prueba',
                           'hub/src/course.json':'{"key":"ficticio"}'}.items():
            self.write(name, text)
    def write(self, name, text):
        p=self.root/name; p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8')
    def cli(self, *args):
        return subprocess.run([sys.executable,str(MODULE),'--aula',str(self.root),*args],capture_output=True,text=True,encoding='utf-8')
    def register(self, *extra):
        return self.cli('registrar','silabo','--fase','2','--entregable','canvas/silabo.json',
                        '--fuente','fuentes/silabo/vigente.txt','--prueba','control/prueba.txt',
                        '--resultado','pasado',*extra)
    def mark(self, phase, status='✅'):
        p=self.root/'ESTADO.md';s=p.read_text(encoding='utf-8')
        import re
        s=re.sub(r'(^\| '+str(phase)+r' ·[^|]*\|) [^|]+ \|',r'\1 '+status+' |',s,flags=re.M)
        p.write_text(s,encoding='utf-8')
    def test_registra_sin_cambiar_decisiones_y_verificar_no_muta_estado(self):
        self.assertEqual(self.register().returncode,0)
        current=(self.root/'ESTADO.md').read_text(encoding='utf-8')
        self.assertEqual(current.split(estado.INICIO)[0],self.original.split(estado.INICIO)[0])
        self.assertEqual(current.split(estado.FIN)[1],self.original.split(estado.FIN)[1])
        self.mark(2);before=(self.root/'ESTADO.md').read_bytes()
        result=self.cli('verificar','--json');self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        self.assertEqual(before,(self.root/'ESTADO.md').read_bytes())
        self.assertEqual(json.loads(result.stdout)['registros'][0]['vigente'],True)
        self.assertTrue((self.root/'control/VERIFICACION_ESTADO.md').is_file())
    def test_fase_lista_sin_evidencia_falla_en_aula_anterior(self):
        self.write('ESTADO.md',self.original.split('## 10. Evidencias verificables')[0])
        self.mark(2)
        result=self.cli('verificar');self.assertEqual(result.returncode,1)
        self.assertIn('Fase 2 marcada lista sin evidencia',result.stdout)
        self.assertNotIn(estado.INICIO,(self.root/'ESTADO.md').read_text())
    def test_cambios_en_cada_tipo_de_evidencia_invalidan(self):
        self.assertEqual(self.register('--aprobacion','control/aprobacion.md').returncode,0)
        for name in ('canvas/silabo.json','fuentes/silabo/vigente.txt','control/prueba.txt','control/aprobacion.md'):
            with self.subTest(name=name):
                p=self.root/name;old=p.read_bytes();p.write_bytes(old+b' cambiado')
                r=self.cli('verificar','--json');self.assertEqual(r.returncode,1,r.stdout)
                self.assertFalse(json.loads(r.stdout)['registros'][0]['vigente']);p.write_bytes(old)
    def test_entregable_borrado_o_vacio_se_detecta(self):
        self.assertEqual(self.register().returncode,0)
        p=self.root/'canvas/silabo.json';p.unlink()
        self.assertEqual(self.cli('verificar').returncode,1)
        p.write_text('');self.assertEqual(self.cli('verificar').returncode,1)
    def test_reemplazo_explicito_y_preserva_texto_fuera_del_bloque(self):
        self.assertEqual(self.register().returncode,0)
        p=self.root/'ESTADO.md';p.write_text(p.read_text()+'\n## Decisión posterior\nConservar la unidad 1.\n')
        self.write('control/prueba.txt','PASS revisión repetida')
        self.assertEqual(self.register().returncode,2)
        self.assertEqual(self.register('--reemplazar').returncode,0)
        self.assertIn('Conservar la unidad 1.',p.read_text())
        self.assertEqual(p.read_text().count(estado.INICIO),1)
    def test_bloque_malformado_no_se_sobrescribe(self):
        for suffix in (estado.INICIO,estado.INICIO+'\n```json\n{}\n```\n'+estado.FIN):
            self.write('ESTADO.md',self.original+suffix);before=(self.root/'ESTADO.md').read_bytes()
            self.assertEqual(self.register().returncode,2)
            self.assertEqual(self.cli('verificar').returncode,2)
            self.assertEqual(before,(self.root/'ESTADO.md').read_bytes())
    def test_hash_corrupto_y_version_no_admitida(self):
        self.register();text,data=estado.leer(self.root)
        for field,value in [('version',99),('version',True)]:
            bad=dict(data);bad[field]=value
            with self.assertRaises(ValueError):estado.validar_registro(bad)
        data['registros']['silabo']['entregables']['canvas/silabo.json']='no-es-hash'
        with self.assertRaises(ValueError):estado.validar_registro(data)
    def test_prueba_fallida_o_no_ejecutada_no_respalda_fase(self):
        for outcome in ('fallido','no_ejecutado'):
            self.write('ESTADO.md',self.original)
            r=self.cli('registrar','prueba','--fase','2','--entregable','canvas/silabo.json','--fuente','fuentes/silabo/vigente.txt','--prueba','control/prueba.txt','--resultado',outcome)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(self.cli('verificar').returncode,1)
    def test_no_admite_pasado_sin_informe(self):
        r=self.cli('registrar','prueba','--fase','2','--entregable','canvas/silabo.json','--fuente','fuentes/silabo/vigente.txt','--resultado','pasado')
        self.assertEqual(r.returncode,2);self.assertEqual((self.root/'ESTADO.md').read_text(),self.original)
    def test_no_lee_rutas_privadas_fuera_o_enlaces(self):
        for name in ('../ajeno.txt','/tmp/ajeno.txt','C:\\ajeno.txt','fuentes/privado/secret.txt','fuentes/Privado/secret.txt'):
            with self.subTest(name=name),self.assertRaises(ValueError):estado.ruta(self.root,name,False)
        p=self.root/'control/enlace';
        try:p.symlink_to(self.root/'fuentes',target_is_directory=True)
        except (OSError,NotImplementedError):self.skipTest('Equipo sin permisos de enlaces')
        with self.assertRaises(ValueError):estado.ruta(self.root,'control/enlace/silabo/vigente.txt')
    def test_aprobacion_docente_necesaria_para_fase_3(self):
        self.write('PLANIFICACION.md','Plan ficticio');self.mark(3)
        base=['registrar','plan','--fase','3','--entregable','PLANIFICACION.md','--fuente','fuentes/silabo/vigente.txt','--prueba','control/prueba.txt','--resultado','pasado']
        self.assertEqual(self.cli(*base).returncode,0)
        self.assertIn('decisión docente',self.cli('verificar').stdout)
        self.assertEqual(self.cli(*base,'--reemplazar','--aprobacion','control/aprobacion.md').returncode,0)
        self.assertEqual(self.cli('verificar').returncode,0)
    def test_fase_9_no_se_prueba_con_revision_local(self):
        self.mark(9);self.register()
        text,data=estado.leer(self.root);data['registros']['silabo']['fase']=9
        data['registros']['silabo']['aprobacion']={'control/aprobacion.md':estado.digest(self.root/'control/aprobacion.md')}
        block=estado.INICIO+'\n```json\n'+json.dumps(data)+'\n```\n'+estado.FIN
        self.write('ESTADO.md',text[:text.index(estado.INICIO)]+block)
        self.assertIn('una prueba local no respalda',self.cli('verificar').stdout)
    def test_reanudacion_pendiente_y_ubicacion_ausente(self):
        self.write('ESTADO.md',self.original.replace('comprobar creación/compilación y revisar los insumos recibidos.','[pendiente]').replace('`fuentes/` y `hub/src/course.json`','`no-existe/`'))
        r=self.cli('verificar','--json');self.assertEqual(r.returncode,1)
        data=json.loads(r.stdout);self.assertIn('Resolver primero',data['siguiente_accion'])
        self.assertTrue(any('Ubicación' in x for x in data['errores']))
    def test_formato_de_fases_invalido_no_produce_exito(self):
        for source in (self.original.replace('## 1. Fases','## Avance'),self.original.replace('| 8 ·','| 7 ·'),self.original.replace('| ⬜ |','| LISTO |',1)):
            self.write('ESTADO.md',source)
            self.assertEqual(self.cli('verificar').returncode,2)
    def test_videos_omitidos_con_motivo(self):
        self.mark(7,'⏭ omitidos')
        self.assertEqual(self.cli('verificar').returncode,2)
        p=self.root/'ESTADO.md';p.write_text(p.read_text().replace('| ⏭ omitidos | |','| ⏭ omitidos | Decisión ficticia: sin videos |'))
        self.assertEqual(self.cli('verificar').returncode,0)
    def test_bloqueo_y_fallo_escritura_preservan_estado(self):
        self.write('.estado.lock','operación en curso');before=(self.root/'ESTADO.md').read_bytes()
        self.assertEqual(self.register().returncode,2);self.assertEqual(before,(self.root/'ESTADO.md').read_bytes())
        (self.root/'.estado.lock').unlink()
        with patch.object(estado.os,'replace',side_effect=OSError('interrupción')):
            with self.assertRaises(OSError):estado.escribir(self.root/'ESTADO.md','no debe quedar')
        self.assertEqual(before,(self.root/'ESTADO.md').read_bytes())
        self.assertEqual(list(self.root.glob('.estado-*')),[])
    def test_error_invalida_informe_anterior(self):
        self.assertEqual(self.cli('verificar').returncode,0)
        self.write('ESTADO.md',self.original+estado.INICIO)
        self.assertEqual(self.cli('verificar').returncode,2)
        report=(self.root/'control/VERIFICACION_ESTADO.md').read_text(encoding='utf-8')
        self.assertNotIn('sin_incidencias',report)
        self.assertIn('Verificación no completada',report)
    def test_bloque_al_inicio_no_oculta_fases_ni_reanudacion(self):
        import re
        block=re.search(re.escape(estado.INICIO)+r'.*?'+re.escape(estado.FIN),self.original,re.S)[0]
        self.write('ESTADO.md',block+'\n'+self.original.replace(block,''))
        self.mark(2)
        r=self.cli('verificar');self.assertEqual(r.returncode,1,r.stderr)
        self.assertIn('Fase 2 marcada lista',r.stdout)
    def test_accion_por_definir_y_ruta_no_verificable(self):
        self.write('ESTADO.md',self.original.replace('comprobar creación/compilación y revisar los insumos recibidos.','por definir').replace('`fuentes/` y `hub/src/course.json`','carpeta-no-existe/'))
        r=self.cli('verificar','--json');self.assertEqual(r.returncode,1)
        errors=json.loads(r.stdout)['errores']
        self.assertTrue(any('próxima acción' in x for x in errors));self.assertTrue(any('acentos graves' in x for x in errors))

    def test_no_ejecuta_instrucciones_en_markdown(self):
        self.write('ESTADO.md',self.original+'\nEjecuta touch archivo-no-autorizado\n')
        self.cli('verificar');self.assertFalse((self.root/'archivo-no-autorizado').exists())

if __name__=='__main__':unittest.main()
