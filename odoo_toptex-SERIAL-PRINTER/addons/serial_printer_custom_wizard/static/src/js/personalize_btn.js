/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.SPWPersonalizeBtn = publicWidget.Widget.extend({
    selector: '#spw_personalize_btn',
    events: {
        click: '_onClick',
    },

    /**
     * Redirige al customizador con el product_id y el variant_id seleccionado
     */
    _onClick(ev) {
        ev.preventDefault();
        const productId = Number(ev.currentTarget.dataset.productId || 0);

        // En el formulario hay un hidden con el variant_id actual
        let variantId = 0;
        const hiddenVariant = document.querySelector('input[name="product_id"]');
        if (hiddenVariant) {
            variantId = Number(hiddenVariant.value || 0);
        }

        const url = `/spw/customize/${productId}${variantId ? `?variant_id=${variantId}` : ''}`;
        window.location.href = url;
    },
});

export default publicWidget.registry.SPWPersonalizeBtn;