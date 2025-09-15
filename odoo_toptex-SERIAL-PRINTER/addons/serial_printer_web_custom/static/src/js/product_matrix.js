/**  serial_printer_web_custom / product_matrix.js
 *   Añade al carrito todas las tallas con cantidad > 0 del color pulsado.
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

        /**
         * Cuando se pulsa el botón de un color:
         * - Lee los inputs .qty-input dentro de esa tarjeta
         * - Hace una llamada /shop/cart/update_json por variante
         */
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
                // Nada que añadir: pequeño feedback visual
                $btn.addClass('btn-outline-secondary');
                setTimeout(() => $btn.removeClass('btn-outline-secondary'), 800);
                return;
            }

            Promise.all(calls).then(() => {
                // Refrescamos para ver carrito y cantidades actualizadas
                window.location.reload();
            }).catch(() => {
                // En caso de error mostramos un feedback básico
                $btn.removeClass('btn-primary').addClass('btn-danger');
                setTimeout(() => $btn.removeClass('btn-danger').addClass('btn-primary'), 2000);
            });
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});