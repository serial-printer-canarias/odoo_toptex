/** @odoo-module **/
odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.SPWAddCustomizeBtn = publicWidget.Widget.extend({
        selector: 'form.o_wsale_product_form',
        start() {
            // 1) Localizamos el product.template id
            const $form = this.$el;
            let tmplId = $form.find('input[name="product_id"]').val(); // Odoo suele ponerlo aquí
            if (!tmplId) {
                const $holder = $form.closest('[data-oe-model="product.template"]');
                tmplId = $holder.length ? $holder.data('oe-id') : null;
            }
            if (!tmplId) return this._super(...arguments);

            // 2) Evitamos duplicar botón
            if ($form.find('.spw-btn-personalizar').length) {
                return this._super(...arguments);
            }

            // 3) URL con el editor APAGADO
            const href = `/personalizar/${tmplId}?enable_editor=0`;

            // 4) Creamos e insertamos el botón junto a "Añadir al carrito"
            const $btn = $('<a/>', {
                class: 'btn btn-outline-primary spw-btn-personalizar ms-2',
                href: href,
                text: 'Personalizar'
            });

            const $btnBar = $form.find('.o_wsale_product_btn').first();
            if ($btnBar.length) {
                $btnBar.append($btn);
            } else {
                $form.append($btn);
            }

            return this._super(...arguments);
        },
    });
});