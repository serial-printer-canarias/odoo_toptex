odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    // Ejecuta cuando el DOM está listo (esto hace que Odoo "requiera" el módulo)
    require('web.dom_ready');

    function getProductIdFromUrl() {
        // /shop/slug-del-producto-305  ->  305
        const m = window.location.pathname.match(/-(\d+)(?:$|[/?#])/);
        return m ? m[1] : null;
    }

    function insertButton() {
        // Solo en páginas de producto de eCommerce
        if (!/\/shop\//.test(window.location.pathname)) return;

        const pid = getProductIdFromUrl();
        if (!pid) return;

        // Evitar duplicados
        if (document.getElementById('spw_customize_btn')) return;

        // Localizar el botón "Add to cart" (robusto para temas distintos)
        const addToCartBtn = document.querySelector(
            'form[action*="/shop/cart/update"] button[type="submit"], ' +
            'button#add_to_cart, ' +
            '.o_wsale_product_btn button[type="submit"]'
        );

        // Contenedor alternativo si no encontramos el botón
        const fallbackContainer = document.querySelector(
            '#product_details, .o_wsale_product_information, .product_main, #wrap .container, #wrap'
        );

        const where = addToCartBtn ? addToCartBtn.parentElement : fallbackContainer;
        if (!where) return;

        // Crear el botón
        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-primary ms-2';
        btn.href = '/personalizacion/' + pid;
        btn.textContent = 'Personalizar';

        if (addToCartBtn) {
            addToCartBtn.insertAdjacentElement('afterend', btn);
        } else {
            where.appendChild(btn);
        }
    }

    // Insertar ahora…
    insertButton();

    // …y reintentar si el DOM se re-renderiza (cambios de variante, etc.)
    const observer = new MutationObserver(() => insertButton());
    observer.observe(document.body, { childList: true, subtree: true });
});