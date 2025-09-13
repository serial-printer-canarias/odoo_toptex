/** serial_printer_custom_wizard/static/src/js/spw_button.js **/
odoo.define('serial_printer_custom_wizard.spw_button', function (require) {
    'use strict';

    const publicRoot = require('web.public.root');

    function getVariantIdFromForm() {
        const form = document.querySelector("form[action*='/shop']");
        const hidden = form && form.querySelector("input[name='product_id']");
        return hidden ? hidden.value : null;
    }

    publicRoot.whenReady(() => {
        document.addEventListener('click', (ev) => {
            const btn = ev.target.closest('#spw_personalize_btn');
            if (!btn) return;

            ev.preventDefault();

            const tmplId = btn.dataset.productTemplateId || null;
            const variantId = btn.dataset.variantId || getVariantIdFromForm();

            if (!tmplId || tmplId === '0') {
                console.error('SPW: Falta data-product-template-id en el botón');
                return;
            }

            const url =
                `/spw/customize/${encodeURIComponent(tmplId)}` +
                (variantId ? `?variant_id=${encodeURIComponent(variantId)}` : '');

            window.location.assign(url);
        });
    });
});