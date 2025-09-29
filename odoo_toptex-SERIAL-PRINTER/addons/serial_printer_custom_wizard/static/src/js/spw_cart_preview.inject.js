/** SPW – Cart preview (imagen + píldora + texto) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  function ready(cb){ document.readyState==='loading' ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }
  const ts = () => Date.now();

  function getLineId(lineEl){
    const c = lineEl.getAttribute('data-line-id') ? lineEl :
      lineEl.querySelector('[data-line-id]') ||
      lineEl.querySelector('input[name="line_id"]') ||
      lineEl.querySelector('button[data-line-id], a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || null;
  }

  // Lee "Técnica:", "Color SVG:", "Observaciones:" del texto de la línea
  function parseMeta(text){
    const meta = { tech:null, color:null, notes:null };
    if (!text) return meta;
    const t = text.replace(/\s+/g,' ').trim();
    const mTech = t.match(/Técnica:\s*([^|#\n]+)/i);
    const mCol  = t.match(/Color\s*SVG:\s*(#[0-9a-f]{3,8})/i);
    const mNote = t.match(/Observaciones:\s*([^|#\n]+)/i);
    meta.tech = mTech ? mTech[1].trim() : null;
    meta.color = mCol ? mCol[1].trim() : null;
    meta.notes = mNote ? mNote[1].trim() : null;
    return meta;
  }

  function ensureBox(info){
    let box = info.querySelector('.spw-cart-box');
    if (!box){
      box = document.createElement('div');
      box.className = 'spw-cart-box';
      box.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;';
      const img = document.createElement('img');
      img.className = 'spw-cart-img';
      img.alt = 'Personalización';
      img.loading = 'lazy';
      img.style.cssText = 'width:120px;height:auto;border:1px solid #e5e7eb;border-radius:8px;background:#fff';
      const right = document.createElement('div');
      right.className = 'spw-meta';
      right.style.cssText = 'display:flex;flex-direction:column;gap:6px;font-size:14px;line-height:1.2';
      const pill = document.createElement('span');
      pill.className = 'spw-pill';
      pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block;margin-right:6px;vertical-align:middle';
      const metaText = document.createElement('div');
      metaText.className = 'spw-meta-text';
      right.appendChild(metaText);
      box.appendChild(img);
      box.appendChild(pill);
      box.appendChild(right);
      info.appendChild(box);
    }
    return box;
  }

  function renderLine(lineEl){
    const info = lineEl.querySelector(INFO_SEL) || lineEl;
    if (!info) return;
    const lineId = getLineId(lineEl);
    if (!lineId) return;

    const text = (info.textContent || '');
    const meta = parseMeta(text);
    const box = ensureBox(info);

    // imagen
    const img = box.querySelector('.spw-cart-img');
    img.src = `/spw/line_preview/${lineId}.png?v=${ts()}`;
    img.onerror = () => { img.style.opacity = '0'; }; // si no hay PNG, que no moleste

    // píldora
    const pill = box.querySelector('.spw-pill');
    pill.title = meta.color || '—';
    pill.style.background = meta.color || 'transparent';

    // texto
    const t = [];
    if (meta.color) t.push(`<b>${meta.color}</b>`);
    if (meta.tech)  t.push(`Técnica: ${meta.tech}`);
    if (meta.color) t.push(`Color SVG: ${meta.color}`);
    if (meta.notes) t.push(`Obs.: ${meta.notes}`);
    box.querySelector('.spw-meta-text').innerHTML = t.join('<br/>');
  }

  function boot(){
    const root = document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    if (!root) return;
    root.querySelectorAll(LINE_SEL).forEach(renderLine);
    new MutationObserver(ms => {
      for (const m of ms){
        m.addedNodes && m.addedNodes.forEach(n => {
          if (n instanceof HTMLElement){
            if (n.matches?.(LINE_SEL)) renderLine(n);
            else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
          }
        });
      }
    }).observe(root, { childList:true, subtree:true });
  }

  ready(boot);
});