/** @odoo-module **/
import publicWidget from 'web.public.widget';

publicWidget.registry.SpwPersonalizeButton = publicWidget.Widget.extend({
    selector: '#spw_personalize_btn',
    events: { click: '_onClick' },

    _onClick(ev) {
        ev.preventDefault();
        // Leemos SIEMPRE la variante del input hidden estándar
        const variantInput = document.querySelector('form input[name="product_id"]');
        const variantId = variantInput && variantInput.value;
        if (!variantId) {
            console.warn('[SPW] No se encontró product_id en el formulario.');
            return;
        }
        window.location.href = `/spw/customize/${variantId}`;
    },
});