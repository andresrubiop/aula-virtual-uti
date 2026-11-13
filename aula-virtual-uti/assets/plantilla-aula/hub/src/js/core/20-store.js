/* Almacenamiento local seguro (solo comodidades por navegador: progreso, tema, respuestas).
   Si localStorage no está disponible (ventana privada, Blackboard con iframe restringido) todo sigue funcionando. */
(function () {
  'use strict';
  const PREFIX = '@@KEY@@:';   // build.py pone la clave del curso (course.json → key)
  const mem = {};
  window.Hub.store = {
    get(key, fallback) {
      try {
        const v = localStorage.getItem(PREFIX + key);
        return v == null ? (key in mem ? mem[key] : fallback) : JSON.parse(v);
      } catch (e) { return key in mem ? mem[key] : fallback; }
    },
    set(key, value) {
      mem[key] = value;
      try { localStorage.setItem(PREFIX + key, JSON.stringify(value)); } catch (e) { /* sin persistencia */ }
    },
    remove(key) {
      delete mem[key];
      try { localStorage.removeItem(PREFIX + key); } catch (e) { /* nada */ }
    },
  };
})();
