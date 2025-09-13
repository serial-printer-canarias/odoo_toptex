/** serial_printer_custom_wizard/static/src/js/spw_logo_preview.js **/
odoo.define('serial_printer_custom_wizard.spw_logo_preview', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');

  publicWidget.registry.SpwLogoPreview = publicWidget.Widget.extend({
    selector: '#spw_canvas',

    start() {
      this.$canvas  = this.$el;
      this.$product = this.$('#spw_product_img');
      this.$logo    = this.$('#spw_logo_preview');

      // Controles (están fuera del canvas)
      this.$input   = $('#spw_logo_input');
      this.$size    = $('#spw_size');
      this.$posx    = $('#spw_pos_x');
      this.$posy    = $('#spw_pos_y');
      this.$rotate  = $('#spw_rotate');

      // Eventos
      this.$input.on('change', this._onFileChange.bind(this));
      [this.$size, this.$posx, this.$posy, this.$rotate].forEach(($el) => {
        $el.on('input change', this._applyTransform.bind(this));
      });

      // Recalcular al redimensionar (móvil/rotación)
      $(window).on('resize', this._applyTransform.bind(this));

      return this._super.apply(this, arguments);
    },

    // Carga el archivo local en base64 y lo pone en <img id="spw_logo_preview">
    _onFileChange(ev) {
      const file = ev.target.files && ev.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        // Mostrar el logo
        this.$logo.attr('src', e.target.result).removeClass('d-none');

        // Reset valores cómodos
        this.$size.val(40);
        this.$posx.val(0);
        this.$posy.val(0);
        this.$rotate.val(0);

        this._applyTransform();
      };
      reader.readAsDataURL(file); // compatible con iOS/Safari
    },

    // Aplica tamaño/posición/rotación al overlay
    _applyTransform() {
      if (!this.$logo.attr('src')) return;

      const sizePct = parseInt(this.$size.val() || '40', 10); // porcentaje del ancho del producto
      const dx      = parseInt(this.$posx.val() || '0', 10);  // px relativos
      const dy      = parseInt(this.$posy.val() || '0', 10);
      const rot     = parseInt(this.$rotate.val() || '0', 10);

      const prodW = this.$product.width() || 1;
      const logoW = Math.max(10, Math.round((sizePct / 100) * prodW));

      this.$logo.css({
        width: logoW + 'px',
        transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) rotate(${rot}deg)`,
      });
    },
  });

  return publicWidget.registry.SpwLogoPreview;
});