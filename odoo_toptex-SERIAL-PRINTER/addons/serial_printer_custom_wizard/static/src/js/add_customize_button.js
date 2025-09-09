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
        const m = window.location.pathname.match(/\/shop\/product\/(?:.*-)?(\d+)(?:\/)?$/);
        return m ? m[1] : null;
    }

    function addButton() {
        const pid = getProductIdFromUrl();
        if (!pid) return;

        // Contenedores típicos según tema
        const container = firstSelector([
            '#product_details',
            '.o_wsale_product_information',
            '.o_wsale_product_page',
            '.product_main',
            '#wrap .container',
            '#wrap'
        ]);
        if (!container) return;

        if (document.querySelector('#spw_customize_btn')) return;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-secondary my-3';
        btn.href = '/personalizacion/' + pid;
        btn.textContent = 'Personalizar';

        // Si existe el botón de carrito, colócalo después para que se vea siempre
        const addToCart = document.querySelector('form[action*="/shop/cart/update"] button[type="submit"]');
        if (addToCart && addToCart.parentElement) {
            addToCart.parentElement.insertAdjacentElement('afterend', btn);
        } else {
            container.insertBefore(btn, container.firstChild);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addButton);
    } else {
        addButton();
    }
});