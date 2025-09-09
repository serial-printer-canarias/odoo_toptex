/** @odoo-module **/

odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';
    const domReady = require('web.dom_ready');

    domReady(function () {
        // Marca visual para comprobar que el JS se cargó
        if (!document.getElementById('spw_probe')) {
            const probe = document.createElement('div');
            probe.id = 'spw_probe';
            probe.textContent = 'SPW JS OK';
            probe.style.position = 'fixed';
            probe.style.bottom = '8px';
            probe.style.right = '8px';
            probe.style.padding = '4px 8px';
            probe.style.fontSize = '12px';
            probe.style.background = '#eef';
            probe.style.border = '1px solid #99f';
            probe.style.borderRadius = '6px';
            probe.style.zIndex = '99999';
            document.body.appendChild(probe);
            setTimeout(() => probe.remove(), 4000);
        }

        // Solo en ficha de producto (formulario de "add to cart")
        const form = document.querySelector('form.o_wsale_product_form, form[action*="/shop/cart/update"]');
        if (!form) return;

        // Evitar duplicado
        if (document.getElementById('spw_customize_btn')) return;

        // Intentar sacar el id del product template desde la URL /shop/slug-123
        const m = window.location.pathname.match(/-(\d+)(?:\/)?$/);
        const tmplId = m ? m[1] : null;
        if (!tmplId) return;

        // Colocar el botón junto al botón de añadir al carrito
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