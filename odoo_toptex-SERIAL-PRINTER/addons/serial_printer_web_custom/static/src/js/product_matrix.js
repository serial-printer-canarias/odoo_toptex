/** serial_printer_web_custom/static/src/js/product_matrix.js **/
odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
    async function waitProductIdChange($root, before, timeout = 1500) {
        const start = Date.now();
        while (Date.now() - start < timeout) {
            const cur = parseInt($root.find('input[name="product_id"]').val() || '0', 10);
            if (cur && cur !== before) return cur;
            await sleep(40);
        }
        return parseInt($root.find('input[name="product_id"]').val() || '0', 10);
    }
    function esc(s) {
        return String(s || '').replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    }

    publicWidget.registry.SerialPrinterMatrixGrid = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',

        start: function () {
            this.$root = this.$el;
            this._buildMatrix();
            return this._super.apply(this, arguments);
        },

        _groups: function () {
            const groups = [];
            // Odoo 18 suele usar estas clases para los grupos de atributos
            this.$root.find('.css_attribute, .css_attribute_color').each(function () {
                const $g = $(this);
                const title = ($g.find('.attribute_name, label, .o_wsale_attr_label').first().text() || '').trim();
                const $inputs = $g.find('input[type="radio"].js_variant_change');
                if ($inputs.length) groups.push({ $g, title, $inputs });
            });
            return groups;
        },

        _detectRowColGroups: function (groups) {
            const sizeIdx  = groups.findIndex(g => /(talla|size|größe|taglia|maat|tamanho)/i.test(g.title));
            const colorIdx = groups.findIndex(g => /(color|colour|farbe|colore|kleur|cor)/i.test(g.title));
            if (sizeIdx < 0 || colorIdx < 0) return null;
            return { rowGroup: groups[sizeIdx], colGroup: groups[colorIdx] };
        },

        _buildMatrix: async function () {
            const groups = this._groups();
            if (groups.length < 2) return;
            const picked = this._detectRowColGroups(groups);
            if (!picked) return;

            const { rowGroup, colGroup } = picked;

            // Punto de inserción: debajo del CTA
            const $anchor = this.$root.find('.o_wsale_cta_wrapper, form[action*="/shop/cart/update"]').last();
            if (!$anchor.length) return;

            const $box = $(`
                <div class="sp-matrix card rounded p-3 mt-3">
                  <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="fw-semibold">Pedido rápido (Color × Talla)</div>
                    <button class="btn btn-sm btn-primary sp-matrix-add">Añadir seleccionados</button>
                  </div>
                  <div class="table-responsive">
                    <table class="table table-sm align-middle sp-matrix-table">
                      <thead><tr><th>Talla</th></tr></thead>
                      <tbody></tbody>
                    </table>
                  </div>
                </div>
            `);
            const $theadRow = $box.find('thead tr');
            const $tbody    = $box.find('tbody');

            // Cabecera: colores
            const colors = [];
            colGroup.$inputs.each(function () {
                const $r = $(this);
                const id = parseInt($r.val() || '0', 10);
                const name =
                    ($r.closest('label').text() || $r.data('value_name') || $r.attr('title') || `#${id}`).trim();
                colors.push({ id, $r, name });
                $theadRow.append(`<th class="text-center">${esc(name)}</th>`);
            });

            // Guardar selección original para restaurar al final
            const $origColor = colGroup.$inputs.filter(':checked');
            const $origSize  = rowGroup.$inputs.filter(':checked');
            const origPid    = parseInt(this.$root.find('input[name="product_id"]').val() || '0', 10);

            // Filas: tallas; celdas: cada color → resolvemos variant_id programáticamente
            const self = this;
            for (const sizeRadio of rowGroup.$inputs.toArray()) {
                const $s = $(sizeRadio);
                const sizeId = parseInt($s.val() || '0', 10);
                const sizeName =
                    ($s.closest('label').text() || $s.data('value_name') || $s.attr('title') || `#${sizeId}`).trim();
                const $tr = $(`<tr><th>${esc(sizeName)}</th></tr>`);

                for (const col of colors) {
                    const before = parseInt(self.$root.find('input[name="product_id"]').val() || '0', 10);
                    // Seleccionamos color + talla, dejamos que Odoo calcule combinación
                    col.$r.prop('checked', true).change();
                    $s.prop('checked', true).change();
                    const variantId = await waitProductIdChange(self.$root, before);

                    const $td = $(`
                        <td class="text-center">
                          <input type="number" class="form-control form-control-sm sp-qty"
                                 min="0" step="1" value="0" data-variant-id="${variantId}">
                        </td>
                    `);
                    $tr.append($td);
                }
                $tbody.append($tr);
            }

            // Restaurar selección original
            if ($origColor.length) $origColor.prop('checked', true).change();
            if ($origSize.length)  $origSize.prop('checked', true).change();
            await waitProductIdChange(this.$root, origPid);

            // Insertar en la página
            $anchor.after($box);

            // Añadir al carrito todo lo marcado
            $box.on('click', '.sp-matrix-add', async function (ev) {
                ev.preventDefault();
                const calls = [];
                $box.find('.sp-qty').each(function () {
                    const qty = parseFloat(this.value || '0');
                    const variantId = parseInt(this.dataset.variantId || '0', 10);
                    if (qty > 0 && variantId) {
                        calls.push(ajax.jsonRpc('/shop/cart/update_json', 'call', {
                            product_id: variantId, add_qty: qty, display: false,
                        }));
                    }
                });
                if (!calls.length) return;
                await Promise.all(calls);
                window.location.reload();
            });
        },
    });

    return publicWidget.registry.SerialPrinterMatrixGrid;
});