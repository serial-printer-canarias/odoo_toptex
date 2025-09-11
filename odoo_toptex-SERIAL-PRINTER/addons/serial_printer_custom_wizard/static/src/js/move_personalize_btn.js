/** Mueve el botón #spw_personalize_btn justo después del botón "Añadir al carrito" */
odoo.define('serial_printer_custom_wizard.move_personalize_btn', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.spwMovePersonalizeBtn = publicWidget.Widget.extend({
    selector: '.o_wsale_product_page, .oe_website_sale',
    start() {
      const btn = document.getElementById('spw_personalize_btn');
      if (!btn) return;

      const candidates = [
        '.o_wsale_product_form .o_add_to_cart',        // Odoo 18 clásico
        '.o_wsale_product_form .js_add_cart_json',     // alternativo
        '#o_wsale_add_to_cart',                        // fallback
      ];
      const addBtn = document.querySelector(candidates.join(', '));
      if (addBtn && addBtn.parentNode) {
        addBtn.parentNode.insertBefore(btn, addBtn.nextSibling);
        btn.classList.remove('btn-outline-primary');
        btn.classList.add('btn-secondary','ms-2','mt-0');
      }
    },
  });
});