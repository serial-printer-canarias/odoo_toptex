odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    function firstSelector(list) {
        for (const s of list) {
            const el = document.querySelector(s);
            if (el) return el;
        }
        return null;
    }

    function isProductPage() {
        // Odoo 17 ecommerce
        if (document.querySelector('[data-oe-model="product.template"]')) return true;
        return /\/shop\/.*product/.test(location.pathname);
    }

    const SPW = publicWidget.Widget.extend({
        selector: 'body',

        start() {
            // Garantizamos la píldora aunque se desactive la vista anterior
            if (!document.getElementById('spw-pill')) {
                const p = document.createElement('div');
                p.id = 'spw-pill';
                p.textContent = 'SPW JS OK';
                p.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:99999;background:#e6eefc;border:1px solid #bcd;padding:6px 10px;border-radius:8px;font-size:12px;';
                document.body.appendChild(p);
            }
            if (isProductPage()) {
                this._placeButton();
                // Recolocar si cambian variantes / recarga parcial
                document.addEventListener('change', (ev) => {
                    if (ev.target.closest('form.js_product')) this._placeButton();
                });
            }
            return this._super(...arguments);
        },

        _placeButton() {
            if (document.getElementById('spw_customize_btn')) return;

            const container =
                firstSelector([
                    '.o_wsale_product_buy',           // contenedor de compra
                    '.o_wsale_product_page .product_main',
                    '#product_details',
                    '.o_wsale_product_page',
                    '#wrap'
                ]) || document.body;

            const btn = document.createElement('button');
            btn.id = 'spw_customize_btn';
            btn.type = 'button';
            btn.className = 'btn btn-outline-secondary mt-3';
            btn.textContent = 'Personalizar';

            // Insertar lo más cerca posible del Add to cart
            const addToCart =
                firstSelector(['.o_wsale_add_to_cart', '.o_wsale_product_buy', 'form.js_product']);
            (addToCart && addToCart.parentElement ? addToCart.parentElement : container)
                .appendChild(btn);

            const pid = this._currentProductId();
            btn.addEventListener('click', () => {
                // Ruta simple de prueba; cámbiala luego por tu página real
                const dest = pid ? `/spw/personalizar/${pid}` : `/spw/personalizar`;
                window.location.href = dest;
            });
        },

        _currentProductId() {
            const main = document.querySelector('[data-oe-model="product.template"]');
            if (main && main.dataset.oeId) return main.dataset.oeId;
            const m = window.location.pathname.match(/(\d+)(?:-[^\/]*)?$/);
            return m ? m[1] : null;
        },
    });

    publicWidget.registry.spwCustomizeButton = SPW;
    return SPW;
});