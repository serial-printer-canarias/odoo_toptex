// Sonda de carga de assets (segura)
window._sp = window._sp || {};
_sp.debug = _sp.debug || {
  log:  (...a) => console.log('[SP]', ...a),
  ok:   (m) => console.log('%c[SP] ' + m, 'color:#0a0'),
  warn: (m) => console.warn('[SP]', m),
};
_sp.debug.ok('web.assets_frontend cargado ✅');