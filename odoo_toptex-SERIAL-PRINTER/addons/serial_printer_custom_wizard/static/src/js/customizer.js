odoo.define('serial_printer_custom_wizard.customizer', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.SpwCustomizer = publicWidget.Widget.extend({
    selector: '.spw-customizer',

    start() {
      this.$base   = this.$('#spw_product_img');
      this.$logo   = this.$('#spw_logo_preview');
      this.$file   = this.$('#spw_logo_input');
      this.$scale  = this.$('#spw_scale');
      this.$rotate = this.$('#spw_rotate');
      this.$posX   = this.$('#spw_pos_x');
      this.$posY   = this.$('#spw_pos_y');

      // Imagen de la variante si viene en la URL
      const params = new URLSearchParams(window.location.search);
      const variantId = params.get('product_id');
      if (variantId) {
        this.$base.attr('src', `/web/image/product.product/${variantId}/image_1024`);
      }

      // Preview del logo
      this.$file.on('change', (ev) => {
        const f = ev.target.files && ev.target.files[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = (e) => {
          this.$logo.attr('src', e.target.result).css('display', 'block');
          this._applyTransforms();
        };
        reader.readAsDataURL(f);
      });

      // Controles
      const refresh = () => this._applyTransforms();
      this.$scale.on('input change', refresh);
      this.$rotate.on('input change', refresh);
      this.$posX.on('input change', refresh);
      this.$posY.on('input change', refresh);

      // Posiciones rápidas
      this.$('[data-spw-pos]').on('click', (ev) => {
        const pos = $(ev.currentTarget).data('spw-pos');
        if (pos === 'left')  { this.$posX.val(25); this.$posY.val(50); }
        if (pos === 'right') { this.$posX.val(75); this.$posY.val(50); }
        if (pos === 'back')  { this.$posX.val(50); this.$posY.val(70); }
        this._applyTransforms();
      });

      return this._super(...arguments);
    },

    _applyTransforms() {
      const x = parseFloat(this.$posX.val() || 50);
      const y = parseFloat(this.$posY.val() || 50);
      const s = parseFloat(this.$scale.val() || 100) / 100; // 1.0 por defecto
      const r = parseFloat(this.$rotate.val() || 0);
      this.$logo.css({
        left: `${x}%`,
        top: `${y}%`,
        transform: `translate(-50%, -50%) rotate(${r}deg) scale(${s})`,
      });
    },
  });
});