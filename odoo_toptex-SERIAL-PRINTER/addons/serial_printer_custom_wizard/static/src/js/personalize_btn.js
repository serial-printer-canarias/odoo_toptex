/** @odoo-module */
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');

  publicWidget.registry.SpwPersonalizeBtn = publicWidget.Widget.extend({
    selector: '#spw_personalize_btn',

    start() {
      this._buildUrl();
      this.$el.on('click', (ev) => {
        ev.preventDefault();
        this._buildUrl();
        const href = this.$el.attr('href');
        if (href) {
          window.location.href = href;
        }
      });
      return this._super(...arguments);
    },

    _buildUrl() {
      const slot = document.getElementById('spw_personalize_slot');
      const tmplId = slot && slot.dataset.ptmpl ? slot.dataset.ptmpl : '';
      const variantInput = document.querySelector("input[name='product_id']");
      const variantId = variantInput ? variantInput.value : '';
      const url = `/spw/customize/${tmplId}${variantId ? `?variant_id=${variantId}` : ''}`;
      this.$el.attr('href', url);
    },
  });
});