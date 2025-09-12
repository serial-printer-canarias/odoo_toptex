/** Abre el personalizador con los parámetros correctos */
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.SPWPersonalizeButton = publicWidget.Widget.extend({
        selector: '#spw_personalize_btn',
        events: { 'click': '_onClick' },

        _onClick: function (ev) {
            ev.preventDefault();

            const $form = $('form.o_wsale_product_form, form#product_form');

            // Variante seleccionada
            const variantId = ($form.find('input.product_id:checked').val()
                            || $form.find('input[name="product_id"]').val()
                            || null);

            // Template por si lo necesitas
            const tmplId = ($form.find('input[name="product_template_id"]').val()
                         || $form.data('product-template-id')
                         || null);

            // Imagen actual en la ficha
            const img = document.querySelector('.o_wsale_product_img img, img.js_product_img, img.product_detail_img');
            const imgUrl = img ? img.getAttribute('src') : null;

            const params = new URLSearchParams();
            if (variantId) params.set('variant_id', variantId);
            if (tmplId) params.set('tmpl_id', tmplId);
            if (imgUrl) params.set('image', imgUrl);

            // IMPORTANTE: SIEMPRE a /spw/customize (sin ID al final)
            const url = '/spw/customize' + (params.toString() ? ('?' + params.toString()) : '');
            window.location.href = url;
        },
    });
});