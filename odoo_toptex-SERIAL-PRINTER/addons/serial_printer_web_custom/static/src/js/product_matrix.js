/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { jsonRpc } from 'web.ajax';

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: '.o_wsale_product_page',

    start() {
        // Construir una única vez por página
        if (!document.querySelector('#sp-matrix-anchor')) return this._super(...arguments);
        if (document.querySelector('#sp-matrix')) return this._super(...arguments);

        this._buildMatrix();
        return this._super(...arguments);
    },

    // === helpers ===
    _dataset() {
        const root = document.querySelector('.js_product') || document;
        const tmpl =
            parseInt(root?.dataset?.productTemplateId || 0, 10) ||
            parseInt(document.querySelector('[data-product-template-id]')?.dataset?.productTemplateId || 0, 10) ||
            parseInt(document.querySelector('input[name="product_id"]')?.value || 0, 10);

        const pricelist =
            parseInt(document.querySelector('[data-pricelist-id]')?.dataset?.pricelistId || 0, 10);

        return { tmplId: tmpl || 0, pricelistId: pricelist || 0 };
    },

    _getAttributeBlocks() {
        const container = document.querySelector('.js_product .js_attributes') || document;
        const blocks = [];
        container?.querySelectorAll('[data-attribute_name]').forEach((el) => {
            const name = (el.getAttribute('data-attribute_name') || '').trim();
            const options = [];
            el.querySelectorAll('input[type="radio"]').forEach((inp) => {
                const id = parseInt(
                    inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || 0,
                    10
                );
                const label = (inp.closest('label')?.textContent || inp.title || '').trim();
                if (id) options.push({ id, text: label });
            });
            if (options.length) blocks.push({ name, options });
        });
        return blocks;
    },

    _pickColorSize(blocks) {
        const isColor = (n) => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
        const isSize  = (n) => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');
        let color = blocks.find((b) => isColor(b.name));
        let size  = blocks.find((b) => isSize(b.name));
        if (!color) color = blocks[0];
        if (!size)  size  = blocks[1];
        return { color, size };
    },

    // === build ===
    async _buildMatrix() {
        const anchor = document.querySelector('#sp-matrix-anchor');
        const blocks = this._getAttributeBlocks();
        if (!anchor || blocks.length < 2) return;

        const { color, size } = this._pickColorSize(blocks);
        if (!color || !size) return;

        const wrap = document.createElement('div');
        wrap.id = 'sp-matrix';
        wrap.className = 'sp-matrix o-pt-3';
        wrap.innerHTML = `
          <table class="sp-matrix__table">
            <thead>
              <tr>
                <th class="sp-sticky-left">Color</th>
                ${size.options.map((s) => `<th>${this._esc(s.text)}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${color.options.map((c) => `
                <tr data-color-id="${c.id}">
                  <th class="sp-sticky-left">
                    <div class="sp-color">
                      <img class="sp-color__img" alt="">
                      <span class="sp-color__name">${this._esc(c.text)}</span>
                    </div>
                  </th>
                  ${size.options.map((s) => `
                    <td data-size-id="${s.id}">
                      <div class="sp-cell">
                        <input type="number" class="sp-qty" min="0" step="1"
                               data-color-id="${c.id}" data-size-id="${s.id}">
                        <div class="sp-meta">
                          <span class="sp-price"></span>
                          <span class="sp-stock"></span>
                        </div>
                      </div>
                    </td>`).join('')}
                </tr>`).join('')}
            </tbody>
          </table>
          <button type="button" class="btn btn-primary mt-2 sp-add-to-cart">Añadir selección</button>
        `;
        anchor.after(wrap);

        // listeners
        wrap.querySelector('.sp-add-to-cart').addEventListener('click', (ev) => this._addAllToCart(ev));

        // hidratar celdas
        await this._hydrateCells(wrap);
        // Log útil para comprobar que se cargó
        console.debug('[SP] matrix ready');
    },

    _esc(s) { return (s || '').replace(/[&<>"']/g, (m) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); },

    _comboArgs(avIds) {
        const { tmplId, pricelistId } = this._dataset();
        return {
            product_template_id: tmplId || undefined,
            product_id: 0,
            combination: avIds,         // lista de ids de valores de atributo
            add_qty: 1,
            parent_combination: [],
            pricelist_id: pricelistId || undefined,
        };
    },

    async _fetchCombination(avIds) {
        const args = this._comboArgs(avIds);
        // Ruta estándar de website_sale (equivale a wSaleUtils._getCombinationInfo)
        return jsonRpc('/shop/get_combination_info', 'call', args)
            .catch(() => jsonRpc('/sale/get_combination_info', 'call', args))
            .catch(() => null);
    },

    async _getStock(variantId) {
        // On hand (qty_available) como referencia rápida
        try {
            const res = await jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'product.product',
                method: 'read',
                args: [[variantId], ['qty_available']],
                kwargs: {},
            });
            return (res && res[0] && typeof res[0].qty_available === 'number') ? res[0].qty_available : null;
        } catch {
            return null;
        }
    },

    async _hydrateCells(root) {
        const cells = Array.from(root.querySelectorAll('td[data-size-id]'));
        const workers = 6;
        const queue = cells.slice();

        const run = async () => {
            while (queue.length) {
                const td = queue.shift();
                const colorId = parseInt(td.closest('tr')?.dataset?.colorId || '0', 10);
                const sizeId  = parseInt(td.dataset.sizeId || '0', 10);
                if (!colorId || !sizeId) continue;

                const info = await this._fetchCombination([colorId, sizeId]);
                if (!info || !info.product_id) { td.classList.add('sp-unavailable'); continue; }

                // Guardamos variant_id en el input
                const input = td.querySelector('.sp-qty');
                input.dataset.variantId = String(info.product_id);

                // Precio
                if (typeof info.price === 'number') {
                    td.querySelector('.sp-price').textContent = this._formatPrice(info.price);
                }

                // Stock
                let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
                if (stock === null) stock = await this._getStock(info.product_id);
                if (stock !== null) td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;

                // Imagen por color (solo se pone si aún no está)
                const img = td.closest('tr').querySelector('.sp-color__img');
                if (!img.getAttribute('src')) {
                    img.setAttribute('src', `/web/image/product.product/${info.product_id}/image_128`);
                }
            }
        };

        await Promise.all(new Array(workers).fill(0).map(run));
    },

    _formatPrice(v) {
        try {
            const lang = document.documentElement.lang || 'es-ES';
            const code = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
            return new Intl.NumberFormat(lang, { style: 'currency', currency: code }).format(v);
        } catch {
            return (Math.round(v * 100) / 100).toFixed(2);
        }
    },

    _addAllToCart(ev) {
        ev.preventDefault();
        const calls = [];
        document.querySelectorAll('#sp-matrix .sp-qty').forEach((inp) => {
            const qty = parseFloat(inp.value || '0');
            const product_id = parseInt(inp.dataset.variantId || '0', 10);
            if (qty > 0 && product_id) {
                calls.push(jsonRpc('/shop/cart/update_json', 'call', {
                    product_id, add_qty: qty, display: false,
                }));
            }
        });
        if (!calls.length) return;
        Promise.all(calls).then(() => window.location.reload());
    },
});

export default publicWidget.registry.SerialPrinterMatrix;