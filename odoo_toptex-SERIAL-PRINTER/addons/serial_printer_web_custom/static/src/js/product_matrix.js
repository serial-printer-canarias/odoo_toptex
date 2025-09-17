/** Odoo 18 - Matrix color × talla sin dependencias externas */
odoo.define('serial_printer_web_custom.product_matrix', [], function () {
    "use strict";

    // -------- JSON-RPC mínimo (sustituye a web.ajax) --------
    async function jsonRpc(url, params = {}) {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params, id: Date.now() }),
            credentials: 'same-origin',
        });
        const payload = await res.json();
        if (payload && payload.error) throw payload.error;
        return payload ? payload.result : null;
    }

    // ------------------- Ordenación de tallas -------------------
    const SIZE_ORDER = [
        'XXS','XS','S','M','L','XL','XXL','3XL','4XL','5XL','6XL',
    ];
    function sizeSortKey(txt) {
        const t = String(txt || '').trim().toUpperCase();
        const fixed = SIZE_ORDER.indexOf(t);
        if (fixed !== -1) return fixed;
        const m = t.match(/^(\d{1,3})\s*(EU|US|UK|FR)?$/); // 6 UK, 38 EU, etc.
        if (m) return 100 + parseInt(m[1], 10);           // orden numérico ascendente
        return 1000 + (t.charCodeAt(0) || 0);
    }

    // ------------------- Utilidades DOM -------------------
    function onReady(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }
    function norm(s) {
        return String(s || '')
            .toLowerCase()
            .normalize('NFD').replace(/\p{Diacritic}/gu, '')
            .trim();
    }
    function getAttrBlocks(scope) {
        const container =
            scope.querySelector('.js_product .js_attributes') ||
            scope.querySelector('#product_details .js_attributes') ||
            scope.querySelector('.oe_website_sale .js_attributes');
        if (!container) return [];

        const groups = container.querySelectorAll(
            '.js_attribute, .o_wsale_product_configurator_row, .o_variant_attribute'
        );
        const blocks = [];
        groups.forEach(group => {
            const labelEl =
                group.querySelector('.o_variant_label, .attribute_name, .o_wsale_product_configurator_label') ||
                group.closest('[data-attribute_name]');
            const name =
                (labelEl && (labelEl.textContent || labelEl.getAttribute('data-attribute_name'))) ?
                    (labelEl.textContent || labelEl.getAttribute('data-attribute_name')) : '';

            const radios = Array.from(group.querySelectorAll('input[type="radio"]'));
            if (!radios.length) return;

            const options = radios.map(inp => {
                const id = parseInt(
                    inp.getAttribute('data-value_id') ||
                    inp.getAttribute('data-attribute_value_id') ||
                    inp.value || '0', 10
                ) || null;
                const lab = group.querySelector(`label[for="${inp.id}"]`);
                const txt = (lab && lab.textContent) ||
                            inp.getAttribute('data-value_name') ||
                            inp.getAttribute('data-attribute_name') || '';
                return { id, text: String(txt).trim(), input: inp };
            }).filter(o => o.id && o.text);

            blocks.push({ name: String(name).trim(), options });
        });

        return blocks;
    }
    function findColorAndSize(blocks) {
        const isColor = n => /^(color|colour|couleur|farbe)$/i.test(norm(n));
        const isSize  = n => /^(talla|size|taille|grosse|maat)$/i.test(norm(n));
        const color = blocks.find(b => isColor(b.name)) || blocks[0] || null;
        const size  = blocks.find(b => isSize(b.name))  || blocks[1] || null;
        return { color, size };
    }

    // ------------------- Render del grid -------------------
    function renderGrid({ color, size }, mountAfter) {
        if (!color || !size) return null;
        size.options.sort((a, b) => sizeSortKey(a.text) - sizeSortKey(b.text));

        const box = document.createElement('div');
        box.id = 'sp-matrix';
        box.innerHTML = `
            <div class="sp-matrix-note mb-2 text-muted small">
                Indica cantidades por color y talla.
            </div>
            <table class="sp-matrix__table">
                <thead>
                    <tr>
                        <th class="sp-sticky-left">Color</th>
                        ${size.options.map(o => `<th><div class="text-center fw-600">${o.text}</div></th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${color.options.map(c => `
                        <tr data-color-id="${c.id}">
                            <th class="sp-sticky-left">
                                <div class="sp-color">
                                    <img class="sp-color__img" alt="${c.text}">
                                    <span>${c.text}</span>
                                </div>
                            </th>
                            ${size.options.map(s => `
                                <td>
                                    <div class="sp-cell">
                                        <input class="form-control sp-qty" type="number" min="0" step="1"
                                               data-av-ids="${c.id},${s.id}">
                                        <div class="sp-meta"></div>
                                    </div>
                                </td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            <div class="mt-2 text-end">
                <button type="button" class="btn btn-primary add-to-cart-matrix">Añadir selección</button>
            </div>
        `;
        mountAfter.parentNode.insertBefore(box, mountAfter.nextSibling);
        return box;
    }

    // ------------------- Resolver de variant_id (lazy) -------------------
    function getPricelistId() {
        const el = document.querySelector('input[name="pricelist_id"]');
        return el ? parseInt(el.value, 10) || 0 : 0;
    }
    function getProductTemplateId() {
        const cand = document.querySelector('input[name="product_template_id"]') ||
                     document.querySelector('#product_details[data-product-template-id]');
        if (cand) {
            const v = cand.value || cand.getAttribute('data-product-template-id');
            return parseInt(v || '0', 10) || 0;
        }
        return 0;
    }
    async function getVariantId(ptId, avIds) {
        const payload = {
            product_template_id: ptId,
            combination_ids: avIds,
            add_qty: 1,
            pricelist_id: getPricelistId(),
            product_id: 0,
        };
        const data = await jsonRpc('/website_sale/get_combination_info', payload);
        return data && data.product_id ? parseInt(data.product_id, 10) : 0;
    }

    // ------------------- Bootstrap -------------------
    function ensureMatrix() {
        const page = document.querySelector('.o_wsale_product_page');
        if (!page) return;

        // evita duplicar
        if (page.querySelector('#sp-matrix')) return;

        const blocks = getAttrBlocks(page);
        const found = findColorAndSize(blocks);
        if (!found.color || !found.size) return;

        const attrs = page.querySelector('.js_product .js_attributes') ||
                      page.querySelector('#product_details .js_attributes');
        if (!attrs) return;

        const grid = renderGrid(found, attrs);
        if (!grid) return;

        // Oculta radios originales SOLO cuando existe la matriz
        const productForm = page.querySelector('.js_product');
        if (productForm) productForm.classList.add('sp-matrix-active');

        // Placeholder de imagen (fase 2: foto real por variante)
        found.color.options.forEach(c => {
            const img = grid.querySelector(`tr[data-color-id="${c.id}"] .sp-color__img`);
            if (img) img.src = "/web/static/img/placeholder.png";
        });

        // Resolver variant_id al enfocar una celda
        const ptId = getProductTemplateId();
        grid.addEventListener('focusin', async (ev) => {
            const inp = ev.target.closest('input.sp-qty');
            if (!inp || inp.dataset.variantId || !ptId) return;
            const avIds = (inp.dataset.avIds || '')
                .split(',').map(x => parseInt(x, 10)).filter(Boolean);
            if (!avIds.length) return;
            const vid = await getVariantId(ptId, avIds);
            if (vid) inp.dataset.variantId = String(vid);
        });

        // Añadir selección al carrito
        const addBtn = grid.querySelector('.add-to-cart-matrix');
        addBtn?.addEventListener('click', async () => {
            const calls = [];
            grid.querySelectorAll('input.sp-qty').forEach(inp => {
                const qty = parseFloat(inp.value || '0');
                if (!qty || qty <= 0) return;
                calls.push((async () => {
                    let vid = parseInt(inp.dataset.variantId || '0', 10);
                    if (!vid && ptId) {
                        const avIds = (inp.dataset.avIds || '')
                            .split(',').map(x => parseInt(x, 10)).filter(Boolean);
                        vid = await getVariantId(ptId, avIds);
                        if (vid) inp.dataset.variantId = String(vid);
                    }
                    if (!vid) return;
                    await jsonRpc('/shop/cart/update_json', {
                        product_id: vid,
                        add_qty: qty,
                        display: false,
                    });
                })());
            });
            if (!calls.length) return;
            await Promise.all(calls);
            window.location.reload();
        });
    }

    onReady(() => {
        // Intento inmediato y también cuando Owl/DOM cambie (por si el bloque se monta tarde)
        ensureMatrix();
        const mo = new MutationObserver(() => ensureMatrix());
        mo.observe(document.body, { childList: true, subtree: true });
        // Traza mínima para verificar carga
        console.log('[SP] product_matrix listo');
    });

    return {};
});