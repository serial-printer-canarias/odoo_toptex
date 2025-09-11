/** @odoo-module **/
import publicWidget from 'web.public.widget';

publicWidget.registry.SpwPersonalizeBtn = publicWidget.Widget.extend({
    selector: 'form.o_wsale_product_form',
    start() {
        this._updateHref();
        // Odoo actualiza este hidden con la variante seleccionada
        this.$el.on('change', 'input[name="product_id"]', this._updateHref.bind(this));
        // Por si el tema emite cambios en otros inputs de atributos
        this.$el.on('change', 'input.js_variant_change, select.js_variant_change', this._updateHref.bind(this));
        return this._super(...arguments);
    },
    _updateHref() {
        const variantId = this.$el.find('input[name="product_id"]').val();
        const $btn = this.$el.find('#spw_personalize_btn');
        if (!$btn.length || !variantId) return;

        // Base = /personalizar/<product_template_id>
        let base = $btn.data('base');
        if (!base) {
            base = $btn.attr('href');
            $btn.attr('data-base', base);
        }
        $btn.attr('href', `${base}?variant_id=${encodeURIComponent(variantId)}`);
    },
});