/** Odoo 18 – Product matrix (color x talla) */
odoo.define('serial_printer_web_custom.product_matrix', ['web.ajax'], function (require) {
    'use strict';

    const ajax = require('web.ajax');

    // ===== util =====
    function onReady(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    // ===== detectar bloques de atributos (Color/Talla) =====
    function getAttributeBlocks(scope) {
        const blocks = [];
        const root = scope.querySelector('.js_product .js_attributes');
        if (!root) return blocks;

        const groups = Array.from(
            root.querySelectorAll('.o_wsale_product_attribute, .form-group, .js_attribute_value')
        ).map(g => g.closest('.o_wsale_product_attribute') || g)
         .filter((g, i, arr) => g && arr.indexOf(g) === i);

        groups.forEach(group => {
            const radios = Array.from(group.querySelectorAll('input[type="radio"]'));
            if (!radios.length) return;

            const labelNode = group.querySelector('.fw-semibold, .o_variant_label, .form-label, label');
            const name = (labelNode ? labelNode.textContent : '').trim();

            const options = radios.map(inp => {
                const id = parseInt(
                    inp.dataset.attributeValueId || inp.dataset.valueId || inp.value || '0',
                    10
                );
                const lab = group.querySelector(`label[for="${inp.id}"]`);
                const text = (lab ? lab.textContent : (inp.getAttribute('data-value_name') || inp.value || '')).trim();
                return id ? { id, text, input: inp } : null;
            }).filter(Boolean);

            if (name && options.length) blocks.push({ name, options, el: group });
        });

        return blocks;
    }

    function splitColorSize(blocks) {
        const by = kw => blocks.find(b => new RegExp(kw, 'i').test(b.name));
        const color = by('color|colour|colou?r');
        let size = by('talla|size|tamaño|uk|eu|us');
        if (!size && blocks.length >= 2) size = (blocks[0] === color) ? blocks[1] : blocks[0];
        return { color, size };
    }

    // orden lógico de tallas
    function sizeOrderKey(txt) {
        const t = (txt || '').toUpperCase().trim();
        const map = { 'XXS':10,'XS':20,'S':30,'M':40,'L':50,'XL':60,'XXL':70,'3XL':80,'4XL':90,'5XL':100 };
        if (map[t] != null) return map[t];
        const m = t.match(/(\d+)\s*(UK|EU|US)?/);
        if (m) return parseInt(m[1], 10);
        return 99999;
    }

    function findColorImageUrl(scope/*, colorText*/) {
        const mainImg = scope.querySelector('.o_website_sale_img, .img-fluid, img');
        return mainImg ? mainImg.src : '';
    }

    function renderGrid(scope, color, size) {
        const sizes = [...size.options].sort((a, b) => sizeOrderKey(a.text) - sizeOrderKey(b.text));

        const wrap = document.createElement('div');
        wrap.id = 'sp-matrix';
        wrap.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <strong>Indica cantidades por color y talla</strong>
                <button id="sp-matrix-add" type="button" class="btn btn-primary btn-sm">
                    Añadir selección
                </button>
            </div>
            <div class="table-responsive">
                <table class="sp-matrix__table">
                    <thead>
                        <tr>
                            <th class="sp-sticky-left">Color</th>
                            ${sizes.map(s => `<th>${s.text}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${color.options.map(c => {
                            const img = findColorImageUrl(scope, c.text);
                            const cells = sizes.map(s => `
                                <td>
                                    <div class="sp-cell">
                                        <input type="number" min="0" step="1"
                                            class="form-control form-control-sm sp-qty"
                                            data-color-id="${c.id}" data-size-id="${s.id}">
                                        <div class="sp-meta" data-meta="${c.id}_${s.id}"></div>
                                    </div>
                                </td>
                            `).join('');
                            return `
                                <tr>
                                    <th class="sp-sticky-left">
                                        <div class="sp-color">
                                            ${img ? `<img class="sp-color__img" src="${img}" alt="${c.text}">` : ''}
                                            <span>${c.text}</span>
                                        </div>
                                    </th>
                                    ${cells}
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        const attrs = scope.querySelector('.js_product .js_attributes');
        attrs.parentNode.insertBefore(wrap, attrs.nextSibling);

        // ocultar radios originales sólo cuando haya matriz
        document.body.classList.add('sp-matrix-active');

        wrap.querySelector('#sp-matrix-add')
            .addEventListener('click', () => addSelectionToCart(scope, wrap));
    }

    async function resolveVariantId(ptId, attrValueIds, qty) {
        try {
            const r = await ajax.jsonRpc('/shop/product/get_combination_info', 'call', {
                product_template_id: ptId,
                combination: attrValueIds,
                add_qty: qty,
            });
            return r && (r.product_id || r.variant_id || r.product_product_id || 0);
        } catch (e) {
            try {
                const r2 = await ajax.jsonRpc('/sale/get_combination_info', 'call', {
                    product_template_id: ptId,
                    combination: attrValueIds,
                    add_qty: qty,
                });
                return r2 && (r2.product_id || r2.variant_id || r2.product_product_id || 0);
            } catch (e2) {
                return 0;
            }
        }
    }

    async function addSelectionToCart(scope, wrap) {
        const ptId = parseInt(
            (scope.querySelector('[data-oe-model="product.template"]') &&
                scope.querySelector('[data-oe-model="product.template"]').getAttribute('data-oe-id')) ||
            (scope.querySelector('input[name="product_template_id"]') &&
                scope.querySelector('input[name="product_template_id"]').value) ||
            (scope.querySelector('input[name="product_tmpl_id"]') &&
                scope.querySelector('input[name="product_tmpl_id"]').value) || '0', 10);

        const cells = Array.from(wrap.querySelectorAll('input.sp-qty'))
            .map(i => ({ qty: parseFloat(i.value || '0'), c: parseInt(i.dataset.colorId, 10), s: parseInt(i.dataset.sizeId, 10) }))
            .filter(x => x.qty > 0 && x.c && x.s);

        if (!cells.length || !ptId) return;

        for (const it of cells) {
            const variantId = await resolveVariantId(ptId, [it.c, it.s], it.qty);
            if (variantId) {
                await ajax.jsonRpc('/shop/cart/update_json', 'call', {
                    product_id: variantId,
                    add_qty: it.qty,
                    display: false,
                });
            }
        }
        window.location.href = '/shop/cart';
    }

    // ===== init =====
    onReady(function () {
        const page = document.querySelector('.o_wsale_product_page');
        if (!page) return;
        if (document.getElementById('sp-matrix')) return; // evita duplicados

        const blocks = getAttributeBlocks(page);
        const { color, size } = splitColorSize(blocks);
        if (!color || !size) return;

        renderGrid(page, color, size);
    });
});