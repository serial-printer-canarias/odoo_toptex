/** serial_printer_web_custom - product_matrix.js
 *  Añade al carrito todas las tallas con cantidad > 0 del bloque del color pulsado.
 */
odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',
        events: {
            'click .add-to-cart-btn': '_onAddToCartColor',
        },

        _onAddToCartColor: function (ev) {
            ev.preventDefault();
            const $btn = $(ev.currentTarget);
            const $card = $btn.closest('.border.rounded.p-3');
            const $inputs = $card.find('input.qty-input');
            const calls = [];

            $inputs.each(function () {
                const $inp = $(this);
                const qty = parseFloat($inp.val());
                const variantId = parseInt($inp.data('variant-id'), 10);
                if (qty > 0 && variantId) {
                    calls.push(
                        ajax.jsonRpc('/shop/cart/update_json', 'call', {
                            product_id: variantId,
                            add_qty: qty,
                            display: false,
                        })
                    );
                }
            });

            if (!calls.length) {
                $btn.addClass('btn-outline-secondary');
                setTimeout(() => $btn.removeClass('btn-outline-secondary'), 800);
                return;
            }

            Promise.all(calls).then(() => {
                window.location.reload(); // refresca cantidades y mini-carrito
            }).catch(() => {
                $btn.removeClass('btn-primary').addClass('btn-danger');
                setTimeout(() => $btn.removeClass('btn-danger').addClass('btn-primary'), 2000);
            });
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});