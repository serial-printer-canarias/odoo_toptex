// Sonda simple para comprobar carga de assets y evitar ReferenceError
window._sp = window._sp || {};
_sp.debug = _sp.debug || {
  log: (...a) => console.log('[SP]', ...a),
  ok:  (msg) => console.log('%c[SP] ' + msg, 'color:#0a0'),
  warn:(msg) => console.warn('[SP]', msg),
};

_sp.debug.ok('web.assets_frontend cargado ✅');