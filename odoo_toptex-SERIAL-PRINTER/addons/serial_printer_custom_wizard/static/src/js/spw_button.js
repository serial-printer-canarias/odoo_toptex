/** @odoo-module **/

odoo.define('serial_printer_custom_wizard.spw_button', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.SpwPersonalizeBtn = publicWidget.Widget.extend({
        selector: '#spw_personalize_btn',
        events: {
            'click': '_onClick',
        },

        /**
         * Click en "Personalizar"
         */
        _onClick: function (ev) {
            ev.preventDefault();

            const btn = ev.currentTarget;
            const templateId = btn.dataset.productTemplateId;
            if (!templateId) {
                console.warn('SPW: Falta data-product-template-id en el botón.');
                return;
            }

            // Tomamos la variante seleccionada del <form> donde está el botón
            const $form = $(btn).closest('form');
            const $variantInput = $form.find('input[name="product_id"]');
            const variantId = $variantInput.length ? $variantInput.val() : '';

            // Construimos URL de tu customizer (no tocamos nada más)
            let url = `/spw/customize/${templateId}`;
            if (variantId) {
                url += `?variant_id=${encodeURIComponent(variantId)}`;
            }
            window.location.href = url;
        },
    });

    return publicWidget.registry.SpwPersonalizeBtn;
});