odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',
        events: { 'click .add-to-cart-btn': '_onAddToCartColor' },
        _onAddToCartColor: function (ev) {
            ev.preventDefault();
            const $btn = $(ev.currentTarget);
            const $card = $btn.closest('.border.rounded.p-3');
            const $inputs = $card.find('input.qty-input');
            const calls = [];
            $inputs.each(function () {
                const $inp = $(this);
                const qty = parseFloat($inp.val());
                const product_id = parseInt($inp.data('variant-id'), 10);
                if (qty > 0 && product_id) {
                    calls.push(ajax.jsonRpc('/shop/cart/update_json', 'call', {
                        product_id, add_qty: qty, display: false,
                    }));
                }
            });
            if (!calls.length) return;
            Promise.all(calls).then(() => window.location.reload());
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});