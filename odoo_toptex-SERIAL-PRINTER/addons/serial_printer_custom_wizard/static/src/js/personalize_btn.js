// serial_printer_custom_wizard/static/src/js/personalize_btn.js
// Vanilla JS seguro: no usa el cargador de módulos de Odoo
(function () {
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest('#spw_personalize_btn');
    if (!a) return;

    ev.preventDefault();
    try {
      var form = a.closest('form') ||
                 document.querySelector('form[action="/shop/cart/update"]') ||
                 document.querySelector('form.js_add_cart_json');

      var pidInput = form ? form.querySelector('input[name="product_id"]') : null;
      var variantId = pidInput ? pidInput.value : '';
      var tmplId = a.getAttribute('data-tmpl-id') || '';

      if (!tmplId) return;

      var url = '/spw/customize/' + tmplId + (variantId ? ('?variant_id=' + encodeURIComponent(variantId)) : '');
      window.location.href = url;
    } catch (e) {
      console.error('SPW personalize button error:', e);
    }
  }, false);
})();