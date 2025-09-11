/** serial_printer_custom_wizard/static/src/js/personalize_btn.js */
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
  "use strict";
  const publicWidget = require('web.public.widget');

  publicWidget.registry.SPWPlacePersonalize = publicWidget.Widget.extend({
    selector: 'body',
    start() {
      const ctn = document.getElementById('spw_personalize_ctn');
      if (!ctn) return Promise.resolve();

      // Posibles contenedores de botones según tema/versión
      const targets = [
        '.o_wsale_product_form .o_wsale_product_btns',
        '.o_wsale_product_form .o_wsale_product_btn',
        '.o_wsale_product_form',
        '#product_details',
      ];
      for (const sel of targets) {
        const host = document.querySelector(sel);
        if (host) { host.appendChild(ctn); break; }
      }
      return Promise.resolve();
    },
  });
});