/** @odoo-module **/
window._sp = window._sp || {};
_sp.debug = _sp.debug || {};
_sp.debug.ok = true;
_sp.debug.blocks = () =>
  [...document.querySelectorAll('.js_product .js_attributes [data-attribute_name]')]
    .map(b => ({ name: b.getAttribute('data-attribute_name'), radios: b.querySelectorAll('input[type="radio"]').length }));

console.log("[SP] web.assets_frontend cargado ✅");