odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    function ready(fn) {
        if (document.readyState !== 'loading') { fn(); }
        else document.addEventListener('DOMContentLoaded', fn);
    }

    function firstSelector(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    function getProductId() {
        // En Odoo 17 suele existir este hidden en el formulario
        const pidInput = document.querySelector('form[action*="/shop/cart/update"] input[name="product_id"]');
        if (pidInput && pidInput.value) return pidInput.value;

        // Fallback: /shop/product/<slug>-<id>
        const m = window.location.pathname.match(/\/shop\/product\/.+-(\d+)$/);
        return m ? m[1] : null;
    }

    ready(function () {
        const pid = getProductId();
        if (!pid) return;

        // Evitar duplicados
        if (document.getElementById('spw_customize_btn')) return;

        // Contenedores comunes según tema
        const container = firstSelector([
            '.o_wsale_product_information', // tema estándar
            '.o_wsale_product_page',
            '#product_details',
            '.product_main',
        ]);
        if (!container) return;

        // Buscar el bloque de botones (debajo del "Add to cart")
        const addToCart = container.querySelector('button[name="add_to_cart"], a[href*="/shop/cart/update"]');
        const buttonHost = addToCart ? addToCart.parentElement : container;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-primary ms-2';
        btn.href = `/spw/personalizar/${pid}`;
        btn.textContent = 'Personalizar';

        buttonHost.appendChild(btn);
    });
});