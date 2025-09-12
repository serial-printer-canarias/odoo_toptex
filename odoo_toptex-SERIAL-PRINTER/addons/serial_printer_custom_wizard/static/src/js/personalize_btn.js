/** serial_printer_custom_wizard/static/src/js/personalize_btn.js **/
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    publicWidget.registry.SPWPersonalizeBtn = publicWidget.Widget.extend({
        selector: '#spw_personalize_btn',
        events: { 'click': '_onClick' },

        _onClick(ev) {
            ev.preventDefault();
            const btn = ev.currentTarget;
            const productId = btn.dataset.productId; // viene del template
            // Odoo siempre tiene un input hidden con el variant/product_id seleccionado
            const variantInput = document.querySelector('form input[name="product_id"]');
            const variantId = variantInput ? variantInput.value : null;

            if (productId) {
                const url = `/spw/customize/${productId}` + (variantId ? `?variant_id=${variantId}` : '');
                window.location.href = url;
            }
        },
    });
});