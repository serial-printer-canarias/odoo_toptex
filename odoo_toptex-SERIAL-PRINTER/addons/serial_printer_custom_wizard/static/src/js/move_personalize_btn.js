/** serial_printer_custom_wizard/static/src/js/move_personalize_btn.js **/
odoo.define('serial_printer_custom_wizard.move_personalize_btn', function (require) {
    'use strict';
    const domReady = require('web.dom_ready');
    domReady(() => {
        // Dejamos el botón donde lo coloca la vista. No mover para evitar conflictos.
        const btn = document.getElementById('spw_personalize_btn');
        if (!btn) return;
    });
});