/** Always show "Personalizar" and point to current variant id */
odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    const CustomizeButton = publicWidget.Widget.extend({
        selector: 'body',

        start() {
            this._ensureButton();
            // Reintenta cuando cambian variantes o el DOM
            document.body.addEventListener('change', (ev) => {
                if (ev.target && ev.target.name === 'product_id') this._ensureButton();
            });
            this._obs = new MutationObserver(() => this._ensureButton());
            const root = document.querySelector('.o_wsale_product_page_main') || document.body;
            this._obs.observe(root, { childList: true, subtree: true });
            return this._super(...arguments);
        },

        _getVariantId() {
            const el = document.querySelector('input[name="product_id"]');
            return el && el.value ? parseInt(el.value, 10) : null;
        },

        _container() {
            return document.querySelector('.o_wsale_product_btns,.o_wsale_product_btn') ||
                   document.querySelector('form[action*="/shop/cart/update"]');
        },

        _ensureButton() {
            const cont = this._container();
            const vid = this._getVariantId();
            if (!cont || !vid) return;

            let btn = document.getElementById('spw_customize_btn');
            if (!btn) {
                btn = document.createElement('a');
                btn.id = 'spw_customize_btn';
                btn.className = 'btn btn-outline-primary ms-2';
                btn.innerHTML = '<i class="fa fa-magic me-1"></i><span>Personalizar</span>';
                cont.appendChild(btn);
            }
            btn.href = `/personalizar/${vid}`;
        },
    });

    publicWidget.registry.spwCustomizeButton = CustomizeButton;
    return CustomizeButton;
});