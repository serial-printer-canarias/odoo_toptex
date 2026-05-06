/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { jsonRpc } from 'web.rpc';

const SEL_PAGE = '.o_wsale_product_page';

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = String(s || '');
    return d.innerHTML;
}

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: SEL_PAGE,

    events: {
        'click .sp-add-to-cart': '_onAddAllToCart',
    },

    start() {
        // Evita duplicados si Odoo reinyecta widgets
        const old = this.el.querySelector('#sp-matrix');
        if (old) old.remove();

        // Construir una vez si hay atributos
        this._buildIfPossible().catch(() => {});
        return this._super(...arguments);
    },

    // ============== Localizadores de atributos (color/talla) ==============
    _getAttributeBlocks() {
        const cont = this.el.querySelector('.js_product .js_attributes');
        if (!cont) return [];
        const blocks = [];
        cont.querySelectorAll('[data-attribute_name]').forEach((b) => {
            const name = (b.getAttribute('data-attribute_name') || '').trim();
            const options = [];
            b.querySelectorAll('input[type="radio"]').forEach((inp) => {
                const id = parseInt(
                    inp.dataset.valueId ||
                    inp.dataset.attributeValueId ||
                    inp.value || '0', 10
                );
                const label = (inp.closest('label')?.innerText || inp.title || '').trim();
                if (id) options.push({ id, text: label });
            });
            if (options.length) blocks.push({ name, options, node: b });
        });
        return blocks;
    },

    _pickColorAndSize(blocks) {
        const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
        const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');

        let color = blocks.find(b => isColor(b.name));
        let size  = blocks.find(b => isSize(b.name));

        // Fallbacks
        if (!color && blocks.length) color = blocks[0];
        if (!size  && blocks.length > 1) size  = blocks[1];

        return { color, size };
    },

    // ============== Construcción de la tabla ==============
    async _buildIfPossible() {
        const blocks = this._getAttributeBlocks();
        if (!blocks.length) return;

        const { color, size } = this._pickColorAndSize(blocks);
        if (!color) return; // al menos color

        // Ancla: debajo del precio; si no, debajo del bloque de atributos; si no, al final
        const anchor =
            this.el.querySelector('.product_price') ||
            this.el.querySelector('.js_product .js_attributes') ||
            this.el;

        const wrap = document.createElement('div');
        wrap.id = 'sp-matrix';
        wrap.className = 'sp-matrix o-pt-3';
        anchor.parentNode.insertBefore(wrap, anchor.nextSibling);

        // Cabecera
        const table = document.createElement('table');
        table.className = 'sp-matrix__table';
        const thead = document.createElement('thead');
        const trh = document.createElement('tr');
        trh.innerHTML = `<th class="sp-sticky-left">Color</th>`;
        const sizeOptions = size ? size.options : [{id: 0, text: 'One Size'}];
        sizeOptions.forEach(s => {
            const th = document.createElement('th');
            th.innerHTML = escapeHtml(s.text);
            trh.appendChild(th);
        });
        thead.appendChild(trh);

        // Body
        const tbody = document.createElement('tbody');
        color.options.forEach(c => {
            const tr = document.createElement('tr');
            tr.dataset.colorId = String(c.id);
            tr.innerHTML = `
                <th class="sp-sticky-left">
                  <div class="sp-color">
                    <img class="sp-color__img" alt="">
                    <span class="sp-color__name">${escapeHtml(c.text)}</span>
                  </div>
                </th>
            `;
            sizeOptions.forEach(s => {
                const td = document.createElement('td');
                td.dataset.sizeId = String(s.id || 0);
                td.innerHTML = `
                    <div class="sp-cell">
                      <input class="sp-qty" type="number" min="0" step="1"
                             data-color-id="${c.id}" data-size-id="${s.id || 0}">
                      <div class="sp-meta">
                        <span class="sp-price"></span>
                        <span class="sp-stock"></span>
                      </div>
                    </div>
                `;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        wrap.appendChild(table);
        wrap.insertAdjacentHTML('beforeend',
            `<button type="button" class="btn btn-primary mt-2 sp-add-to-cart">Añadir selección</button>`
        );

        // Hidratar celdas (precio/stock/variant_id/imagen)
        await this._hydrateCells(wrap);
    },

    // ============== Utilidades de combinación / stock ==============
    _comboArgs(avIds) {
        const tmplId = parseInt(
            this.el.querySelector('[data-product-template-id]')?.dataset.productTemplateId ||
            this.el.querySelector('input[name="product_id"]')?.value || '0', 10);

        const pricelistId = parseInt(
            this.el.querySelector('[data-pricelist-id]')?.dataset.pricelistId || '0', 10);

        return {
            product_template_id: tmplId || undefined,
            product_id: 0,
            combination: avIds,          // lista de IDs de valores de atributo
            add_qty: 1,
            parent_combination: [],
            pricelist_id: pricelistId || undefined,
        };
    },

    async _fetchCombination(avIds) {
        const args = this._comboArgs(avIds.filter(Boolean));
        try {
            return await jsonRpc('/shop/get_combination_info', 'call', args);
        } catch (e1) {
            try {
                return await jsonRpc('/sale/get_combination_info', 'call', args);
            } catch (e2) {
                return null;
            }
        }
    },

    async _getStock(variantId) {
        try {
            const res = await jsonRpc('/web/dataset/call_kw', 'call', {
                model: 'product.product',
                method: 'read',
                args: [[variantId], ['qty_available']],
                kwargs: {},
            });
            return (res && res[0] && typeof res[0].qty_available === 'number')
                ? res[0].qty_available : null;
        } catch (e) {
            return null;
        }
    },

    _formatPrice(v) {
        if (typeof v !== 'number') return '';
        try {
            const lang = document.documentElement.lang || 'es-ES';
            const curr = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
            return new Intl.NumberFormat(lang, { style: 'currency', currency: curr }).format(v);
        } catch {
            return v.toFixed(2);
        }
    },

    // ============== Hidratar tabla ==============
    async _hydrateCells(root) {
        const tds = Array.from(root.querySelectorAll('td[data-size-id]'));
        // Descubre variant_id por celda
        for (const td of tds) {
            const colorId = parseInt(td.closest('tr')?.dataset.colorId || '0', 10);
            const sizeId  = parseInt(td.dataset.sizeId || '0', 10);
            const avIds   = sizeId ? [colorId, sizeId] : [colorId];

            const info = await this._fetchCombination(avIds);
            if (!info || !info.product_id) {
                td.classList.add('sp-unavailable');
                continue;
            }

            // Guarda variant_id
            td.querySelector('.sp-qty').dataset.variantId = String(info.product_id);

            // Precio si viene
            if (typeof info.price === 'number') {
                td.querySelector('.sp-price').textContent = this._formatPrice(info.price);
            }

            // Stock (info.stock_quantity puede no venir siempre)
            let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
            if (stock === null) stock = await this._getStock(info.product_id);
            if (stock !== null) td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;

            // Imagen por fila/color (sólo si aún no está)
            const img = td.closest('tr').querySelector('.sp-color__img');
            if (!img.getAttribute('src')) {
                img.setAttribute('src', `/web/image/product.product/${info.product_id}/image_128`);
            }
        }
    },

    // ============== Carrito masivo ==============
    async _onAddAllToCart(ev) {
        ev.preventDefault();
        const lines = [];
        this.el.querySelectorAll('#sp-matrix .sp-qty').forEach((inp) => {
            const qty = parseFloat(inp.value || '0');
            const pid = parseInt(inp.dataset.variantId || '0', 10);
            if (qty > 0 && pid) lines.push({ product_id: pid, qty });
        });
        if (!lines.length) return;

        // Llamadas estándar una a una (robusto en todos los sitios)
        await Promise.all(lines.map(l => jsonRpc('/shop/cart/update_json', 'call', {
            product_id: l.product_id,
            add_qty: l.qty,
            display: false,
        })));

        window.location.reload();
    },
});

export default publicWidget.registry.SerialPrinterMatrix;