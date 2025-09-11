/** serial_printer_custom_wizard/static/src/js/personalize_btn.js **/
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.spwPersonalizeBtn = publicWidget.Widget.extend({
        selector: '#wrapwrap',

        start() {
            // Posicionar y preparar el botón al cargar
            this._moveBtn();
            this._updateHref();
            // Escuchar cambios de variante (cambios en inputs de la ficha)
            this.el.addEventListener('change', this._updateHref.bind(this), true);
            return this._super(...arguments);
        },

        _btn() {
            return document.getElementById('spw_personalize_btn');
        },

        _tmplId() {
            const btn = this._btn();
            return btn ? (btn.dataset.product_tmpl_id || btn.getAttribute('data-product_tmpl_id')) : null;
        },

        _variantId() {
            // Odoo mantiene el id de variante en un input hidden name="product_id"
            const hidden = document.querySelector('input[name="product_id"]');
            if (hidden && hidden.value) return hidden.value;
            const btn = this._btn();
            return btn ? (btn.dataset.variant_id || '0') : '0';
        },

        _updateHref() {
            const btn = this._btn();
            if (!btn) return;
            const tmplId = this._tmplId();
            const variantId = this._variantId();
            if (tmplId) {
                btn.setAttribute('href', `/spw/customize/${tmplId}?variant_id=${variantId}`);
            }
        },

        _moveBtn() {
            const wrap = document.getElementById('spw_personalize_btn_wrapper');
            if (!wrap) return;

            // Busca un contenedor de acciones junto a "Añadir al carrito"
            const targets = [
                '.o_wsale_product_btn',          // tema estándar
                '.o_wsale_product_buttons',      // variante de tema
                'form.o_add_to_cart_form .o_wsale_product_btn',
                '#product_details .o_wsale_product_btn',
            ];
            for (const sel of targets) {
                const t = document.querySelector(sel);
                if (t) { t.appendChild(wrap); break; }
            }
        },
    });

    return publicWidget.registry.spwPersonalizeBtn;
});