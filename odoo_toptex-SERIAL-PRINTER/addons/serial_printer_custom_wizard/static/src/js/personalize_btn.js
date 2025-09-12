/** @odoo-module **/
import publicWidget from 'web.public.widget';

publicWidget.registry.spwPersonalizeBtn = publicWidget.Widget.extend({
    selector: '#spw_personalize_btn',
    events: {
        'click': '_onClick',
    },

    _onClick(ev) {
        ev.preventDefault();

        // Localizamos el form estándar de Odoo
        const $form = $('form.o_add_to_cart_form, form[name="add_to_cart"]');

        // En Odoo 16/17/18 el id de variante vive en input[name="product_id"]
        let variantId = $form.find('input[name="product_id"]').val()
            || $form.find('input[name="product_product_id"]').val();

        // Si no hay variante, como fallback mandamos el template
        const tmplId = $form.find('input[name="product_template_id"]').val()
            || $form.find('input[name="product_template"]').val();

        let url = '/shop/customize';
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