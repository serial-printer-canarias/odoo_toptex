odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    // Orden lógico para tallas de texto
    const SIZE_ORDER = ['XXS','XS','S','M','L','XL','XXL','3XL','4XL','5XL'];

    function normalizeLabel(txt) {
        return (txt || '').replace(/\s+/g,' ').trim();
    }
    function sizeKey(label) {
        const t = normalizeLabel(label).toUpperCase();
        // Numérico tipo "6 UK", "38 EU", etc.
        const m = t.match(/(\d+)/);
        if (m) return { type: 'num', v: parseInt(m[1],10), raw: t };
        // Texto clásico
        const idx = SIZE_ORDER.indexOf(t);
        return { type: 'txt', v: (idx === -1 ? 999 : idx), raw: t };
    }
    function sortSizes(options) {
        return options.slice().sort((a,b)=>{
            const ak = sizeKey(a.name), bk = sizeKey(b.name);
            if (ak.type !== bk.type) return ak.type === 'num' ? -1 : 1;
            if (ak.v !== bk.v) return ak.v - bk.v;
            return a.name.localeCompare(b.name);
        });
    }

    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',
        events: {
            'click .sp-add-to-cart': '_onAddAllToCart',
            'click .js_add_cart_json': '_hookNativeAddToCart',
        },

        start() {
            this._buildIfPossible();
            return this._super.apply(this, arguments);
        },

        // ----- detectar bloques de atributos -----
        _getAttributeBlocks() {
            const blocks = [];
            this.$('.js_product .js_attributes [data-attribute_name]').each(function () {
                const $b = $(this);
                const name = normalizeLabel($b.attr('data-attribute_name') || '');
                const options = $b.find('input[type="radio"]').map(function () {
                    const $inp = $(this);
                    const id = parseInt($inp.data('value_id') || $inp.data('attribute_value_id') || $inp.val(), 10);
                    const label = normalizeLabel($inp.closest('label').text() || $inp.attr('title'));
                    return id ? { id, name: label, $inp } : null;
                }).get();
                if (name && options.length) blocks.push({ name, options, $el: $b });
            });
            return blocks;
        },
        _pickColorAndSize(blocks){
            const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n);
            const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n);
            let color = blocks.find(b=>isColor(b.name));
            let size  = blocks.find(b=>isSize(b.name));
            if (size) size.options = sortSizes(size.options);
            return { color, size };
        },

        // ----- construir matriz -----
        async _buildIfPossible() {
            const blocks = this._getAttributeBlocks();
            const { color, size } = this._pickColorAndSize(blocks);
            if (!color || !size) return;

            this.el.classList.add('sp-matrix-active'); // para ocultar radios originales

            const $after = this.$('.product_price').first();
            const $mount = $('<div id="sp-matrix" class="sp-matrix o-pt-3"></div>');
            ($after.length ? $after : this.$el).after($mount);

            // tabla
            const $table = $('<table class="sp-matrix__table"></table>');
            const $thead = $('<thead><tr><th class="sp-sticky-left">Color</th></tr></thead>');
            size.options.forEach(o => $thead.find('tr').append(`<th>${_.escape(o.name)}</th>`));
            const $tbody = $('<tbody></tbody>');

            color.options.forEach(c=>{
                const $tr = $(`
                  <tr data-color-id="${c.id}">
                    <th class="sp-sticky-left">
                      <div class="sp-color">
                        <img class="sp-color__img" alt="">
                        <span class="sp-color__name">${_.escape(c.name)}</span>
                      </div>
                    </th>
                  </tr>`);
                size.options.forEach(s=>{
                    const $td = $(`
                      <td data-size-id="${s.id}">
                        <div class="sp-cell">
                          <input type="number" min="0" step="1" class="sp-qty"
                                 data-color-id="${c.id}" data-size-id="${s.id}">
                          <div class="sp-meta">
                            <span class="sp-price"></span>
                            <span class="sp-stock"></span>
                          </div>
                        </div>
                      </td>`);
                    $tr.append($td);
                });
                $tbody.append($tr);
            });

            $table.append($thead,$tbody);
            $mount.append($table);
            $mount.append('<button type="button" class="btn btn-primary mt-2 sp-add-to-cart">Añadir selección</button>');

            // hidratar celdas y poner imagen por color
            await this._hydrateCells(size, color);
        },

        // ----- helpers de combinación -----
        _tmplId() {
            return parseInt(
                this.$('[data-product-template-id]').data('product-template-id') ||
                this.$('input[name="product_id"]').val() || 0, 10);
        },
        _pricelistId() {
            return parseInt(this.$('[data-pricelist-id]').data('pricelist-id') || 0, 10);
        },
        _comboArgs(avIds) {
            return {
                product_template_id: this._tmplId() || undefined,
                product_id: 0,
                combination: avIds,
                add_qty: 1,
                parent_combination: [],
                pricelist_id: this._pricelistId() || undefined,
            };
        },
        async _fetchCombination(avIds) {
            const args = this._comboArgs(avIds);
            try { return await ajax.jsonRpc('/shop/get_combination_info','call',args); }
            catch(e) { try { return await ajax.jsonRpc('/sale/get_combination_info','call',args); }
            catch(e2){ return null; } }
        },
        async _getStock(variantId) {
            try {
                const res = await ajax.jsonRpc('/web/dataset/call_kw','call',{
                    model:'product.product', method:'read', args:[[variantId],['qty_available']], kwargs:{}
                });
                return res && res[0] ? res[0].qty_available : null;
            } catch(e){ return null; }
        },

        async _hydrateCells(size, color) {
            // Imagen por fila/color usando primer tamaño
            await Promise.all(color.options.map(async (c)=>{
                const s0 = size.options[0];
                const info = await this._fetchCombination([c.id, s0.id]);
                if (info && info.product_id) {
                    $(`tr[data-color-id="${c.id}"] .sp-color__img`)
                      .attr('src', `/web/image/product.product/${info.product_id}/image_128`);
                }
            }));

            // Celdas
            const tds = Array.from(this.el.querySelectorAll('#sp-matrix td'));
            const queue = tds.slice();
            const self = this;

            async function worker(){
                while(queue.length){
                    const td = queue.shift();
                    const $td = $(td);
                    const colorId = parseInt($td.closest('tr').data('color-id'),10);
                    const sizeId  = parseInt($td.attr('data-size-id'),10);
                    const info = await self._fetchCombination([colorId, sizeId]);
                    if (info && info.product_id) {
                        const $input = $td.find('.sp-qty');
                        $input.attr('data-variant-id', info.product_id);

                        if (typeof info.price === 'number') {
                            $td.find('.sp-price').text(self._formatPrice(info.price));
                        }
                        let stock = (info.stock_quantity != null) ? info.stock_quantity : await self._getStock(info.product_id);
                        if (stock != null) $td.find('.sp-stock').text(`Stock: ${stock}`);
                    } else {
                        $td.addClass('sp-unavailable');
                    }
                }
            }
            await Promise.all(new Array(6).fill(0).map(worker));
        },

        _formatPrice(v){
            try{
                const lang = document.documentElement.lang || 'es-ES';
                const curr = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
                return new Intl.NumberFormat(lang,{style:'currency',currency:curr}).format(v);
            }catch(e){ return (Math.round(v*100)/100).toFixed(2); }
        },

        // ----- Add to cart -----
        _hookNativeAddToCart(ev){
            // si hay alguna cantidad en la matriz, usamos la suma y evitamos el default
            const hasQty = !!this.$('#sp-matrix .sp-qty').toArray().find(i => parseFloat(i.value||'0') > 0);
            if (hasQty) {
                ev.preventDefault();
                this._onAddAllToCart(ev);
            }
        },
        _onAddAllToCart(ev){
            ev.preventDefault();
            const calls = [];
            this.$('#sp-matrix .sp-qty').each(function(){
                const qty = parseFloat(this.value || '0');
                const product_id = parseInt(this.dataset.variantId || '0', 10);
                if (qty > 0 && product_id) {
                    calls.push(ajax.jsonRpc('/shop/cart/update_json','call',{
                        product_id, add_qty: qty, display: false,
                    }));
                }
            });
            if (!calls.length) return;
            Promise.all(calls).then(()=>window.location.reload());
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});