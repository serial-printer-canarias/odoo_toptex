odoo.define('serial_printer_custom_wizard.personalizar_preview', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    publicWidget.registry.spwPreview = publicWidget.Widget.extend({
        selector: '#spw_wrapper',
        start() {
            this.$logoInput = this.$('#spw_logo');
            this.$logoPreview = this.$('#spw_logo_preview');
            if (this.$logoInput.length) {
                this.$logoInput.on('change', this._onLogoChange.bind(this));
            }
            return this._super(...arguments);
        },
        _onLogoChange(ev) {
            const file = ev.target.files && ev.target.files[0];
            if (!file) return;
            const url = URL.createObjectURL(file);
            this.$logoPreview.attr('src', url).removeClass('d-none');
        },
    });

    return publicWidget.registry.spwPreview;
});