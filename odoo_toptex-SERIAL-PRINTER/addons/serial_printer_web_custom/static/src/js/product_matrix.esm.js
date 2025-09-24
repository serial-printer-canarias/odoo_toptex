/** @odoo-module **/

// ---------------------------------------------------------
//  SP Matrix (ESM) – grid 1D/2D + hidratar precio/stock/img
//  NOTA: el cambio clave está en fetchCombination() y getStock()
//  que ahora usan payload JSON-RPC correcto para rutas website.
// ---------------------------------------------------------

console.log('[SP] product_matrix activo (1D/2D)');

const ROOT_SELECTOR = '.o_wsale_product_page';     // página de producto
const MATRIX_ID     = 'sp-matrix';

// ---------- Helpers UI ----------
function q(root, sel)       { return root.querySelector(sel); }
function qa(root, sel)      { return Array.from(root.querySelectorAll(sel)); }
function esc(txt)           { return _.escape(String(txt ?? '')); }
function fmtPrice(v) {
    try {
        const lang = document.documentElement.lang || 'es-ES';
        const curr = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
        return new Intl.NumberFormat(lang, { style: 'currency', currency: curr }).format(v);
    } catch {
        return (Math.round((+v || 0) * 100) / 100).toFixed(2);
    }
}

// ---------- RPC helpers (cambio principal) ----------
async function rpcJson(url, params) {
    const res = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({ jsonrpc: '2.0', params, id: Date.now() }),
    });
    if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error.message || 'RPC JSON error');
    return data.result;
}

async function callKw(model, method, args = [], kwargs = {}) {
    const res = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { model, method, args, kwargs }, id: Date.now() }),
    });
    if (!res.ok) throw new Error(`call_kw HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw new Error(data.error.message || 'RPC call_kw error');
    return data.result;
}

// ---------- Detección atributos (Color/Size/PTAV) ----------
function getAttributeBlocks(root) {
    const blocks = [];
    qa(root, '.js_product .js_attributes [data-attribute_name]').forEach((el) => {
        const name = (el.getAttribute('data-attribute_name') || '').trim();
        const options = qa(el, 'input[type="radio"]').map((inp) => {
            const $inp = inp;
            // Robusto: distintas plantillas usan claves data-* diferentes
            const ds = $inp.dataset || {};
            const ptav =
                parseInt(ds.ptav || ds.productTemplateAttributeValueId || ds.productTemplateAttributeValue || ds.ptavid || ds.ptavId || 0, 10) ||
                parseInt(ds.valueId || ds.attributeValueId || $inp.value || 0, 10);
            const label = ($inp.closest('label')?.textContent || $inp.getAttribute('title') || '').trim();
            return { ptav, label, input: $inp };
        }).filter(o => o.ptav);
        if (options.length) blocks.push({ name, options, el });
    });
    return blocks;
}

function pickColorAndSize(blocks) {
    const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
    const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');
    let color = blocks.find(b => isColor(b.name));
    let size  = blocks.find(b => isSize(b.name));
    if (!color && blocks.length) color = blocks[0];
    if (!size  && blocks.length > 1) size  = blocks[1];
    return { color, size };
}

// ---------- Args combinación ----------
function getTemplateId(root) {
    return parseInt(
        q(root, '[data-product-template-id]')?.dataset.productTemplateId ||
        q(root, 'input[name="product_id"]')?.value || 0, 10);
}
function getPricelistId(root) {
    return parseInt(q(root, '[data-pricelist-id]')?.dataset.pricelistId || 0, 10);
}
function comboArgs(ptavIds, root) {
    return {
        product_template_id: getTemplateId(root) || undefined,
        product_id: 0,                             // Odoo lo calcula con combination
        combination: ptavIds,                      // *** PTAV IDs ***
        add_qty: 1,
        parent_combination: [],
        pricelist_id: getPricelistId(root) || undefined,
    };
}

// ---------- OBTENER combinación (cambio principal) ----------
async function fetchCombination(ptavIds, root) {
    const payload = comboArgs(ptavIds, root);
    try {
        return await rpcJson('/shop/get_combination_info', payload);
    } catch {
        // Algunas plantillas usan /sale/get_combination_info
        return await rpcJson('/sale/get_combination_info', payload);
    }
}

async function getStock(variantId) {
    try {
        const res = await callKw('product.product', 'read', [[variantId], ['qty_available']]);
        return (res && res[0] && typeof res[0].qty_available === 'number') ? res[0].qty_available : null;
    } catch { return null; }
}

// ---------- Construir grid ----------
function buildMatrix(root, color, size) {
    // contenedor
    let matrix = q(root, `#${MATRIX_ID}`);
    if (matrix) return matrix;

    matrix = document.createElement('div');
    matrix.id = MATRIX_ID;
    matrix.className = 'sp-matrix o-pt-3';

    // anclaje justo bajo precio
    const anchor = q(root, '.product_price') || root;
    anchor.after(matrix);

    const table   = document.createElement('table');
    table.className = 'sp-matrix__table';
    const thead   = document.createElement('thead');
    const trHead  = document.createElement('tr');
    trHead.innerHTML = `<th class="sp-sticky-left">Color</th>${size.options.map(o => `<th>${esc(o.label)}</th>`).join('')}`;
    thead.appendChild(trHead);

    const tbody = document.createElement('tbody');

    color.options.forEach(c => {
        const tr = document.createElement('tr');
        tr.dataset.colorPtav = String(c.ptav);
        tr.innerHTML = `
            <th class="sp-sticky-left">
              <div class="sp-color">
                <img class="sp-color__img" alt="">
                <span class="sp-color__name">${esc(c.label)}</span>
              </div>
            </th>
        `;
        size.options.forEach(s => {
            const td = document.createElement('td');
            td.dataset.sizePtav = String(s.ptav);
            td.innerHTML = `
              <div class="sp-cell">
                <input type="number" min="0" step="1" class="sp-qty"
                       data-color-ptav="${c.ptav}" data-size-ptav="${s.ptav}">
                <div class="sp-meta">
                  <span class="sp-price"></span>
                  <span class="sp-stock"></span>
                </div>
              </div>`;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });

    table.appendChild(thead);
    table.appendChild(tbody);
    matrix.appendChild(table);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-primary mt-2 sp-add-to-cart';
    btn.textContent = 'Añadir selección';
    matrix.appendChild(btn);

    return matrix;
}

// ---------- Hidratar celdas (precio/stock/img/variant) ----------
async function hydrate(root) {
    const tds = qa(root, `#${MATRIX_ID} td`);
    if (!tds.length) return;

    const queue = tds.slice();
    const workers = new Array(6).fill(0).map(async function run() {
        while (queue.length) {
            const td = queue.shift();
            const colorPtav = parseInt(td.dataset.colorPtav || td.querySelector('.sp-qty')?.dataset.colorPtav || 0, 10);
            const sizePtav  = parseInt(td.dataset.sizePtav  || td.querySelector('.sp-qty')?.dataset.sizePtav  || 0, 10);
            if (!colorPtav || !sizePtav) { td.classList.add('sp-unavailable'); continue; }

            let info = null;
            try { info = await fetchCombination([colorPtav, sizePtav], root); } catch { info = null; }

            if (info && info.product_id) {
                const input = td.querySelector('.sp-qty');
                input.dataset.variantId = String(info.product_id);

                const price = (typeof info.price === 'number') ? info.price
                             : (typeof info.website_price === 'number') ? info.website_price
                             : (typeof info.list_price === 'number') ? info.list_price
                             : null;
                if (price !== null) td.querySelector('.sp-price').textContent = fmtPrice(price);

                let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
                if (stock === null) stock = await getStock(info.product_id);
                if (stock !== null) td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;

                // Imagen por fila/color (si no la tiene ya)
                const row = td.closest('tr');
                const img = row.querySelector('.sp-color__img');
                if (!img.getAttribute('src')) {
                    img.setAttribute('src', `/web/image/product.product/${info.product_id}/image_128`);
                }
            } else {
                td.classList.add('sp-unavailable');
            }
        }
    });
    await Promise.all(workers);
}

// ---------- Carrito masivo ----------
function bindCart(root) {
    const btn = q(root, `#${MATRIX_ID} .sp-add-to-cart`);
    if (!btn) return;
    btn.addEventListener('click', async (ev) => {
        ev.preventDefault();
        const qtyInputs = qa(root, `#${MATRIX_ID} .sp-qty`);
        const calls = [];
        qtyInputs.forEach((inp) => {
            const qty = parseFloat(inp.value || '0');
            const variantId = parseInt(inp.dataset.variantId || '0', 10);
            if (qty > 0 && variantId) {
                calls.push(fetch('/shop/cart/update_json', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
                    body: JSON.stringify({ jsonrpc: '2.0', params: { product_id: variantId, add_qty: qty, display: false }, id: Date.now() }),
                }));
            }
        });
        if (!calls.length) return;
        await Promise.all(calls);
        window.location.reload();
    });
}

// ---------- Boot ----------
function boot() {
    const root = q(document, ROOT_SELECTOR);
    if (!root) return;
    if (q(root, `#${MATRIX_ID}`)) return; // no duplicar

    const blocks = getAttributeBlocks(root);
    if (blocks.length < 1) return;
    const { color, size } = pickColorAndSize(blocks);
    if (!color) return;

    // Si no hay talla, usamos grid 1D (una sola columna "One Size")
    const fakeSize = size || { options: [{ ptav: color.options[0].ptav, label: 'One Size' }] };

    buildMatrix(root, color, fakeSize);
    hydrate(root).then(() => bindCart(root));
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
} else {
    boot();
}