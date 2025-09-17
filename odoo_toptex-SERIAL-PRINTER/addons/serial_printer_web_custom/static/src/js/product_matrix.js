/** serial_printer_web_custom/static/src/js/product_matrix.js **/
odoo.define('@serial_printer_web_custom/js/product_matrix', [
    'web.public.widget',
], function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    /**
     * Dibuja una rejilla Color x Talla (solo visual por ahora).
     * Se muestra únicamente si encuentra dos atributos: color y talla.
     */
    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',
        start() {
            try {
                const $form = this.$el.find('form.o_wsale_product_configurator');
                if (!$form.length) return this._super(...arguments);

                // localizar bloques de atributos
                const blocks = $form.find('.o_variant_field');
                const parsed = blocks.toArray().map(el => {
                    const $b = $(el);
                    const name = ($b.find('.o_variant_label, .label, legend').first().text() || '')
                        .trim().toLowerCase();
                    const options = $b.find('input[type="radio"],input[type="checkbox"]').toArray().map(inp => {
                        const $inp = $(inp);
                        const txt = ($inp.closest('label, .o_variant_value').text() || '').trim();
                        return { text: txt };
                    });
                    return { name, options };
                });

                // detectar color / talla en varios idiomas
                const isColor = n => /(color|colour|couleur|farbe|colore|kleur|cor)/i.test(n);
                const isSize  = n => /(size|talla|taille|größe|groesse|taglia|maat|tamanho)/i.test(n);

                const color = parsed.find(b => isColor(b.name));
                const size  = parsed.find(b => isSize(b.name));

                // Solo si hay dos ejes
                if (!color || !size) return this._super(...arguments);
                if (this.$el.find('#sp-matrix').length) return this._super(...arguments);

                // Render sencillo
                let html = '<div id="sp-matrix" class="border rounded p-3 mt-3">';
                html += '<div class="fw-bold mb-2">Pedido rápido por Color x Talla</div>';
                html += '<div class="d-flex mb-1"><div class="w-25"></div>';
                size.options.forEach(o => { html += `<div class="w-25 text-center fw-bold">${_.escape(o.text)}</div>`; });
                html += '</div>';
                color.options.forEach(c => {
                    html += `<div class="d-flex align-items-center mb-1"><div class="w-25 fw-bold">${_.escape(c.text)}</div>`;
                    size.options.forEach(() => { html += `<div class="w-25"><input class="form-control form-control-sm" type="number" min="0" value="0"></div>`; });
                    html += '</div>';
                });
                html += '</div>';

                // insertar debajo del configurador
                $form.after(html);
            } catch (e) {
                // no bloqueamos la página si algo falla
                console.error('[SP] Matrix error:', e);
            }
            return this._super(...arguments);
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});