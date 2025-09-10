odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    function firstSelector(list) {
        for (var i = 0; i < list.length; i++) {
            var el = document.querySelector(list[i]);
            if (el) return el;
        }
        return null;
    }

    function getProductIdFromUrl() {
        // /shop/product/slug-123  ó con / al final
        var m = window.location.pathname.match(/\/shop\/product\/[^/]*-(\d+)(?:\/|$)/);
        return m ? m[1] : null;
    }

    function addButton() {
        var pid = getProductIdFromUrl();
        if (!pid) return;

        var container = firstSelector([
            '.o_wsale_product_information', // v17
            '#product_details',             // v15/16
            '.o_wsale_product_page',
            '.product_main',
            '#wrap .container',
            '#wrap'
        ]);
        if (!container) return;

        if (document.getElementById('spw_customize_btn')) return;

        var btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-secondary mt-3 w-100';
        btn.textContent = 'Personalizar';
        btn.href = '/spw/personalizar/' + pid;

        // intentar ponerlo justo tras el wishlist o cerca del Add to cart
        var wishlistRow = container.querySelector('a[href*="wishlist"]');
        if (wishlistRow && wishlistRow.parentElement) {
            wishlistRow.parentElement.parentElement.insertBefore(btn, wishlistRow.parentElement.nextSibling);
        } else {
            var addToCart = container.querySelector('form[action*="/shop/cart/update"] .btn-primary, .o_wsale_product_information .btn-primary');
            if (addToCart && addToCart.parentElement) {
                addToCart.parentElement.appendChild(btn);
            } else {
                container.appendChild(btn);
            }
        }

        // insignia de depuración para saber que el JS cargó
        if (!document.getElementById('spw_js_ok')) {
            var badge = document.createElement('div');
            badge.id = 'spw_js_ok';
            badge.textContent = 'SPW JS OK';
            badge.style.cssText = 'position:fixed;right:8px;bottom:8px;padding:6px 10px;border-radius:8px;background:#e9eefc;border:1px solid #d0d7ff;font:12px/1.2 system-ui;z-index:9999';
            document.body.appendChild(badge);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addButton);
    } else {
        addButton();
    }
});