// SP Matrix – Odoo 18 (PTAV-aware): precio, stock, foto y carrito en bloque
(() => {
  'use strict';

  const log = (...a) => console.log('[SP]', ...a);

  // ---------- helpers de anclaje ----------
  function getJsProduct() {
    return document.querySelector('.o_wsale_product_page .js_product')
        || document.querySelector('.js_product')
        || document.querySelector('.o_wsale_product_page');
  }
  function placeAnchor() {
    let anchor = document.getElementById('sp-matrix-anchor');
    if (!anchor) {
      anchor = document.createElement('div');
      anchor.id = 'sp-matrix-anchor';
      anchor.className = 'sp-matrix-anchor';
    }
    const root = getJsProduct();
    if (!root) { document.body.appendChild(anchor); return anchor; }
    const attrs =
      root.querySelector('.js_attributes')
      || root.querySelector('ul.o_wsale_product_attribute')
      || root.querySelector('[data-attribute_name]')?.closest('.row, ul, div');
    (attrs || root.querySelector('.product_price, .o_wsale_product_price_section') || root).after(anchor);
    return anchor;
  }

  // ---------- leer bloques de atributos (PTAV + AV) ----------
  function readIds(inp) {
    const d = inp.dataset || {};
    const ptav =
      parseInt(d.ptav || d.ptavId || d.productTemplateAttributeValueId ||
               d.productTemplateAttributeValue || d.ptav_id || d.ptavl || '0', 10) || null;
    const av =
      parseInt(d.valueId || d.attributeValueId || inp.value || '0', 10) || null;
    return { ptavId: ptav, avId: av };
  }
  function getAttributeBlocks(root) {
    const blocks = [];
    const containers = root.querySelectorAll('[data-attribute_name], .o_wsale_product_attribute[data-attribute-name]');
    containers.forEach((el) => {
      const name = (el.getAttribute('data-attribute_name') || el.getAttribute('data-attribute-name') || '').trim();
      const options = [];
      el.querySelectorAll('input[type="radio"],input[type="checkbox"]').forEach((inp) => {
        const { ptavId, avId } = readIds(inp);
        const label = (inp.closest('label')?.textContent || inp.title || '').trim();
        if (ptavId || avId) options.push({ name: label, ptavId, avId, id: ptavId || avId });
      });
      if (options.length) blocks.push({ name, options, el });
    });
    return blocks;
  }
  function pickColorAndSize(blocks) {
    const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
    const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');
    let color = blocks.find(b => isColor(b.name));
    let size  = blocks.find(b => isSize(b.name));
    if (!size && blocks.length === 1) {
      size = { name: 'One Size', options: [{ id: -1, name: 'One Size', ptavId: null, avId: null }], _synthetic: true };
      if (!color) color = blocks[0];
    }
    if (!color && blocks.length) color = blocks[0];
    if (!size  && blocks.length > 1) size  = blocks[1];
    return { color, size };
  }

  // ---------- HTTP helpers ----------
  async function httpPlain(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
    const data = await res.json();
    return data?.result ?? data;
  }
  async function httpRpc(url, payload) {
    return httpPlain(url, { jsonrpc: '2.0', method: 'call', params: payload, id: Date.now() });
  }

  // ---------- datos de producto ----------
  function currentTemplateId(root) {
    return parseInt(
      root.querySelector('[data-product-template-id]')?.dataset.productTemplateId
      || root.querySelector('input[name="product_template_id"]')?.value
      || root.querySelector('input[name="product_id"]')?.value || 0, 10);
  }
  function comboArgs(ids, root) {
    const tmplId = currentTemplateId(root);
    const pricelistId = parseInt(document.querySelector('[data-pricelist-id]')?.dataset.pricelistId || 0, 10);
    return {
      product_template_id: tmplId || undefined,
      product_id: 0,
      combination: ids, // PTAV preferido
      add_qty: 1,
      parent_combination: [],
      pricelist_id: pricelistId || undefined,
    };
  }
  async function fetchCombinationWith(ids, root) {
    const args = comboArgs(ids, root);
    const tries = [
      () => httpPlain('/shop/get_combination_info', args),
      () => httpRpc('/shop/get_combination_info', args),
      () => httpPlain('/sale/get_combination_info', args),
      () => httpRpc('/sale/get_combination_info', args),
    ];
    for (const t of tries) {
      try {
        const res = await t();
        if (res && (res.product_id || res.product_template_id)) return res;
      } catch { /* siguiente */ }
    }
    return null;
  }
  // Fallback fuerte: encontrar variante por PTAV/AV con search_read
  async function searchVariantFallback(root, { cPTAV, sPTAV, cAV, sAV }) {
    const tmplId = currentTemplateId(root);
    const domain = [['product_tmpl_id', '=', tmplId]];
    if (cPTAV) domain.push(['product_template_attribute_value_ids', 'in', [cPTAV]]);
    if (sPTAV) domain.push(['product_template_attribute_value_ids', 'in', [sPTAV]]);
    // si no hay PTAV, probamos por AV (campo many2many en producto 17/18: product_variant_value_ids o attribute_value_ids según versión)
    const altFields = ['product_variant_value_ids', 'attribute_value_ids'];
    const fields = ['id', 'list_price', 'qty_available', 'image_128'];
    // primer intento por PTAV
    try {
      const res = await httpRpc('/web/dataset/call_kw', {
        model: 'product.product', method: 'search_read',
        args: [domain], kwargs: { fields, limit: 1 },
      });
      if (Array.isArray(res) && res.length) return {
        product_id: res[0].id,
        price: res[0].list_price,
        stock_quantity: res[0].qty_available,
      };
    } catch { /* siguiente */ }
    // segundo intento por AV
    for (const f of altFields) {
      const d2 = [['product_tmpl_id', '=', tmplId]];
      if (cAV) d2.push([f, 'in', [cAV]]);
      if (sAV) d2.push([f, 'in', [sAV]]);
      try {
        const res2 = await httpRpc('/web/dataset/call_kw', {
          model: 'product.product', method: 'search_read',
          args: [d2], kwargs: { fields, limit: 1 },
        });
        if (Array.isArray(res2) && res2.length) return {
          product_id: res2[0].id,
          price: res2[0].list_price,
          stock_quantity: res2[0].qty_available,
        };
      } catch { /* seguir */ }
    }
    return null;
  }
  async function getStock(variantId) {
    try {
      const res = await httpRpc('/web/dataset/call_kw', {
        model: 'product.product', method: 'read',
        args: [[variantId], ['qty_available']], kwargs: {},
      });
      return (res && res[0] && typeof res[0].qty_available === 'number') ? res[0].qty_available : null;
    } catch { return null; }
  }
  function fmtPrice(v) {
    try {
      const lang = document.documentElement.lang || 'es-ES';
      const curr = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
      return new Intl.NumberFormat(lang, { style: 'currency', currency: curr }).format(v);
    } catch { return (Math.round(v * 100) / 100).toFixed(2); }
  }

  // ---------- construir tabla ----------
  async function buildMatrix() {
    const root = getJsProduct();
    if (!root) return;

    const blocks = getAttributeBlocks(root);
    if (!blocks.length) return;
    const { color, size } = pickColorAndSize(blocks);
    if (!color || !size) return;

    const anchor = placeAnchor();
    anchor.innerHTML = '';

    const wrap = document.createElement('div'); wrap.className = 'sp-matrix';
    const table = document.createElement('table'); table.className = 'sp-matrix__table';

    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    trh.innerHTML = `<th class="sp-sticky-left">Color</th>`;
    size.options.forEach(s => { const th = document.createElement('th'); th.textContent = s.name; trh.appendChild(th); });
    thead.appendChild(trh);

    const tbody = document.createElement('tbody');
    color.options.forEach(c => {
      const tr = document.createElement('tr');
      tr.dataset.colorPtav = c.ptavId || '';
      tr.dataset.colorAv   = c.avId   || '';
      tr.dataset.colorId   = c.id     || '';
      tr.innerHTML = `
        <th class="sp-sticky-left">
          <div class="sp-color">
            <img class="sp-color__img" alt="">
            <span class="sp-color__name">${c.name || ''}</span>
          </div>
        </th>`;
      size.options.forEach(s => {
        const td = document.createElement('td');
        td.dataset.sizePtav = s.ptavId || '';
        td.dataset.sizeAv   = s.avId   || '';
        td.dataset.sizeId   = s.id     || '';
        td.innerHTML = `
          <div class="sp-cell">
            <input class="sp-qty" type="number" min="0" step="1"
                   data-color-ptav="${c.ptavId || ''}" data-size-ptav="${s.ptavId || ''}"
                   data-color-id="${c.id || ''}" data-size-id="${s.id || ''}">
            <div class="sp-meta"><span class="sp-price">—</span><span class="sp-stock">—</span></div>
          </div>`;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.append(thead, tbody);
    wrap.appendChild(table);

    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'btn btn-primary mt-2 sp-add-to-cart'; btn.textContent = 'Añadir selección';
    wrap.appendChild(btn);

    anchor.appendChild(wrap);

    hydrateCells(wrap, root);
    btn.addEventListener('click', () => addAllToCart(wrap));
  }

  // ---------- hidratar ----------
  async function hydrateCells(container, root) {
    const cells = Array.from(container.querySelectorAll('td'));
    const queue = cells.slice();

    async function worker() {
      while (queue.length) {
        const td = queue.shift();

        const cPTAV = parseInt(td.closest('tr')?.dataset.colorPtav || '0', 10)
                   || parseInt(td.closest('tr')?.dataset.colorId   || '0', 10);
        const sPTAV = parseInt(td.dataset.sizePtav || '0', 10)
                   || parseInt(td.dataset.sizeId   || '0', 10);
        const cAV   = parseInt(td.closest('tr')?.dataset.colorAv || '0', 10) || 0;
        const sAV   = parseInt(td.dataset.sizeAv || '0', 10) || 0;

        // 1) combo por PTAV / AV
        let combo = sPTAV > 0 ? [cPTAV, sPTAV] : [cPTAV];
        let info = await fetchCombinationWith(combo, root);
        if ((!info || !info.product_id) && (cAV || sAV)) {
          combo = sAV > 0 ? [cAV, sAV] : [cAV];
          info = await fetchCombinationWith(combo, root);
        }
        // 2) fallback por search_read
        if (!info || !info.product_id) {
          info = await searchVariantFallback(root, { cPTAV, sPTAV, cAV, sAV });
        }

        if (info && info.product_id) {
          td.querySelector('.sp-qty').dataset.variantId = info.product_id;

          const price = (typeof info.price === 'number') ? info.price
                      : (typeof info.list_price === 'number') ? info.list_price
                      : (typeof info.website_price === 'number') ? info.website_price : null;
          if (price !== null) td.querySelector('.sp-price').textContent = fmtPrice(price);

          let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
          if (stock === null) stock = await getStock(info.product_id);
          if (stock !== null) td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;

          const img = td.closest('tr').querySelector('.sp-color__img');
          if (img && !img.src) img.src = `/web/image/product.product/${info.product_id}/image_128`;
        } else {
          td.classList.add('sp-unavailable');
        }
      }
    }

    await Promise.all(new Array(6).fill(0).map(worker));
    log('matrix hidratada');
  }

  // ---------- carrito ----------
  function addAllToCart(container) {
    const inputs = container.querySelectorAll('.sp-qty');
    const ops = [];
    inputs.forEach((inp) => {
      const qty = parseFloat(inp.value || '0');
      const product_id = parseInt(inp.dataset.variantId || '0', 10);
      if (qty > 0 && product_id) {
        ops.push(fetch('/shop/cart/update_json', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
          body: JSON.stringify({ product_id, add_qty: qty, display: false }),
        }));
      }
    });
    if (!ops.length) return;
    Promise.allSettled(ops).then(() => window.location.reload());
  }

  // ---------- debug util ----------
  window._sp = {
    debug: {
      blocks: () => getAttributeBlocks(getJsProduct()),
      test: async () => {
        const root = getJsProduct();
        const { color, size } = pickColorAndSize(getAttributeBlocks(root));
        const c = color?.options?.[0]; const s = size?.options?.[0];
        if (!c) return console.warn('[SP] sin opciones');
        const ids = [c.ptavId || c.id].concat(s ? [s.ptavId || s.id] : []);
        const r = await fetchCombinationWith(ids, root);
        console.log('[SP] test combo ->', ids, r);
        return r;
      },
    },
  };

  // ---------- boot ----------
  function start() { if (document.querySelector('.o_wsale_product_page')) buildMatrix(); }
  (document.readyState === 'loading') ? document.addEventListener('DOMContentLoaded', start) : start();
})();