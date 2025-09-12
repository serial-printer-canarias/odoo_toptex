/** Personalize button -> abre el personalizador */
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.SPWPersonalizeButton = publicWidget.Widget.extend({
        selector: '#spw_personalize_btn',
        events: {
            'click': '_onClick',
        },

        _onClick: function (ev) {
            ev.preventDefault();

            // Obtiene variante seleccionada si existe
            const $form = $('form.o_wsale_product_form, form#product_form');
            const variantId = ($form.find('input.product_id:checked').val()
                            || $form.find('input[name="product_id"]').val()
                            || $form.find('input[name="product_template_id"]').val());

            // Imagen base (si podemos leerla del DOM)
            const img = document.querySelector('.o_wsale_product_img img, img.js_product_img, img.product_detail_img');
            const imgUrl = img ? img.getAttribute('src') : null;

            const params = new URLSearchParams();
            if (variantId) params.set('variant_id', variantId);
            // por compatibilidad, enviamos también tmpl_id si existe en el form
            const tmplId = $form.find('input[name="product_template_id"]').val();
            if (tmplId) params.set('tmpl_id', tmplId);
            if (imgUrl) params.set('image', imgUrl);

            window.location.href = '/spw/customize' + (params.toString() ? ('?' + params.toString()) : '');
        },
    });
});