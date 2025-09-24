/** SP Matrix (Odoo 18) – grid con precio/stock y “añadir en bloque”
 *  - Se inserta JUSTO debajo de los atributos del configurador.
 *  - Imagen por color (fila), precio + stock por celda (color x talla).
 *  - Añadir al carrito todas las cantidades > 0.
 */
(function () {
  'use strict';

  const log  = (...a) => (_sp?.debug?.log || console.log.bind(console, '[SP]'))(...a);
  const ok   = (m) => (_sp?.debug?.ok  || console.log.bind(console, '%c[SP] '+m,'color:#0a0'))();
  const warn = (m) => (_sp?.debug?.warn|| console.warn.bind(console, '[SP]', m))();

  // ---------- Localizadores robustos ----------
  function getJsProduct() {
    return document.querySelector('.o_wsale_product_page .js_product') ||
           document.querySelector('.js_product') ||
           document.querySelector('.o_wsale_product_page');
  }
  function placeAnchor() {
    let anchor = document.getElementById('sp-matrix-anchor');
    if (!anchor) {
      anchor = document.createElement('div');
      anchor.id = 'sp-matrix-anchor';
      anchor.className = 'sp-matrix-anchor';
    }
    const jsProduct = getJsProduct();
    if (!jsProduct) return document.body.appendChild(anchor), anchor;

    // Preferimos justo DESPUÉS del bloque de atributos
    const attrsWrap =
      jsProduct.querySelector('.js_attributes') ||
      jsProduct.querySelector('ul.o_wsale_product_attribute') ||
      jsProduct.querySelector('[data-attribute_name]')?.closest('.row, ul, div');
    if (attrsWrap) {
      attrsWrap.after(anchor);
    } else {
      // Fallback: después del precio
      const price = jsProduct.querySelector('.product_price, .o_wsale_product_price_section');
      (price || jsProduct).after(anchor);
    }
    return anchor;
  }

  // ---------- Leer bloques de atributos (color/talla) ----------
  function getAttributeBlocks(root) {
    const blocks = [];
    (root.querySelectorAll('[data-attribute_name]') || []).forEach((el) => {
      const name = (el.getAttribute('data-attribute_name') || '').trim();
      const options = [];
      el.querySelectorAll('input[type="radio"], input[type="checkbox"]').forEach((inp) => {
        const id =
          parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value, 10);
        const label = (inp.closest('label')?.textContent || inp.title || '').trim();
        if (id) options.push({ id, name: label });
      });
      if (options.length) blocks.push({ name, options, el });
    });
    return blocks;
  }
  function pickColorAndSize(blocks) {
    const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
    const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');
    let color = blocks.find(b => isColor(b.name)), size = blocks.find(b => isSize(b.name));
    if (!color && blocks.length) color = blocks[0];
    if (!size  && blocks.length > 1) size  = blocks[1];
    return { color, size };
  }

  // ---------- RPC helpers ----------
  function comboArgs(avIds, root) {
    const tmplId = parseInt(
      root.querySelector('[data-product-template-id]')?.dataset.productTemplateId ||
      root.querySelector('input[name="product_template_id"]')?.value ||
      root.querySelector('input[name="product_id"]')?.value || 0, 10);
    const pricelistId = parseInt(
      document.querySelector('[data-pricelist-id]')?.dataset.pricelistId || 0, 10);

    return {
      product_template_id: tmplId || undefined,
      product_id: 0,
      combination: avIds,
      add_qty: 1,
      parent_combination: [],
      pricelist_id: pricelistId || undefined,
    };
  }
  async function fetchCombination(avIds, root) {
    const args = comboArgs(avIds, root);
    // 1º /shop, 2º /sale (compat)
    try {
      const r = await fetch('/shop/get_combination_info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ args: [args], kwargs: {} }),
      });
      if (r.ok) return (await r.json()).result;
      throw new Error('shop 4xx');
    } catch {
      try {
        const r = await fetch('/sale/get_combination_info', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ args: [args], kwargs: {} }),
        });
        if (r.ok) return (await r.json()).result;
      } catch (e) { /* ignore */ }
    }
    return null;
  }
  async function getStock(variantId) {
    try {
      const r = await fetch('/web/dataset/call_kw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'product.product', method: 'read',
          args: [[variantId], ['qty_available']], kwargs: {},
        }),
      });
      const data = await r.json();
      return (Array.isArray(data.result) && data.result[0] && typeof data.result[0].qty_available === 'number')
        ? data.result[0].qty_available
        : null;
    } catch { return null; }
  }
  function fmtPrice(v) {
    try {
      const lang = document.documentElement.lang || 'es-ES';
      const curr = document.querySelector('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
      return new Intl.NumberFormat(lang, { style: 'currency', currency: curr }).format(v);
    } catch { return (Math.round(v * 100) / 100).toFixed(2); }
  }

  // ---------- Pintar tabla ----------
  async function buildMatrix() {
    const jsProduct = getJsProduct();
    if (!jsProduct) return warn('No se encontró .js_product');

    const anchor = placeAnchor();
    if (!anchor) return warn('Sin ancla');

    const blocks = getAttributeBlocks(jsProduct);
    if (blocks.length < 2) return warn('No hay suficientes atributos para matriz');

    const { color, size } = pickColorAndSize(blocks);
    if (!color || !size) return warn('Faltan color/talla');

    // Reset anchor
    anchor.innerHTML = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'sp-matrix';
    const table = document.createElement('table');
    table.className = 'sp-matrix__table';

    // THEAD
    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    trh.innerHTML = `<th class="sp-sticky-left">Color</th>`;
    size.options.forEach(s => {
      const th = document.createElement('th');
      th.textContent = s.name || '';
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    // TBODY
    const tbody = document.createElement('tbody');
    color.options.forEach(c => {
      const tr = document.createElement('tr');
      tr.setAttribute('data-color-id', c.id);
      tr.innerHTML = `
        <th class="sp-sticky-left">
          <div class="sp-color">
            <img class="sp-color__img" alt="">
            <span class="sp-color__name">${(c.name || '')}</span>
          </div>
        </th>`;
      size.options.forEach(s => {
        const td = document.createElement('td');
        td.setAttribute('data-size-id', s.id);
        td.innerHTML = `
          <div class="sp-cell">
            <input class="sp-qty" type="number" min="0" step="1"
                   data-color-id="${c.id}" data-size-id="${s.id}">
            <div class="sp-meta">
              <span class="sp-price"></span>
              <span class="sp-stock"></span>
            </div>
          </div>`;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.append(thead, tbody);
    wrapper.appendChild(table);

    // Botón añadir
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-primary mt-2 sp-add-to-cart';
    btn.textContent = 'Añadir selección';
    wrapper.appendChild(btn);

    anchor.appendChild(wrapper);
    ok('Matrix renderizada');

    hydrateCells(wrapper, jsProduct);
    btn.addEventListener('click', () => addAllToCart(wrapper));
  }

  // ---------- Hidratar celdas con variante/price/stock/img ----------
  async function hydrateCells(root, jsProduct) {
    const cells = Array.from(root.querySelectorAll('td'));
    const q = cells.slice(); // cola

    async function worker() {
      while (q.length) {
        const td = q.shift();
        const colorId = parseInt(td.closest('tr').dataset.colorId, 10);
        const sizeId  = parseInt(td.dataset.sizeId, 10);
        const info = await fetchCombination([colorId, sizeId], jsProduct);

        if (info && info.product_id) {
          td.querySelector('.sp-qty').dataset.variantId = info.product_id;

          // Precio
          const price = (typeof info.price === 'number') ? info.price
                      : (typeof info.list_price === 'number') ? info.list_price
                      : null;
          if (price !== null) td.querySelector('.sp-price').textContent = fmtPrice(price);

          // Stock (preferir info.stock_quantity si viene)
          let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
          if (stock === null) stock = await getStock(info.product_id);
          if (stock !== null) td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;

          // Imagen por fila (si no está aún)
          const img = td.closest('tr').querySelector('.sp-color__img');
          if (img && !img.src) img.src = `/web/image/product.product/${info.product_id}/image_128`;
        } else {
          td.classList.add('sp-unavailable');
          td.querySelector('.sp-price').textContent = '—';
          td.querySelector('.sp-stock').textContent = '';
        }
      }
    }
    await Promise.all(new Array(6).fill(0).map(worker));
    ok('Celdas hidratadas');
  }

  // ---------- Añadir al carrito en bloque ----------
  function addAllToCart(root) {
    const inputs = root.querySelectorAll('.sp-qty');
    const ops = [];
    inputs.forEach((inp) => {
      const qty = parseFloat(inp.value || '0');
      const product_id = parseInt(inp.dataset.variantId || '0', 10);
      if (qty > 0 && product_id) {
        ops.push(fetch('/shop/cart/update_json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ product_id, add_qty: qty, display: false }),
        }));
      }
    });
    if (!ops.length) return;
    Promise.allSettled(ops).then(() => window.location.reload());
  }

  // Boot
  function start() {
    const onProd = !!document.querySelector('.o_wsale_product_page');
    if (!onProd) return;
    buildMatrix();
  }
  (document.readyState === 'loading')
    ? document.addEventListener('DOMContentLoaded', start)
    : start();
})();