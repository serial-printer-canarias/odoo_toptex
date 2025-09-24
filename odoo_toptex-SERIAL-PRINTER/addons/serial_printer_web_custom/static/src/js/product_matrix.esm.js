// SP Matrix – Odoo 18 (PTAV-aware): precio, stock, foto y carrito en bloque
(function () {
  'use strict';

  const log  = (...a) => console.log('[SP]', ...a);
  const warn = (...a) => console.warn('[SP]', ...a);

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

  // ---------- leer bloques de atributos (PTAV/AV ids) ----------
  function readIds(inp) {
    const d = inp.dataset || {};
    const ptav =
      parseInt(d.ptav || d.ptavId || d.productTemplateAttributeValueId || d.productTemplateAttributeValue || d.ptav_id || d.ptavl || '0', 10) || null;
    const av =
      parseInt(d.valueId || d.attributeValueId || inp.value || '0', 10) || null;
    return { ptavId: ptav, avId: av };
  }
  function getAttributeBlocks(root) {
    const blocks = [];
    const containers = root.querySelectorAll(
      '[data-attribute_name], .o_wsale_product_attribute[data-attribute-name]'
    );
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

    // Si sólo hay 1 bloque (One Size oculto), fabricamos tamaño sintético
    if (!size && blocks.length === 1) {
      size = { name: 'One Size', options: [{ id: -1, name: 'One Size', ptavId: null }], _synthetic: true };
      if (!color) color = blocks[0];
    }
    if (!color && blocks.length) color = blocks[0];
    if (!size  && blocks.length > 1) size  = blocks[1];
    return { color, size };
  }

  // ---------- RPC genérico ----------
  async function rpc(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: payload, id: Date.now() }),
    });
    const txt = await res.text();
    if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
    try {
      const data = JSON.parse(txt);
      if (data.error) throw data.error;
      return data.result;
    } catch (e) {
      throw new Error(`RPC parse fail @ ${url}: ${txt?.slice(0, 180)}`);
    }
  }

  // ---------- utilidades ----------
  function fmtPrice(v) {
    try {
      const lang = document.documentElement.lang || 'es-ES';
      const curr = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
      return new Intl.NumberFormat(lang, { style: 'currency', currency: curr }).format(v);
    } catch {
      return (Math.round(v * 100) / 100).toFixed(2);
    }
  }
  function keyFromPtavs(arr) {
    return (arr || []).filter(Boolean).map(n => parseInt(n, 10)).sort((a,b)=>a-b).join('-');
  }
  function getTemplateId(root) {
    return parseInt(
      root.querySelector('[data-product-template-id]')?.dataset.productTemplateId
      || root.querySelector('input[name="product_template_id"]')?.value
      || root.querySelector('input[name="product_id"]')?.value
      || '0', 10);
  }

  // ---------- CARGA MASIVA DE VARIANTES (sin /shop/get_combination_info) ----------
  async function fetchAllVariants(root) {
    const tmplId = getTemplateId(root);
    if (!tmplId) { warn('sin template_id'); return { byKey: {}, list: [] }; }

    // Pedimos todas las variantes del template publicadas en web
    const payload = {
      model: 'product.product',
      method: 'search_read',
      args: [],
      kwargs: {
        domain: [['product_tmpl_id', '=', tmplId]],
        // Si quieres filtrar a publicadas: descomenta
        // domain: [['product_tmpl_id', '=', tmplId], ['website_published', '=', true]],
        fields: [
          'id',
          'product_template_attribute_value_ids', // PTAVs
          'lst_price', 'website_price', 'price',   // precio disponible
          'qty_available', 'virtual_available',    // stock
        ],
        limit: 2000,
      },
    };

    let rows = [];
    try {
      rows = await rpc('/web/dataset/call_kw', payload);
    } catch (e) {
      warn('error search_read variantes', e);
      return { byKey: {}, list: [] };
    }

    // Indexamos por conjunto de PTAVs
    const byKey = {};
    rows.forEach((r) => {
      const ptavs = Array.isArray(r.product_template_attribute_value_ids)
        ? r.product_template_attribute_value_ids : [];
      const k = keyFromPtavs(ptavs);
      byKey[k] = {
        id: r.id,
        price: (typeof r.website_price === 'number') ? r.website_price
              : (typeof r.price === 'number') ? r.price
              : (typeof r.lst_price === 'number') ? r.lst_price : null,
        stock: (typeof r.qty_available === 'number') ? r.qty_available
              : (typeof r.virtual_available === 'number') ? r.virtual_available : null,
        ptavs,
      };
    });

    log('variantes cargadas', rows.length);
    return { byKey, list: rows };
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
    const table = document.createElement('table'); table.className = 'sp-matrix__table sp-matrix--ready';

    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    trh.innerHTML = `<th class="sp-sticky-left">Color</th>`;
    size.options.forEach(s => { const th = document.createElement('th'); th.textContent = s.name; trh.appendChild(th); });
    thead.appendChild(trh);

    const tbody = document.createElement('tbody');
    color.options.forEach(c => {
      const tr = document.createElement('tr');
      tr.dataset.colorPtav = c.ptavId || '';
      tr.dataset.colorId   = c.id || '';
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
        td.dataset.sizeId   = s.id || '';
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

    // Hidratar con variantes (precio/stock/foto) SIN tocar nada más
    hydrateCells(wrap, root);
    btn.addEventListener('click', () => addAllToCart(wrap));
  }

  // ---------- hidratar desde cache de variantes ----------
  async function hydrateCells(container, root) {
    const { byKey } = await fetchAllVariants(root);
    const cells = Array.from(container.querySelectorAll('td'));

    for (const td of cells) {
      const colorPtav = parseInt(td.closest('tr')?.dataset.colorPtav || td.closest('tr')?.dataset.colorId || '0', 10) || null;
      const sizePtav  = parseInt(td.dataset.sizePtav || td.dataset.sizeId || '0', 10) || null;

      const comboPTAVs = [colorPtav, sizePtav].filter(Boolean);
      const key = keyFromPtavs(comboPTAVs);
      const v = byKey[key];

      if (v && v.id) {
        // ID variante para el carrito
        td.querySelector('.sp-qty').dataset.variantId = v.id;

        // Precio
        if (typeof v.price === 'number') td.querySelector('.sp-price').textContent = fmtPrice(v.price);

        // Stock
        if (typeof v.stock === 'number') td.querySelector('.sp-stock').textContent = `Stock: ${v.stock}`;

        // Foto por variante (lazy: sólo primera de la fila)
        const img = td.closest('tr').querySelector('.sp-color__img');
        if (img && !img.src) img.src = `/web/image/product.product/${v.id}/image_128`;
      } else {
        td.classList.add('sp-unavailable');
      }
    }
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

  // ---------- boot ----------
  function start() {
    if (document.querySelector('.o_wsale_product_page')) {
      log('boot sp-matrix');
      buildMatrix();
    }
  }
  (document.readyState === 'loading')
    ? document.addEventListener('DOMContentLoaded', start)
    : start();
})();