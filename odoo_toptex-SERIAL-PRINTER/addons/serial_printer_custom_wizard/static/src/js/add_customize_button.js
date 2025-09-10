odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    function getProductIdFromUrl() {
        // /shop/slug-305  ó  /shop/product/305
        let m = location.pathname.match(/-(\d+)(?:$|\/)/);
        if (m) return m[1];
        m = location.pathname.match(/\/product\/(\d+)(?:$|\/)/);
        return m ? m[1] : null;
    }

    function firstSelector(list) {
        for (const sel of list) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    function ensureButton() {
        const pid = getProductIdFromUrl();
        if (!pid) return; // no estamos en producto

        if (document.getElementById('spw_customize_btn')) return; // ya existe

        // Sitios típicos donde insertar (según tema)
        const container =
            firstSelector([
                '#product_details',             // theme default
                '.o_wsale_product_information', // otro tema
                '.product_main',                // fallback
                '#wrap .container',
                '#wrap'
            ]) || document.body;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-primary mt-2';
        btn.textContent = 'Personalizar';
        // Cambia la ruta si tu página es distinta:
        btn.href = '/shop/personalizar/' + pid;

        // Si existe el botón de añadir al carrito, lo colocamos a su lado
        const addToCart = document.querySelector('#add_to_cart, .o_add_to_cart, form[action*="/shop/cart/update"]');
        if (addToCart && addToCart.parentElement) {
            addToCart.parentElement.appendChild(btn);
        } else {
            container.appendChild(btn);
        }

        console.log('SPW JS OK: botón insertado');
    }

    function run() {
        try { ensureButton(); } catch (e) { console.error('SPW JS error', e); }
    }

    if (document.readyState !== 'loading') run();
    else document.addEventListener('DOMContentLoaded', run);

    // Reintenta cuando Odoo recarga fragmentos dinámicos
    document.addEventListener('page:loaded', run);
    document.addEventListener('DOMContentUpdated', run);
});