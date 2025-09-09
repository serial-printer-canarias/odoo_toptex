odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    function firstSelector(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    function getProductIdFromUrl() {
        // URLs típicas: /shop/product/slug-305 o /shop/product/305
        const m = window.location.pathname.match(/\/shop\/product\/(?:.*-)?(\d+)(?:\/)?$/);
        return m ? m[1] : null;
    }

    function addButton() {
        const pid = getProductIdFromUrl();
        if (!pid) return;

        // Busca un contenedor fiable en muchas plantillas
        const container = firstSelector([
            '#product_details',                              // clásico
            '.o_wsale_product_information',                  // v16+
            '.o_wsale_product_page',                         // genérico
            '.product_main', '.container', '#wrap'
        ]);
        if (!container) return;

        // Evita duplicados
        if (document.querySelector('#spw_customize_btn')) return;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-secondary my-3';
        btn.href = '/personalizacion/' + pid;
        btn.textContent = 'Personalizar';

        // Inserta al principio del contenedor
        container.insertBefore(btn, container.firstChild);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addButton);
    } else {
        addButton();
    }
});