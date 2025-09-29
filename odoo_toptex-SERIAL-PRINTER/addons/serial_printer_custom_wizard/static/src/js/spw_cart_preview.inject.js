/** SPW – Cart preview: una tarjeta por personalización (foto + píldora + texto) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // ===== util =====
  const ready = (cb) => (document.readyState === 'loading'
    ? document.addEventListener('DOMContentLoaded', cb, { once: true })
    : cb());

  const LINE_SEL = '.o_cart_product, .o_wsale_cart_item, .js_cart_lines tr, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  const exts = ['png','webp','jpg','jpeg'];
  const ts = () => Date.now();

  function getLineId(el) {
    const c = el.getAttribute('data-line-id') ? el :
      el.querySelector('[data-line-id]') ||
      el.querySelector('input[name="line_id"]') ||
      el.querySelector('button[data-line-id], a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || null;
  }

  // Extrae bloques: “— Personalización N — …”
  function parseBlocks(text) {
    const out = [];
    const src = (text || '').replace(/\r/g, '');
    const re = /—\s*Personalización\s*(\d+)\s*—([\s\S]*?)(?=—\s*Personalización\s*\d+\s*—|$)/g;
    let m;
    while ((m = re.exec(src))) {
      const idx = parseInt(m[1], 10);
      const body = (m[2] || '').trim();
      const lines = body.split('\n').map(s => s.trim()).filter(Boolean);
      const hexm = body.match(/#([0-9a-fA-F]{3,8})/);
      const hex = hexm ? ('#' + hexm[1]) : null;
      out.push({ idx, lines, hex });
    }
    // si no hay bloques, intenta antiguo: 1 solo con color suelto
    if (!out.length) {
      const hexm = src.match(/#([0-9a-fA-F]{3,8})/);
      out.push({ idx: 1, lines: src.split('\n').map(s=>s.trim()).filter(Boolean), hex: hexm ? ('#'+hexm[1]) : null });
    }
    // ordena por idx
    out.sort((a,b)=>a.idx-b.idx);
    return out;
  }

  function buildCandidates(lineId, idx) {
    const n = idx;
    const base = `/spw/line_preview/${lineId}`;
    const cands = [];
    // patrón con guion (nuestro endpoint)
    for (const ext of exts) cands.push(`${base}-${n}.${ext}?v=${ts()}`);
    // compat alternos
    for (const ext of exts) {
      cands.push(`${base}_${n}.${ext}?v=${ts()}`);
      cands.push(`${base}/${n}.${ext}?v=${ts()}`);
    }
    // último recurso: sin extensión
    cands.push(`${base}-${n}.png?v=${ts()}`);
    return [...new Set(cands)];
  }

  function ensureMount(info) {
    let wrap = info.querySelector('.spw-cart-preview');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start;margin-top:8px';
      info.appendChild(wrap);
    } else {
      wrap.innerHTML = '';
    }
    return wrap;
  }

  function loadFirst(img, urls) {
    let i = 0;
    function next(){ if (i >= urls.length) { img.remove(); return; } img.onerror = next; img.src = urls[i++]; }
    next();
  }

  function renderLine(lineEl) {
    const info = lineEl.querySelector(INFO_SEL) || lineEl;
    if (!info) return;
    const lineId = getLineId(lineEl);
    if (!lineId) return;

    const text = (info.textContent || '').trim();
    const blocks = parseBlocks(text);
    const mount = ensureMount(info);

    // una tarjeta por bloque
    blocks.forEach(({idx, lines, hex}) => {
      const card = document.createElement('div');
      card.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px;min-width:140px;max-width:160px';

      // figura
      const fig = document.createElement('figure');
      fig.style.cssText = 'margin:0;display:flex;flex-direction:column;align-items:center;gap:6px';

      // imagen
      const img = new Image();
      img.alt = `Personalización ${idx}`;
      img.loading = 'lazy';
      img.style.cssText = 'width:140px;height:auto;border:1px solid #e5e7eb;border-radius:8px;background:#fff';
      fig.appendChild(img);

      // caption: píldora + texto (líneas)
      const cap = document.createElement('figcaption');
      cap.style.cssText = 'font-size:12px;line-height:1.15;text-align:left;width:100%';

      const row = document.createElement('div');
      row.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:4px';
      if (hex) {
        const dot = document.createElement('span');
        dot.title = hex;
        dot.style.cssText = `width:12px;height:12px;border-radius:9999px;border:1px solid #e5e7eb;background:${hex}`;
        row.appendChild(dot);
        const code = document.createElement('span');
        code.textContent = hex;
        row.appendChild(code);
      }
      cap.appendChild(row);

      lines.forEach(s => {
        if (!s) return;
        const p = document.createElement('div');
        p.textContent = s;
        cap.appendChild(p);
      });

      fig.appendChild(cap);
      card.appendChild(fig);
      mount.appendChild(card);

      // carga imagen correspondiente a ese índice
      loadFirst(img, buildCandidates(lineId, idx));
    });
  }

  function run() {
    const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    const applyAll = () => root.querySelectorAll(LINE_SEL).forEach(renderLine);
    applyAll();
    new MutationObserver((ms)=>{
      for (const m of ms) m.addedNodes?.forEach(n=>{
        if (!(n instanceof HTMLElement)) return;
        if (n.matches?.(LINE_SEL)) renderLine(n);
        else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
      });
    }).observe(root, { childList:true, subtree:true });
    console.log('[SPW] cart preview listo (multi-foto + texto por personalización)');
  }

  ready(()=> {
    if (document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) run();
  });
});