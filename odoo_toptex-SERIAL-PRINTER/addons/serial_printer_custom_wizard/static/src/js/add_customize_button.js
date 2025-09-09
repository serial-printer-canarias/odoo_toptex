/** @odoo-module **/

odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';
    const domReady = require('web.dom_ready');

    domReady(function () {
        // Estamos en la ficha de producto si hay un form de "add to cart"
        const form = document.querySelector('form.o_wsale_product_form, form[action*="/shop/cart/update"]');
        if (!form) {
            return; // no es una página de producto
        }

        // Evitar duplicados
        if (document.getElementById('spw_customize_btn')) {
            return;
        }

        // Obtener el product_template_id desde la URL tipo /shop/slug-305
        const m = window.location.pathname.match(/-(\d+)(?:\/)?$/);
        const tmplId = m ? m[1] : null;
        if (!tmplId) {
            return; // no pudimos extraer el id
        }

        // Colocar el botón junto al "Add to cart"
        let target = form.querySelector('button[type="submit"], .o_add_to_cart');
        target = target ? target.parentElement : form;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-primary ms-2';
        btn.href = `/personalizar/${tmplId}`;
        btn.textContent = 'Personalizar';

        target.appendChild(btn);
    });
});