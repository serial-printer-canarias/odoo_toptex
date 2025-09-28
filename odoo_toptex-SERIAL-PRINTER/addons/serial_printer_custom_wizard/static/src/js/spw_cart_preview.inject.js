/** SPW – Cart preview: foto + píldora + texto por personalización (no repite) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  /* -------------------- helpers -------------------- */
  const onReady = (cb) => {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', cb, { once: true });
    else cb();
  };

  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  const ts = () => Date.now();

  function getLineId(lineEl) {
    const c = lineEl.getAttribute('data-line-id') ? lineEl :
      lineEl.querySelector('[data-line-id]') ||
      lineEl.querySelector('input[name="line_id"]') ||
      lineEl.querySelector('button[data-line-id], a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || null;
  }

  /** Divide el name en bloques: — Personalización N — ... (hasta la siguiente) */
  function parseBlocks(text) {
    if (!text) return [];
    const blocks = [];
    const re = /—\s*Personalización\s*(\d+)\s*—([\s\S]*?)(?=(?:—\s*Personalización\s*\d+\s*—)|$)/gi;
    let m;
    while ((m = re.exec(text))) {
      const seq = parseInt(m[1], 10) || blocks.length + 1;
      const body = (m[2] || '').trim();

      const tech  = (body.match(/T[ée]cnica\s*:\s*(.+)/i)?.[1] || '').trim();
      const color = (body.match(/Color\s*SVG\s*:\s*(#[0-9a-fA-F]{3,8})/i)?.[1] || '').trim();
      const notes = (body.match(/Obs(?:ervaciones)?\s*:\s*([\s\S]+)/i)?.[1] || '').trim();

      blocks.push({ seq, tech, color, notes });
    }
    // si no encontró bloques formales, intenta un único bloque color/obs sueltos
    if (!blocks.length) {
      const color = (text.match(/Color\s*SVG\s*:\s*(#[0-9a-fA-F]{3,8})/i)?.[1] || '').trim();
      const tech  = (text.match(/T[ée]cnica\s*:\s*(.+)/i)?.[1] || '').trim();
      const notes = (text.match(/Obs(?:ervaciones)?\s*:\s*([\s\S]+)/i)?.[1] || '').trim();
      if (color || tech || notes) blocks.push({ seq: 1, color, tech, notes });
    }
    // orden por seq
    blocks.sort((a, b) => a.seq - b.seq);
    return blocks;
  }

  function ensureWrap(info) {
    let wrap = info.querySelector('.spw-cart-preview');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-top:8px';
      info.appendChild(wrap);
    } else {
      wrap.innerHTML = '';
    }
    return wrap;
  }

  function renderBlock(wrap, lineId, blk) {
    const row = document.createElement('div');
    row.className = 'spw-item';
    row.style.cssText = 'display:flex;gap:10px;align-items:flex-start';

    // imagen por índice fijo (no fallback → no repite)
    const img = new Image();
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.style.cssText = 'width:120px;max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
    img.src = `/spw/line_preview/${lineId}-${blk.seq}.png?v=${ts()}`;
    img.onerror = () => { img.style.display = 'none'; }; // si no hay PNG, queda solo el texto

    // meta (píldora + textos)
    const meta = document.createElement('div');
    meta.style.cssText = 'display:flex;flex-direction:column;gap:6px;line-height:1.15';

    // píldora + código
    if (blk.color) {
      const pillRow = document.createElement('div');
      pillRow.style.cssText = 'display:flex;gap:8px;align-items:center';

      const pill = document.createElement('span');
      pill.title = blk.color;
      pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #d1d5db;display:inline-block';
      pill.style.background = blk.color;

      const code = document.createElement('span');
      code.textContent = blk.color;
      code.style.cssText = 'font-size:12px;color:#6b7280';

      pillRow.appendChild(pill);
      pillRow.appendChild(code);
      meta.appendChild(pillRow);
    }

    // técnica
    if (blk.tech) {
      const t = document.createElement('div');
      t.textContent = `Técnica: ${blk.tech}`;
      t.style.cssText = 'font-size:12px;color:#111827';
      meta.appendChild(t);
    }

    // observaciones
    if (blk.notes) {
      const n = document.createElement('div');
      n.textContent = `Obs: ${blk.notes}`;
      n.style.cssText = 'font-size:12px;color:#374151;white-space:pre-wrap';
      meta.appendChild(n);
    }

    row.appendChild(img);
    row.appendChild(meta);
    wrap.appendChild(row);
  }

  function renderLine(lineEl) {
    const info = lineEl.querySelector(INFO_SEL) || lineEl;
    if (!info) return;

    const lineId = getLineId(lineEl);
    if (!lineId) return;

    const nameText = (info.textContent || '').trim();
    const blocks = parseBlocks(nameText);
    if (!blocks.length) return;

    const wrap = ensureWrap(info);
    blocks.forEach(blk => renderBlock(wrap, lineId, blk));
  }

  function initialInject() {
    document.querySelectorAll(LINE_SEL).forEach(renderLine);
  }

  function observeMutations() {
    const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    new MutationObserver(ms => {
      for (const m of ms) {
        m.addedNodes && m.addedNodes.forEach(n => {
          if (n instanceof HTMLElement) {
            if (n.matches?.(LINE_SEL)) renderLine(n);
            else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
          }
        });
      }
    }).observe(root, { childList: true, subtree: true });
  }

  function boot() {
    if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    initialInject();
    observeMutations();
    console.log('[SPW] cart injector: multi-personalización con imagen, píldora y texto');
  }

  onReady(boot);
});