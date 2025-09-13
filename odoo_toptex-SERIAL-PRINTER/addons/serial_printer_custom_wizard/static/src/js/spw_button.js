/** serial_printer_custom_wizard/static/src/js/spw_button.js **/
odoo.define('serial_printer_custom_wizard.spw_button', function (require) {
    'use strict';

    const publicRoot = require('web.public.root');

    publicRoot.whenReady(() => {
        document.addEventListener('click', (ev) => {
            const btn = ev.target.closest('#spw_personalize_btn');
            if (!btn) return;

            ev.preventDefault();

            // 1) Sacar la variante seleccionada del <form> (input hidden name="product_id")
            const form = btn.closest('form') || document.querySelector("form[action*='/shop']");
            const variantInput = form && form.querySelector("input[name='product_id']");
            const variantId = variantInput ? variantInput.value : null;

            // 2) Sacar el product.template id
            let tmplId = btn.dataset.productTemplateId || null;
            if (!tmplId) {
                // Fallback: parsear el ID del final de la URL /shop/slug-<id>
                const last = (window.location.pathname.split('/').filter(Boolean).pop() || '');
                const m = last.match(/-(\d+)$/);
                if (m) tmplId = m[1];
            }

            if (!tmplId) {
                console.error('SPW: no se pudo obtener el product.template id');
                return;
            }

            // 3) Construir URL del configurador (mantiene la variante si existe)
            const url = `/spw/customize/${tmplId}${variantId ? `?variant_id=${variantId}` : ''}`;
            window.location.href = url;
        });
    });
});