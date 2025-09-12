/** @odoo-module **/
import publicWidget from 'web.public.widget';

publicWidget.registry.spwPersonalizeBtn = publicWidget.Widget.extend({
    selector: '#spw_personalize_btn',
    events: {
        'click': '_onClick',
    },

    _onClick(ev) {
        ev.preventDefault();

        // Form estándar de la ficha de producto
        const $form = $('form.o_add_to_cart_form, form[name="add_to_cart"]');

        // En Odoo 16/17/18 suele estar en product_id
        const variantId =
            $form.find('input[name="product_id"]').val() ||
            $form.find('input[name="product_product_id"]').val();

        const tmplId =
            $form.find('input[name="product_template_id"]').val() ||
            $form.find('input[name="product_template"]').val();

        // Usamos la ruta sin conflicto
        let url = '/spw/customize';
        const params = [];
        if (variantId) {
            params.push('variant_id=' + encodeURIComponent(variantId));
        } else if (tmplId) {
            params.push('tmpl_id=' + encodeURIComponent(tmplId));
        }
        if (params.length) {
            url += '?' + params.join('&');
        }
        window.location.href = url;
    },
});