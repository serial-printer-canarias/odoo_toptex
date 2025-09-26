/* SP Matrix – Odoo 18: precio, stock, foto y carrito (robusto) */
(function () {
  'use strict';

  const log  = (...a) => console.log('[SP]', ...a);
  const warn = (...a) => console.warn('[SP]', ...a);

  /* ---------------- helpers ---------------- */
  function $(sel, ctx=document){ return ctx.querySelector(sel); }

  function getRoot() {
    return $('.o_wsale_product_page .js_product')
        || $('.js_product')
        || $('.o_wsale_product_page')
        || $('[data-main-object="product.template"]')
        || document.body;
  }
  function placeAnchor() {
    let anchor = document.getElementById('sp-matrix-anchor');
    if (!anchor) {
      anchor = document.createElement('div');
      anchor.id = 'sp-matrix-anchor';
      anchor.className = 'sp-matrix-anchor';
    }
    const root = getRoot();
    const attrs = root.querySelector('.js_attributes')
      || root.querySelector('ul.o_wsale_product_attribute')
      || root.querySelector('[data-attribute_name]')?.closest('.row, ul, div');
    (attrs || root.querySelector('.product_price, .o_wsale_product_price_section') || root)
      .after(anchor);
    return anchor;
  }

  /* ---------- lectura de atributos (PTAV) ---------- */
  function readIdsFromInput(inp) {
    const d = inp.dataset || {};
    const ptav = parseInt(
      d.ptav || d.ptavId || d.productTemplateAttributeValueId ||
      d.productTemplateAttributeValue || d.ptav_id || d.ptavl || inp.value || '0', 10
    ) || null;
    const av = parseInt(d.valueId || d.attributeValueId || '0', 10) || null;
    return { ptavId: ptav, avId: av, id: ptav || av };
  }
  function getBlocks(root) {
    const blocks = [];
    const containers = root.querySelectorAll('[data-attribute_name], .o_wsale_product_attribute[data-attribute-name]');
    containers.forEach(el => {
      const name = (el.getAttribute('data-attribute_name') || el.getAttribute('data-attribute-name') || '').trim();
      const options = [];
      el.querySelectorAll('input[type="radio"],input[type="checkbox"]').forEach(inp => {
        const o = readIdsFromInput(inp);
        const label = (inp.closest('label')?.textContent || inp.title || '').trim();
        if (o.id) options.push({ name: label, ...o });
      });
      if (options.length) blocks.push({ name, options, el });
    });
    return blocks;
  }
  function pickColorSize(blocks) {
    const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n||'');
    const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n||'');
    let color = blocks.find(b => isColor(b.name));
    let size  = blocks.find(b => isSize(b.name));
    if (!size && blocks.length === 1) {
      size = { name: 'One Size', options: [{ id:-1, name:'One Size', ptavId:null }], _synthetic:true };
      if (!color) color = blocks[0];
    }
    if (!color && blocks.length) color = blocks[0];
    if (!size  && blocks.length > 1) size  = blocks[1];
    return { color, size };
  }

  /* ---------------- JSON-RPC robusto ---------------- */
  async function rpc(url, params) {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept':'application/json',
        'Content-Type':'application/json',
        'X-Requested-With':'XMLHttpRequest'
      },
      body: JSON.stringify({ jsonrpc:'2.0', method:'call', params, id: Date.now() }),
    });
    const ct = res.headers.get('content-type') || '';
    if (!res.ok) {
      const txt = await res.text().catch(()=> '');
      throw Object.assign(new Error(`HTTP ${res.status}`), { httpStatus: res.status, body: txt, url });
    }
    if (!/application\/json/i.test(ct)) {
      const txt = await res.text().catch(()=> '');
      throw Object.assign(new Error('Respuesta NO JSON'), { body: txt, url });
    }
    const data = await res.json();
    if (data?.error) {
      const e = data.error;
      const msg = (e.data && e.data.message) || e.message || 'RPC error';
      throw Object.assign(new Error(msg), { odoo: e, url });
    }
    return data.result;
  }

  /* ---------------- combo/ctx ---------------- */
  function readCtx(root) {
    const tmplId = parseInt(
      root.querySelector('[data-product-template-id]')?.dataset.productTemplateId
      || root.querySelector('input[name="product_template_id"]')?.value
      || root.getAttribute('data-oe-id') || '0', 10);
    const pricelistId = parseInt(document.querySelector('[data-pricelist-id]')?.dataset.pricelistId || '0', 10);
    return { tmplId, pricelistId };
  }
  function buildPayload(ptavIds, ctx) {
    return {
      product_template_id: ctx.tmplId,
      product_id: 0,
      combination: ptavIds,
      add_qty: 1,
      parent_combination: [],
      pricelist_id: ctx.pricelistId || undefined,
      only_template: false,
      no_variant_attribute_values: [],
      product_template_attribute_value_ids: [],
      is_main_product: true,
      display_default_code: true,
      strict: true,
    };
  }
  async function getCombo(ptavIds, root) {
    const ctx = readCtx(root);
    const payload = buildPayload(ptavIds, ctx);
    const urls = ['/website_sale/get_combination_info', '/shop/get_combination_info'];
    for (const u of urls) {
      try {
        const r = await rpc(u, payload);
        if (r) return r;
      } catch (e) {
        if (e.httpStatus === 404) { continue; }
        warn('combo fallo', u, e.message);
      }
    }
    return null;
  }

  /* ---- extractores tolerantes ---- */
  function getVariantId(info) {
    return parseInt(
      info?.product_id ?? info?.variant_id ?? info?.id ?? info?.product?.id ?? 0, 10
    ) || 0;
  }
  function getPrice(info) {
    const v = [info?.price, info?.list_price, info?.website_price, info?.price_reduce,
               info?.price_with_tax, info?.price_without_discount]
              .find(x => typeof x === 'number');
    return (typeof v === 'number') ? v : null;
  }
  function getStock(info) {
    const v = [info?.stock_quantity, info?.virtual_available, info?.qty_available,
               info?.free_qty, info?.available_quantity, info?.stock, info?.stock_qty]
              .find(x => typeof x === 'number');
    if (typeof v === 'number') return v;
    if (info?.is_out_of_stock === true) return 0;
    return null;
  }
  function fmtPrice(v) {
    try {
      const lang = document.documentElement.lang || 'es-ES';
      const curr = $('[data-website-currency-code]')?.dataset.websiteCurrencyCode || 'EUR';
      return new Intl.NumberFormat(lang, { style:'currency', currency:curr }).format(v);
    } catch { return (Math.round(v * 100) / 100).toFixed(2); }
  }

  /* ---------------- UI ---------------- */
  async function buildMatrix() {
    const root = getRoot();
    const blocks = getBlocks(root);
    if (!blocks.length) return;
    const { color, size } = pickColorSize(blocks);
    if (!color || !size) return;

    const anchor = placeAnchor();
    anchor.innerHTML = '';

    const wrap  = document.createElement('div'); wrap.className = 'sp-matrix';
    const table = document.createElement('table'); table.className = 'sp-matrix__table';

    const thead = document.createElement('thead');
    const trh   = document.createElement('tr');
    trh.innerHTML = `<th class="sp-sticky-left">Color</th>`;
    size.options.forEach(s => { const th=document.createElement('th'); th.textContent = s.name; trh.appendChild(th); });
    thead.appendChild(trh);

    // Ancho mínimo dinámico según nº de tallas
    const cols = size.options.length;
    if (cols >= 10)      table.style.minWidth = '1340px';
    else if (cols >= 8)  table.style.minWidth = '1160px';
    else if (cols >= 6)  table.style.minWidth = '980px';
    else                 table.style.minWidth = 'auto';

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
            <input class="sp-qty" type="number" min="0" step="1">
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

    await hydrate(wrap, root);
    btn.addEventListener('click', () => addAllToCart(wrap));
  }

  async function hydrate(container, root) {
    const cells = Array.from(container.querySelectorAll('td'));
    const queue = cells.slice();
    async function worker() {
      while (queue.length) {
        const td = queue.shift();
        const colorPtav = parseInt(td.closest('tr')?.dataset.colorPtav || td.closest('tr')?.dataset.colorId || '0', 10);
        const sizePtav  = parseInt(td.dataset.sizePtav || td.dataset.sizeId || '0', 10);
        const combo = sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav];

        let info = null;
        try {
          info = await getCombo(combo, root);
        } catch (e) { warn('combo error', e.message); }
        if (!info) { td.classList.add('sp-unavailable'); continue; }

        const variantId = getVariantId(info);
        if (variantId) td.querySelector('.sp-qty').dataset.variantId = String(variantId);

        const price = getPrice(info);
        if (price != null) td.querySelector('.sp-price').textContent = fmtPrice(price);

        const stock = getStock(info);
        if (stock != null) td.querySelector('.sp-stock').textContent = `Stock: ${stock}`;

        const img = td.closest('tr').querySelector('.sp-color__img');
        if (img && !img.src) {
          img.src = `/web/image/product.product/${variantId || 0}/image_256`;
          img.onerror = () => { img.src = `/web/image/product.template/${readCtx(root).tmplId}/image_256`; };
        }

        if (!variantId && price == null && stock == null) td.classList.add('sp-unavailable');
      }
    }
    await Promise.all(new Array(6).fill(0).map(worker));
  }

  /* ---------------- carrito (hiper-robusto) ---------------- */

  function getCsrf() {
    return (
      document.querySelector('meta[name="csrf-token"]')?.content ||
      (window.odoo && window.odoo.csrf_token) ||
      document.querySelector('input[name="csrf_token"]')?.value ||
      ''
    );
  }

  async function cartUpdateJSON(url, payload) {
    const r = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRF-Token': payload.csrf_token || ''
      },
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    try {
      const data = await r.json();
      if (data && data.error) throw new Error('JSON error');
    } catch (_) {}
    return true;
  }

  async function cartUpdateForm(url, payload) {
    const fd = new FormData();
    Object.entries(payload).forEach(([k,v]) => {
      if (v === undefined || v === null) return;
      if (Array.isArray(v)) v.forEach(val => fd.append(k, String(val)));
      else fd.append(k, String(v));
    });
    const r = await fetch(url, { method: 'POST', credentials: 'same-origin', body: fd });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return true;
  }

  async function ensureVariantIdFromCell(inp, root) {
    let vid = parseInt(inp.dataset.variantId || '0', 10);
    if (vid) return vid;
    const td = inp.closest('td');
    const tr = inp.closest('tr');
    const sizePtav  = parseInt(td?.dataset.sizePtav || td?.dataset.sizeId || '0', 10);
    const colorPtav = parseInt(tr?.dataset.colorPtav || tr?.dataset.colorId || '0', 10);
    const combo = (sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav]).filter(n => n > 0);
    const info = await getCombo(combo, root);
    vid = getVariantId(info || {});
    return vid || 0;
  }

  function addAllToCart(container) {
    const inputs = container.querySelectorAll('.sp-qty');
    const root   = getRoot();
    const ctx    = readCtx(root);
    const csrf   = getCsrf();

    (async () => {
      let any = false;

      for (const inp of inputs) {
        const qty = parseFloat(inp.value || '0');
        if (!(qty > 0)) continue;

        // asegura variant_id
        const variantId = await ensureVariantIdFromCell(inp, root);
        if (!variantId) { warn('sin variantId para celda', inp); continue; }
        any = true;

        // reconstruye combinación por si el endpoint la exige
        const td = inp.closest('td');
        const tr = inp.closest('tr');
        const sizePtav  = parseInt(td?.dataset.sizePtav || td?.dataset.sizeId || '0', 10);
        const colorPtav = parseInt(tr?.dataset.colorPtav || tr?.dataset.colorId || '0', 10);
        const combination = (sizePtav > 0 ? [colorPtav, sizePtav] : [colorPtav]).filter(n => n > 0);

        const payload = {
          product_id: variantId,
          add_qty: qty,
          set_qty: undefined,                   // algunos módulos usan set_qty; lo dejamos undefined
          product_template_id: ctx.tmplId || undefined,
          combination,
          no_variant_attribute_values: [],
          product_custom_attribute_values: [],
          display: false,
          express: false,
          csrf_token: csrf || undefined,
        };

        let ok = false;

        // 1) JSON
        for (const u of ['/shop/cart/update_json', '/website_sale/cart/update_json']) {
          try { await cartUpdateJSON(u, payload); log('añadido JSON', u, payload); ok = true; break; }
          catch (e) { warn('fallo JSON', u, e.message); }
        }

        // 2) FORM (añadimos también set_qty como respaldo)
        if (!ok) {
          const formPayload = { ...payload, set_qty: undefined };
          for (const u of ['/shop/cart/update', '/website_sale/cart/update']) {
            try { await cartUpdateForm(u, formPayload); log('añadido FORM', u, formPayload); ok = true; break; }
            catch (e) { warn('fallo FORM', u, e.message); }
          }
        }

        // 3) GET (mínimo imprescindible)
        if (!ok) {
          const qs = new URLSearchParams({
            product_id: String(payload.product_id),
            add_qty: String(payload.add_qty),
            express: 'false',
          });
          if (csrf) qs.set('csrf_token', csrf);
          if (ctx.tmplId) qs.set('product_template_id', String(ctx.tmplId));
          const url = '/shop/cart/update?' + qs.toString();
          try {
            const r = await fetch(url, { method: 'GET', credentials: 'same-origin', redirect: 'follow' });
            if (!r.ok) throw new Error(`HTTP ${r.status}`);
            log('añadido GET', url);
            ok = true;
          } catch (e) { warn('fallo GET', e.message); }
        }

        if (!ok) warn('NO se pudo añadir', payload);
      }

      if (any) window.location.reload();
    })();
  }

  /* ---------------- boot ---------------- */
  function start(){ if ($('.o_wsale_product_page')) buildMatrix(); }
  (document.readyState === 'loading')
    ? document.addEventListener('DOMContentLoaded', start)
    : start();
})();