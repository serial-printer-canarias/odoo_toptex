/** @odoo-module **/

odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';
    const domReady = require('web.dom_ready');

    function badge(text, color) {
        const el = document.createElement('div');
        el.id = 'spw_probe';
        el.textContent = text;
        el.style.cssText = `
            position:fixed;bottom:8px;right:8px;z-index:99999;
            padding:6px 10px;border-radius:6px;border:1px solid #333;
            background:${color||'#eef'};font:12px/1.3 system-ui;
        `;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 6000);
    }

    domReady(function () {
        // 1) PRUEBA VISUAL: si ves este badge, el JS está cargando.
        badge('SPW JS OK', '#dff0ff');

        // 2) Comprobamos que estamos en una ficha de producto (hay un form de compra).
        const form = document.querySelector(
            'form.o_wsale_product_form, #product_details form, .o_wsale_product_page form'
        );
        if (!form) { console.warn('SPW: no form found'); return; }

        // 3) Evitar duplicados
        if (document.getElementById('spw_customize_btn')) return;

        // 4) Obtener el id del template desde la URL /shop/slug-<id>
        const m = window.location.pathname.match(/-(\d+)(?:\/)?$/);
        const tmplId = m ? m[1] : null;
        if (!tmplId) { console.warn('SPW: no template id in URL'); badge('SPW: sin ID', '#ffe3e3'); return; }

        // 5) Buscar el botón "Add to cart" y colocar al lado nuestro botón
        let anchor = form.querySelector('button[type="submit"], .o_add_to_cart');
        anchor = anchor ? anchor.parentElement : form;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.href = `/personalizar/${tmplId}`;
        btn.className = 'btn btn-outline-primary ms-2';
        btn.style.marginLeft = '8px';
        btn.textContent = 'Personalizar';
        anchor.appendChild(btn);
    });
});