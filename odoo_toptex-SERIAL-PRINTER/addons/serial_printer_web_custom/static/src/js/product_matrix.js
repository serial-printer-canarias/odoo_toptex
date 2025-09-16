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
            const calls = [];
            $card.find('input.qty-input').each(function () {
                const qty = parseFloat(this.value || '0');
                const product_id = parseInt(this.dataset.variantId || '0', 10);
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