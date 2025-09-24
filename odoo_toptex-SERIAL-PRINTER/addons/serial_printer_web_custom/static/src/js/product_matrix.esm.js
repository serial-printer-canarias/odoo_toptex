// SP Matrix – Odoo 18 (PTAV-aware): precio, stock, foto y carrito en bloque
(function () {
  'use strict';

  const LOG_TAG = '[SP]';
  const log = (...a) => console.log(LOG_TAG, ...a);
  const warn = (...a) => console.warn(LOG_TAG, ...a);

  // ---------------- helpers de anclaje ----------------
  function getJsProduct() {
    return (
      document.querySelector('.o_wsale_product_page .js_product') ||
      document.querySelector('.js_product') ||
      document.querySelector('.o_wsale_product_page')
    );
  }
  function placeAnchor() {
    let anchor = document.getElementById('sp-matrix-anchor');
    if (!anchor) {
      anchor = document.createElement('div');
      anchor.id = 'sp-matrix-anchor';
      anchor.className = 'sp-matrix-anchor';
    }
    const root = getJsProduct();
    if (!root) {
      document.body.appendChild(anchor);
      return anchor;
    }
    const attrs =
      root.querySelector('.js_attributes') ||
      root.querySelector('ul.o_wsale_product_attribute') ||
      root.querySelector('[data-attribute_name]')?.closest('.row, ul, div');
    (attrs ||
      root.querySelector('.product_price, .o_wsale_product_price_section') ||
      root
    ).after(anchor);
    return anchor;
  }

  // ---------------- leer bloques de atributos (PTAV) ----------------
  function readIds(inp) {
    const d = inp.dataset || {};
    // PTAV en distintas variantes de Odoo
    const ptav =
      parseInt(
        d.productTemplateAttributeValueId ||
          d.productTemplateAttributeValue ||
          d.ptavId ||
          d.ptav_id ||
          d.ptav ||
          '0',
        10
      ) || null;

    const av =
      parseInt(
        d.attributeValueId || d.valueId || inp.value || '0',
        10
      ) || null;

    return { ptavId: ptav, avId: av };
  }

  function getAttributeBlocks(root) {
    const blocks = [];
    const containers = root.querySelectorAll(
      '[data-attribute_name], .o_wsale_product_attribute[data-attribute-name]'
    );
    containers.forEach((el) => {
      const name =
        (el.getAttribute('data-attribute_name') ||
          el.getAttribute('data-attribute-name') ||
          '').trim();
      const options = [];
      el
        .querySelectorAll('input[type="radio"],input[type="checkbox"]')
        .forEach((inp) => {
          const { ptavId, avId } = readIds(inp);
          const label =
            (inp.closest('label')?.textContent || inp.title || '').trim();
          if (ptavId || avId) options.push({ name: label, ptavId, avId, id: ptavId || avId });
        });
      if (options.length) blocks.push({ name, options, el });
    });
    return blocks;
  }

  function pickColorAndSize(blocks) {
    const isColor = (n) => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
    const isSize = (n) => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');
    let color = blocks.find((b) => isColor(b.name));
    let size = blocks.find((b) => isSize(b.name));
    if (!size && blocks.length === 1) {
      // Sintético One Size
      size = { name: 'One Size', options: [{ id: -1, name: 'One Size', ptavId: null }], _synthetic: true };
      if (!color) color = blocks[0];
    }
    if (!color && blocks.length) color = blocks[0];
    if (!size && blocks.length > 1) size = blocks[1];
    return { color, size };
  }

  // ---------------- JSON helpers ----------------
  // Para controladores "website" (NO jsonrpc): /website_sale/get_combination_info
  async function websitePost(url, payload) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload || {}),
    });
    if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
    return await res.json(); // devuelve JSON plano
  }

  // Para /web/dataset/call_kw (jsonrpc)
  async function rpc(url, params) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        method: 'call',
        params,
        id: Date.now(),
      }),
    });
    if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
    const data = await res.json();
    if (data.error) throw data.error;
    return data.result;
  }

  // ---------------- combinación / stock ----------------
  function getIdsFromPage(root) {
    const tmplId = parseInt(
      root.querySelector('[data-product-template-id]')?.dataset.productTemplateId ||
        root.querySelector('input[name="product_template_id"]')?.value ||
        root.querySelector('input[name="product_id"]')?.value ||
        '0',
      10
    );
    const pricelistId = parseInt(
      document.querySelector('[data-pricelist-id]')?.dataset.pricelistId || '0',
      10
    );
    return { tmplId, pricelistId };
  }

  function comboArgs(ptavIds, root) {
    const { tmplId, pricelistId } = getIdsFromPage(root);
    return {
      product_id: 0,
      combination: ptavIds, // PTAVs
      add_qty: 1,
      parent_combination: [],
      product_template_id: tmplId || undefined,
      pricelist_id: pricelistId || undefined,
    };
  }

  async function fetchCombination(ptavIds, root) {
    // Siempre probamos la pública (website) primero.
    const args = comboArgs(ptavIds, root);
    try {
      log('probando /website_sale/get_combination_info', args);
      return await websitePost('/website_sale/get_combination_info', args);
    } catch (e1) {
      warn('respuesta con error en /website_sale/get_combination_info ►', e1);
      // Fallback: algunos themes exponen esta
      try {
        log('probando /shop/get_combination_info', args);
        return await websitePost('/shop/get_combination_info', args);
      } catch (e2) {
        warn('respuesta con error en /shop/get_combination_info ►', e2);
        return null;
      }
    }
  }

  async function getStock(variantId) {
    try {
      const res = await rpc('/web/dataset/call_kw', {
        model: 'product.product',
        method: 'read',
        args: [[variantId], ['qty_available']],
        kwargs: {},
      });
      const v = res && res[0] && typeof res[0].qty_available === 'number' ? res[0].qty_available : null;
      return v;
    } catch (e) {
      warn('search_read variantes Error:', e);
      return null;
    }
  }

  function fmtPrice(v) {
    try {
      const lang = document.documentElement.lang || 'es-ES';
      const curr =
        document.querySelector('[data-website-currency-code]')?.dataset
          .websiteCurrencyCode || 'EUR';
      return new Intl.NumberFormat(lang, { style: 'currency', currency: curr }).format(v);
    } catch {
      return (Math.round(v * 100) / 100).toFixed(2);
    }
  }

  // ---------------- construir tabla ----------------
  async function buildMatrix() {
    const root = getJsProduct();
    if (!root) return;

    const blocks = getAttributeBlocks(root);
    if (!blocks.length) return;

    const { color, size } = pickColorAndSize(blocks);
    if (!color || !size) return;

    const anchor = placeAnchor();
    anchor.innerHTML = '';

    const wrap = document.createElement('div');
    wrap.className = 'sp-matrix';

    const table = document.createElement('table');
    table.className = 'sp-matrix__table';

    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    trh.innerHTML = `<th class="sp-sticky-left">Color</th>`;
    size.options.forEach((s) => {
      const th = document.createElement('th');
      th.textContent = s.name;
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    const tbody = document.createElement('tbody');
    color.options.forEach((c) => {
      const tr = document.createElement('tr');
      tr.dataset.colorPtav = c.ptavId || '';
      tr.dataset.colorId = c.id || '';
      tr.innerHTML = `
        <th class="sp-sticky-left">
          <div class="sp-color">
            <img class="sp-color__img" alt="">
            <span class="sp-color__name">${c.name || ''}</span>
          </div>
        </th>`;
      size.options.forEach((s) => {
        const td = document.createElement('td');
        td.dataset.sizePtav = s.ptavId || '';
        td.dataset.sizeId = s.id || '';
        td.innerHTML = `
          <div class="sp-cell">
            <input class="sp-qty" type="number" min="0" step="1"
                   data-color-ptav="${c.ptavId || ''}" data-size-ptav="${s.ptavId || ''}"
                   data-color-id="${c.id || ''}" data-size-id="${s.id || ''}">
            <div class="sp-meta">
              <span class="sp-price">—</span>
              <span class="sp-stock">—</span>
            </div>
          </div>`;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    table.append(thead, tbody);
    wrap.appendChild(table);

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-primary mt-2 sp-add-to-cart';
    btn.textContent = 'Añadir selección';
    wrap.appendChild(btn);

    anchor.appendChild(wrap);

    hydrateCells(wrap, root);
    btn.addEventListener('click', () => addAllToCart(wrap));
  }

  // ---------------- hidratar celdas ----------------
  async function hydrateCells(container, root) {
    const cells = Array.from(container.querySelectorAll('td'));
    const queue = cells.slice();

    async function worker() {
      while (queue.length) {
        const td = queue.shift();

        // Leemos PTAV (preferente). Si no hay, caemos al id básico (puede no resolver combinación).
        const colorPtav =
          parseInt(td.closest('tr')?.dataset.colorPtav || '0', 10) ||
          parseInt(td.closest('tr')?.dataset.colorId || '0', 10);
        const sizePtav =
          parseInt(td.dataset.sizePtav || '0', 10) ||
          parseInt(td.dataset.sizeId || '0', 10);

        const combo = sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav];

        const info = await fetchCombination(combo, root);

        if (info && info.product_id) {
          td.classList.remove('sp-unavailable');
          const qtyInput = td.querySelector('.sp-qty');
          qtyInput.dataset.variantId = info.product_id;

          // Precio: intentamos diferentes claves posibles
          const price =
            typeof info.price === 'number'
              ? info.price
              : typeof info.list_price === 'number'
              ? info.list_price
              : typeof info.website_price === 'number'
              ? info.website_price
              : typeof info.display_price === 'number'
              ? info.display_price
              : null;

          if (price !== null) {
            td.querySelector('.sp-price').textContent = fmtPrice(price);
          }

          // Stock desde respuesta o fallback a read()
          let stock =
            info.stock_quantity ??
            info.stock_qty ??
            info.free_qty ??
            null;
          if (stock === null) stock = await getStock(info.product_id);
          if (stock !== null) {
            td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;
          }

          // Foto (si la variante no tiene, caerá a la del template)
          const img = td.closest('tr').querySelector('.sp-color__img');
          if (img && !img.src) {
            const { tmplId } = getIdsFromPage(root);
            img.src = `/web/image/product.product/${info.product_id}/image_128`;
            img.onerror = () => {
              img.src = `/web/image/product.template/${tmplId}/image_128`;
            };
          }
        } else {
          td.classList.add('sp-unavailable');
        }
      }
    }

    // 6 workers en paralelo
    await Promise.all(new Array(6).fill(0).map(worker));
    log('matrix hidratada sp-matrix');
  }

  // ---------------- carrito ----------------
  function addAllToCart(container) {
    const inputs = container.querySelectorAll('.sp-qty');
    const ops = [];
    inputs.forEach((inp) => {
      const qty = parseFloat(inp.value || '0');
      const product_id = parseInt(inp.dataset.variantId || '0', 10);
      if (qty > 0 && product_id) {
        ops.push(
          fetch('/shop/cart/update_json', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ product_id, add_qty: qty, display: false }),
          })
        );
      }
    });
    if (!ops.length) return;
    Promise.allSettled(ops).then(() => window.location.reload());
  }

  // ---------------- boot ----------------
  function start() {
    if (document.querySelector('.o_wsale_product_page')) buildMatrix();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();