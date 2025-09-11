odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.SpwPersonalizeBtn = publicWidget.Widget.extend({
    selector: '#spw_personalize_btn',
    start() {
      this.$el.on('click', (ev) => {
        ev.preventDefault();
        const $form = this.$el.closest('form.o_wsale_product_form, form.o_add_to_cart_form');
        const tmplId = $form.find('input[name="product_template_id"]').val()
          || $('main').data('product-template') || '';
        const variantId = $form.find('input[name="product_id"]').val() || '';
        let url = `/spw/customize?product_tmpl_id=${encodeURIComponent(tmplId)}`;
        if (variantId) {
          url += `&product_id=${encodeURIComponent(variantId)}`;
        }
        window.location.href = url;
      });
      return this._super(...arguments);
    },
  });
});