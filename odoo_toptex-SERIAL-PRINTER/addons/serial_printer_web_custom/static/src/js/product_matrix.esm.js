/*
  Serial Printer Web Custom - Product Matrix (Odoo 18/19)
  - Injects a Color x Size matrix on product page
  - Shows stock per variant (best-effort via get_combination_info)
  - Allows bulk add-to-cart
*/
(function () {
  'use strict';

  const log = (...a) => console.log('[SP-MATRIX]', ...a);
  const warn = (...a) => console.warn('[SP-MATRIX]', ...a);

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  function getRoot() {
    return (
      document.querySelector('.o_wsale_product_page') ||
      document.querySelector('.js_product') ||
      document.querySelector('#wrapwrap') ||
      document
    );
  }

  function getCsrf() {
    return (
      document.querySelector('meta[name="csrf_token"]')?.getAttribute('content') ||
      document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ||
      window.odoo?.csrf_token ||
      document.querySelector('input[name="csrf_token"]')?.value ||
      ''
    );
  }

  function readCtx(root) {
    // Try many places; theme differences
    const el =
      root.querySelector('[data-product-template-id]') ||
      root.querySelector('.js_product[data-product-template-id]') ||
      root.querySelector('.js_product') ||
      root;

    const ds = el?.dataset || {};

    // product template
    const tmplId = parseInt(
      ds.productTemplateId ||
      ds.product_template_id ||
      ds.productTemplate ||
      root.querySelector('input[name="product_template_id"]')?.value ||
      '0',
      10
    ) || 0;

    // current variant (if available)
    const productId = parseInt(
      ds.productProductId ||
      ds.product_product_id ||
      ds.productProduct ||
      root.querySelector('input[name="product_id"]')?.value ||
      '0',
      10
    ) || 0;

    return { tmplId, productId };
  }

  function readIdsFromInput(inp) {
    // Odoo usually stores ptav id in input.value. Some themes store value_id in dataset.
    const ptav = parseInt(inp.value || '0', 10);
    const av = parseInt(inp.dataset.value_id || inp.dataset.valueId || inp.dataset.valueid || '0', 10);
    const id = ptav || av;
    return { id, ptavId: ptav || null, avId: av || null };
  }

  function normalizeLabel(s) {
    return String(s || '').replace(/\s+/g, ' ').trim();
  }

  function getBlocks(root) {
    const blocks = [];

    // Odoo 19: <li name="variant_attribute" data-attribute-name="..." data-attribute-display-type="...">
    // Odoo <=18: legacy selectors kept as fallback.
    const containers = root.querySelectorAll(
      '[name="variant_attribute"][data-attribute-name], .variant_attribute[data-attribute-name], .o_wsale_product_attribute[data-attribute-name], [data-attribute_name]'
    );

    containers.forEach(el => {
      const name = (
        el.dataset.attributeName ||
        el.getAttribute('data-attribute-name') ||
        el.dataset.attribute_name ||
        el.getAttribute('data-attribute_name') ||
        ''
      ).toString().trim();

      const displayType = (
        el.dataset.attributeDisplayType ||
        el.getAttribute('data-attribute-display-type') ||
        el.dataset.displayType ||
        el.getAttribute('data-display-type') ||
        ''
      ).toString().trim();

      const options = [];

      // 1) Inputs (radio/checkbox)
      el.querySelectorAll('input[type="radio"],input[type="checkbox"]').forEach(inp => {
        const o = readIdsFromInput(inp);
        const labelEl = inp.closest('label');
        const label = normalizeLabel((labelEl ? labelEl.textContent : '') || inp.title || inp.getAttribute('aria-label') || '');
        if (o.id) options.push({ name: label, ...o });
      });

      // 2) Selects (display_type = select)
      el.querySelectorAll('select.js_variant_change, select.css_attribute_select, select').forEach(sel => {
        sel.querySelectorAll('option').forEach(opt => {
          const id = parseInt(opt.value || '0', 10);
          if (!id) return;
          const label = normalizeLabel(opt.textContent);
          options.push({ id, ptavId: id, avId: null, name: label });
        });
      });

      // De-dup by id (because some themes duplicate nodes)
      const seen = new Set();
      const uniq = [];
      for (const o of options) {
        const k = String(o.id || 0);
        if (!o.id || seen.has(k)) continue;
        seen.add(k);
        uniq.push(o);
      }

      if (uniq.length) blocks.push({ name, displayType, options: uniq, el });
    });

    return blocks;
  }

  function sortSizes(opts) {
    const order = [
      'XXS', '2XS', 'XS', 'S', 'M', 'L', 'XL', '2XL', 'XXL', '3XL', 'XXXL', '4XL', '5XL', '6XL',
      '28', '30', '32', '34', '36', '38', '40', '42', '44', '46', '48', '50', '52', '54',
    ];
    const norm = (s) => (s || '').toString().trim().toUpperCase();
    return [...opts].sort((a, b) => {
      const A = norm(a.name);
      const B = norm(b.name);
      const ia = order.indexOf(A);
      const ib = order.indexOf(B);
      if (ia !== -1 && ib !== -1) return ia - ib;
      if (ia !== -1) return -1;
      if (ib !== -1) return 1;
      const na = parseInt(A, 10);
      const nb = parseInt(B, 10);
      if (!isNaN(na) && !isNaN(nb)) return na - nb;
      return A.localeCompare(B);
    });
  }

  function pickColorSize(blocks) {
    const isColorName = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || '');
    const isSizeName  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || '');

    const isColor = b => ['color', 'image'].includes(String(b.displayType || '').toLowerCase()) || isColorName(b.name);
    const isSize  = b => isSizeName(b.name);

    let color = blocks.find(isColor);
    let size  = blocks.find(isSize);

    // Si solo hay 1 atributo (ej: solo Color), creamos "Talla única" para poder mostrar matriz y sumar al carrito.
    if (!size && blocks.length === 1) {
      size = { name: 'One Size', options: [{ id: -1, name: 'One Size', ptavId: null }], _synthetic: true };
      if (!color) color = blocks[0];
    }

    // Fallback simple
    if (!color && blocks.length) color = blocks[0];
    if (!size && blocks.length > 1) size = blocks[1];

    if (size && Array.isArray(size.options)) size = { ...size, options: sortSizes(size.options) };
    return { color, size };
  }

  /* ---------------- JSON-RPC helpers ---------------- */
  async function rpc(url, params) {
    const payload = { jsonrpc: '2.0', method: 'call', params: params || {}, id: Date.now() };
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    const data = await res.json().catch(() => null);
    if (data?.error) {
      const msg = data.error?.data?.message || data.error?.message || 'RPC error';
      throw new Error(msg);
    }
    return (data && data.result !== undefined) ? data.result : data;
  }

  async function postCartForm(url, payload) {
    const fd = new FormData();
    Object.entries(payload || {}).forEach(([k, v]) => {
      if (v === undefined || v === null) return;
      if (Array.isArray(v)) v.forEach(x => fd.append(k, String(x)));
      else fd.append(k, String(v));
    });
    const res = await fetch(url, { method: 'POST', body: fd, credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
    return true;
  }

  /* ---------------- combination + stock ---------------- */
  async function getComboInfo(tmplId, productId, ptavIds) {
    if (!tmplId) return null;

    const params = {
      product_template_id: tmplId,
      product_id: productId || 0,
      combination: ptavIds || [],
      add_qty: 1,
      pricelist_id: 0,
      parent_combination: [],
      only_template: false,
    };

    for (const u of ['/website_sale/get_combination_info', '/shop/get_combination_info']) {
      try {
        const r = await rpc(u, params);
        if (r && typeof r === 'object') return r;
      } catch (e) {
        // try next
      }
    }
    return null;
  }

  function getStockFromComboInfo(info) {
    if (!info) return null;
    const cand = [
      info.free_qty,
      info.qty_available,
      info.virtual_available,
      info.stock_quantity,
      info.available_threshold,
      info.available_qty,
    ];
    for (const v of cand) {
      if (typeof v === 'number') return v;
      if (typeof v === 'string' && v.trim() !== '' && !isNaN(parseFloat(v))) return parseFloat(v);
    }
    return null;
  }

  /* ---------------- DOM rendering ---------------- */
  function findVariantsUl(root) {
    return (
      root.querySelector('ul.js_add_cart_variants') ||
      root.querySelector('ul.o_wsale_product_page_variants') ||
      document.querySelector('ul.js_add_cart_variants') ||
      document.querySelector('ul.o_wsale_product_page_variants')
    );
  }

  function placeAnchor() {
    // Prefer anchor rendered by QWeb. If missing, create it right after the variants block.
    let anchor = document.getElementById('sp-matrix-anchor');
    if (anchor) return anchor;

    anchor = document.createElement('div');
    anchor.id = 'sp-matrix-anchor';
    anchor.className = 'sp-matrix-anchor';
    anchor.dataset.spMatrixAnchor = '1';

    const root = getRoot();
    const variants = findVariantsUl(root);

    if (variants && variants.parentNode) {
      variants.parentNode.insertBefore(anchor, variants.nextSibling);
      return anchor;
    }

    (root.querySelector('.product_price, .o_wsale_product_price_section') ||
      root.querySelector('.o_wsale_product_page') ||
      root
    ).appendChild(anchor);

    return anchor;
  }

  function buildTable(color, size) {
    const container = document.createElement('div');
    container.className = 'sp-matrix card card-body shadow-sm';

    const title = document.createElement('div');
    title.className = 'd-flex align-items-center justify-content-between mb-2';
    title.innerHTML = `
      <div class="fw-bold">Stock por variante</div>
      <button type="button" class="btn btn-primary btn-sm" data-sp-add-all="1">
        <i class="fa fa-shopping-cart me-1"></i> Añadir selección
      </button>
    `;
    container.appendChild(title);

    const tableWrap = document.createElement('div');
    tableWrap.className = 'table-responsive';
    container.appendChild(tableWrap);

    const table = document.createElement('table');
    table.className = 'table table-sm align-middle sp-matrix__table';
    tableWrap.appendChild(table);

    const thead = document.createElement('thead');
    thead.innerHTML = `
      <tr>
        <th style="min-width:160px">${(color?.name || 'Color')}</th>
        ${size.options.map(s => `<th class="text-center" style="min-width:90px">${s.name || ''}</th>`).join('')}
      </tr>
    `;
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    table.appendChild(tbody);

    for (const c of color.options) {
      const tr = document.createElement('tr');
      tr.dataset.colorId = String(c.id || 0);
      tr.dataset.colorPtav = String(c.ptavId || c.id || 0);

      const td0 = document.createElement('td');
      td0.innerHTML = `
        <div class="d-flex align-items-center gap-2">
          <div class="sp-color__img rounded border bg-light" style="width:32px;height:32px;overflow:hidden"></div>
          <div class="sp-color__name small">${c.name || ''}</div>
        </div>
      `;
      tr.appendChild(td0);

      for (const s of size.options) {
        const td = document.createElement('td');
        td.className = 'text-center';
        td.dataset.sizeId = String(s.id || 0);
        td.dataset.sizePtav = String(s.ptavId || s.id || 0);

        td.innerHTML = `
          <div class="d-flex flex-column align-items-center gap-1">
            <div class="sp-stock badge text-bg-secondary" data-sp-stock="1">...</div>
            <input class="form-control form-control-sm sp-qty text-center" type="number" min="0" step="1" value="0" style="width:70px"/>
          </div>
        `;
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }

    return container;
  }

  async function ensureVariantIdFromCell(inp, root) {
    const td = inp.closest('td');
    const tr = inp.closest('tr');
    if (!td || !tr) return 0;

    if (td.dataset.variantId) return parseInt(td.dataset.variantId || '0', 10);

    const ctx = readCtx(root);
    const sizePtav = parseInt(td.dataset.sizePtav || td.dataset.sizeId || '0', 10);
    const colorPtav = parseInt(tr.dataset.colorPtav || tr.dataset.colorId || '0', 10);
    const ptavIds = (sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav]).filter(n => n > 0);

    const info = await getComboInfo(ctx.tmplId, ctx.productId, ptavIds);
    const vid = parseInt(info?.product_id || info?.product_product_id || info?.variant_id || '0', 10);
    if (vid) {
      td.dataset.variantId = String(vid);
      return vid;
    }
    return 0;
  }

  async function renderStocks(root, matrixEl) {
    const ctx = readCtx(root);
    const rows = $$('.sp-matrix__table tbody tr', matrixEl);

    for (const tr of rows) {
      const colorPtav = parseInt(tr.dataset.colorPtav || tr.dataset.colorId || '0', 10);
      const tds = $$('td', tr).slice(1);

      let anyVariantId = 0;

      for (const td of tds) {
        const sizePtav = parseInt(td.dataset.sizePtav || td.dataset.sizeId || '0', 10);
        const ptavIds = (sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav]).filter(n => n > 0);

        const info = await getComboInfo(ctx.tmplId, ctx.productId, ptavIds);
        const stock = getStockFromComboInfo(info);
        const badge = $('.sp-stock', td);

        if (badge) {
          if (stock === null) {
            badge.textContent = '-';
            badge.className = 'sp-stock badge text-bg-secondary';
          } else if (stock <= 0) {
            badge.textContent = '0';
            badge.className = 'sp-stock badge text-bg-danger';
          } else if (stock < 10) {
            badge.textContent = String(Math.round(stock));
            badge.className = 'sp-stock badge text-bg-warning';
          } else {
            badge.textContent = String(Math.round(stock));
            badge.className = 'sp-stock badge text-bg-success';
          }
        }

        const vid = parseInt(info?.product_id || '0', 10);
        if (vid) {
          td.dataset.variantId = String(vid);
          if (!anyVariantId) anyVariantId = vid;
        }

        await sleep(30);
      }

      if (anyVariantId) {
        const imgBox = $('.sp-color__img', tr);
        if (imgBox && !imgBox.querySelector('img')) {
          const img = document.createElement('img');
          img.alt = '';
          img.style.width = '100%';
          img.style.height = '100%';
          img.style.objectFit = 'cover';
          img.src = `/web/image/product.product/${anyVariantId}/image_128`;
          imgBox.appendChild(img);
        }
      }
    }
  }

  async function cartUpdateJson(product_id, add_qty) {
    const payload = {
      product_id,
      add_qty,
      set_qty: 0,
      display: false,
      product_custom_attribute_values: [],
      no_variant_attribute_values: [],
    };
    for (const u of ['/shop/cart/update_json', '/website_sale/cart/update_json']) {
      try {
        await rpc(u, payload);
        return true;
      } catch (e) {
        warn('Fallo update_json', u, e.message);
      }
    }
    return false;
  }

  async function addAllToCart(container) {
    const inputs = container.querySelectorAll('.sp-qty');
    const root = getRoot();
    const ctx = readCtx(root);
    const csrf = getCsrf();

    let count = 0;
    for (const inp of inputs) {
      const qty = parseFloat(inp.value || '0');
      if (!(qty > 0)) continue;

      const product_id = await ensureVariantIdFromCell(inp, root);
      if (!product_id) { warn('Sin variant_id para celda', inp); continue; }

      // 1) Preferimos update_json (Odoo 19, robusto)
      const okJson = await cartUpdateJson(product_id, qty);
      if (okJson) { count++; continue; }

      // 2) Fallback: POST clásico al form
      const td = inp.closest('td');
      const tr = inp.closest('tr');
      const sizePtav = parseInt(td?.dataset.sizePtav || td?.dataset.sizeId || '0', 10);
      const colorPtav = parseInt(tr?.dataset.colorPtav || tr?.dataset.colorId || '0', 10);
      const combination = (sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav]).filter(n => n > 0);

      const payload = {
        product_id,
        add_qty: qty,
        product_template_id: ctx.tmplId || undefined,
        combination,
        csrf_token: csrf || undefined,
      };

      let ok = false;
      for (const u of ['/shop/cart/update', '/website_sale/cart/update']) {
        try { await postCartForm(u, payload); ok = true; break; }
        catch (e) { warn('Fallo FORM', u, e.message); }
      }

      if (!ok) warn('NO se pudo añadir', { product_id, qty });
      else count++;
    }

    if (count > 0) window.location.reload();
  }

  async function bootOnce() {
    const root = getRoot();
    const ctx = readCtx(root);

    // Si todavía no hay bloque de variantes, no arrancamos
    const variantsUl = findVariantsUl(root);
    if (!variantsUl) return false;

    const blocks = getBlocks(root);
    if (!blocks.length) return false;

    const { color, size } = pickColorSize(blocks);
    if (!color || !size || !color.options?.length || !size.options?.length) return false;

    const anchor = placeAnchor();
    if (!anchor) return false;

    // Render
    anchor.innerHTML = '';
    const table = buildTable(color, size);
    anchor.appendChild(table);

    // events
    table.querySelector('[data-sp-add-all]')?.addEventListener('click', () => addAllToCart(table));

    // stock
    try {
      if (ctx.tmplId) await renderStocks(root, table);
      else warn('tmplId=0, no se puede consultar get_combination_info todavía');
    } catch (e) {
      warn('renderStocks error', e);
    }

    return true;
  }

  let _booting = false;
  async function bootWithRetry() {
    if (_booting) return;
    _booting = true;

    // Reintentos para Odoo 19 (DOM de variantes puede cargarse después)
    for (let i = 0; i < 30; i++) {
      try {
        const ok = await bootOnce();
        if (ok) { _booting = false; return; }
      } catch (e) {
        warn('boot error', e);
      }
      await sleep(250);
    }
    _booting = false;
  }

  function attachObserver() {
    const root = getRoot();
    const target = root === document ? document.body : root;
    if (!target || target.__spMatrixObs) return;
    target.__spMatrixObs = true;

    const obs = new MutationObserver(() => {
      const variantsUl = findVariantsUl(getRoot());
      if (variantsUl && !document.getElementById('sp-matrix-anchor')) {
        // si llega el UL primero, ancla y render
        placeAnchor();
      }
      bootWithRetry();
    });

    obs.observe(target, { childList: true, subtree: true });
  }

  // --- init ---
  log('loaded');

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      attachObserver();
      bootWithRetry();
    });
  } else {
    attachObserver();
    bootWithRetry();
  }

  window.addEventListener('pageshow', () => bootWithRetry());
})();

  }

  // wait DOM + variants widget
  document.addEventListener('DOMContentLoaded', () => boot());
})();
