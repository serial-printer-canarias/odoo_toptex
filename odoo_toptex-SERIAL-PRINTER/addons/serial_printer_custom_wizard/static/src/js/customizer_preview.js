odoo.define('serial_printer_custom_wizard.customizer_preview', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    // Posiciones -> estilo (porcentaje sobre la imagen base)
    const POS_TO_STYLE = {
        pecho:        { top: '35%', left: '50%', width: '35%' },
        espalda:      { top: '30%', left: '50%', width: '45%' },
        manga:        { top: '50%', left: '80%', width: '20%' },
        frente:       { top: '50%', left: '50%', width: '45%' },
        trasera:      { top: '50%', left: '50%', width: '45%' },
        gorra_frente: { top: '40%', left: '50%', width: '40%' },
    };

    publicWidget.registry.SPWCustomizer = publicWidget.Widget.extend({
        selector: '.spw-customizer',
        start: function () {
            this.$base = this.$('#spw_base_img');
            this.$slot = this.$('#spw_slot');
            this.$logo = this.$('#spw_logo_preview');
            this.$inputFile = this.$('input[name="logo"]');
            this.$position = this.$('select[name="posicion_diseno"]');
            this.$thumbs = this.$('.spw-thumb');
            this.$variantId = this.$('input[name="variant_id"]');

            this.$inputFile.on('change', this._onFileChange.bind(this));
            this.$position.on('change', this._onPositionChange.bind(this));
            this.$thumbs.on('click', this._onThumbClick.bind(this));

            this._applyPosition(this.$position.val());
            return this._super.apply(this, arguments);
        },

        _onFileChange: function (ev) {
            const file = ev.target.files && ev.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.$logo.attr('src', e.target.result).addClass('spw-show');
            };
            reader.readAsDataURL(file);
        },

        _onPositionChange: function () {
            this._applyPosition(this.$position.val());
        },

        _applyPosition: function (pos) {
            const s = POS_TO_STYLE[pos] || POS_TO_STYLE.pecho;
            this.$slot.css({
                top: s.top,
                left: s.left,
                width: s.width,
                transform: 'translate(-50%, -50%)',
            });
        },

        _onThumbClick: function (ev) {
            ev.preventDefault();
            const $t = $(ev.currentTarget);
            const src = $t.data('img');
            const vid = $t.data('variant');
            if (src) this.$base.attr('src', src);
            if (vid) this.$variantId.val(vid);
            this.$thumbs.removeClass('active');
            $t.addClass('active');
        },
    });

    return publicWidget.registry.SPWCustomizer;
});