/** @odoo-module */
odoo.define('serial_printer_custom_wizard.move_personalize_btn', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');

  publicWidget.registry.SpwMovePersonalizeBtn = publicWidget.Widget.extend({
    selector: 'body',

    start() {
      const btn = document.getElementById('spw_personalize_btn');
      const slot = document.getElementById('spw_personalize_slot');
      if (!btn || !slot) {
        return this._super(...arguments);
      }

      // Posibles contenedores según versión/tema
      const targets = [
        ".o_wsale_product_actions",         // v17/18 (tema estándar)
        ".o_wsale_product_btns",            // v16
        "form.o_wsale_buy_form .o_wsale_product_actions",
        "form.o_wsale_buy_form .o_wsale_product_btns",
        "form.o_wsale_buy_form",            // último recurso
      ];

      let target = null;
      for (const sel of targets) {
        target = document.querySelector(sel);
        if (target) break;
      }

      if (target) {
        target.appendChild(btn);
        btn.classList.add('mt-3');
        slot.classList.remove('d-none');
      } else {
        // Si no encontramos nada, mostramos el botón al final del wrap
        slot.classList.remove('d-none');
      }
      return this._super(...arguments);
    },
  });
});