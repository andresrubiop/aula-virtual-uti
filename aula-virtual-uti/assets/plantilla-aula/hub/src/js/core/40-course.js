/* Datos del curso: unidades e hitos. Fuente única: hub/src/course.json (build.py lo publica en window.HUB_COURSE).
   Hora de Ecuador continental (UTC−05:00). Fechas del sílabo UTI B26 v1.0 (05/10/2026). */
(function () {
  'use strict';
  const data = window.HUB_COURSE || { units: [], deadlines: [] };
  const TZ = '-05:00';

  window.Hub.course = {
    code: data.code,
    units: data.units,
    deadlines: (data.deadlines || []).map(d => ({ ...d, when: new Date(`${d.when}:00${TZ}`) }))
      .sort((a, b) => a.when - b.when),
    next(now = new Date()) {
      return this.deadlines.find(d => d.when.getTime() > now.getTime()) || null;
    },
    unit(id) { return this.units.find(u => u.id === id) || null; },
  };
})();
