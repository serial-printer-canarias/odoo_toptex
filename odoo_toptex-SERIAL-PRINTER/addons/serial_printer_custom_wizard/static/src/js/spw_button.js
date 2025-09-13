/** @odoo-module **/

odoo.define('serial_printer_custom_wizard.spw_button', function (require) {
  'use strict';

  function init() {
    const btn = document.getElementById('spw_personalize_btn');
    if (!btn) return;

    btn.addEventListener('click', function (ev) {
      // Si no hay variante, dejamos seguir el href base (sigue funcionando)
      const form = btn.closest('form');
      const variantInput = form ? form.querySelector('input[name="product_id"]') : null;
      const variantId = variantInput && variantInput.value ? variantInput.value : null;
      if (!variantId) return; // fallback: sin JS extra, va al href base

      ev.preventDefault();
      const url = new URL(btn.getAttribute('href'), window.location.origin);
      url.searchParams.set('variant_id', variantId);
      window.location.href = url.toString();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
});