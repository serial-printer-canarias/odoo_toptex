/** SPW – Cart preview (vertical, multi-personalización) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // ---------- ready ----------
  function onReady(cb){ document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }

  // ---------- selectores ----------
  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  // ---------- utils ----------
  function urlLineIdFrom(el){
    if(!el) return null;
    const c = el.getAttribute?.('data-line-id') ? el :
      el.querySelector?.('[data-line-id]') ||
      el.querySelector?.('input[name="line_id"]') ||
      el.querySelector?.('button[data-line-id], a[data-line-id]');
    return c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value);
  }

  function ensureWrap(info){
    let wrap = info.querySelector('.spw-cart-preview');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      // vertical
      wrap.style.cssText = 'display:flex;flex-direction:column;gap:12px;margin-top:8px';
      info.appendChild(wrap);
    }
    return wrap;
  }

  function injectHidingCSS(){
    // Oculta paletas/botones antiguos en carrito y (si aparecieran) en customizer
    const css = `
      #o_cart .spw-color-palette,
      .o_wsale_cart_page .spw-color-palette,
      #o_cart [data-spw-role="color-palette"],
      .o_wsale_cart_page [data-spw-role="color-palette"],
      #o_cart .spw-quick-swatches { display:none !important; }
      .spw_customize_page .spw-quick-swatches { display:none !important; }
      .spw-one .spw-color-name{ padding-left:2px; }
    `;
    if (!document.getElementById('spw-hide-palette-style')) {
      const st = document.createElement('style');
      st.id = 'spw-hide-palette-style';
      st.type = 'text/css';
      st.appendChild(document.createTextNode(css));
      document.head.appendChild(st);
    }
  }

  function card(item){
    const root = document.createElement('div');
    root.className = 'spw-one';
    root.style.cssText = 'display:flex;flex-direction:column;gap:6px;align-items:flex-start;border:1px solid #e5e7eb;border-radius:10px;padding:8px;max-width:220px';

    const img = new Image();
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.src = item.img;
    img.style.cssText = 'width:100%;height:auto;border-radius:8px;object-fit:contain;background:#fff';
    root.appendChild(img);

    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px;flex-wrap:wrap';

    const pill = document.createElement('span');
    pill.title = item.color || '';
    pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
    if(item.color) pill.style.background = item.color;
    row.appendChild(pill);

    const hex = document.createElement('span');
    hex.textContent = item.color || '';
    hex.style.cssText = 'font-size:12px;color:#374151';
    row.appendChild(hex);

    if (item.color_name && item.color_name !== item.color) {
      const name = document.createElement('span');
      name.className = 'spw-color-name';
      name.textContent = `· ${item.color_name}`;
      name.style.cssText = 'font-size:12px;color:#6b7280';
      row.appendChild(name);
    }
    root.appendChild(row);

    const t1 = document.createElement('div');
    t1.textContent = (item.tech ? `Técnica: ${item.tech}` : '');
    t1.style.cssText = 'font-size:12px;color:#374151';
    if(item.tech) root.appendChild(t1);

    const t2 = document.createElement('div');
    t2.textContent = (item.color ? `Color SVG: ${item.color}` : '');
    t2.style.cssText = 'font-size:12px;color:#374151';
    if(item.color) root.appendChild(t2);

    return root;
  }

  async function renderLine(lineEl){
    const info = lineEl.querySelector?.(INFO_SEL) || lineEl;
    const lineId = urlLineIdFrom(lineEl);
    if(!info || !lineId) return;

    const wrap = ensureWrap(info);
    wrap.innerHTML = ''; // limpiar

    try{
      const res = await fetch(`/spw/line_personalizations/${lineId}`);
      const json = await res.json();
      const items = (json && json.ok && Array.isArray(json.items)) ? json.items : [];
      if(!items.length) return;

      // apilar vertical
      items.forEach(it => wrap.appendChild(card(it)));
    }catch(e){
      // silencioso
    }
  }

  function scanInitial(){ document.querySelectorAll(LINE_SEL).forEach(renderLine); }
  function observe(){
    const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    new MutationObserver(ms => {
      for(const m of ms){
        m.addedNodes && m.addedNodes.forEach(n => {
          if(n instanceof HTMLElement){
            if(n.matches?.(LINE_SEL)) renderLine(n);
            else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
          }
        });
      }
    }).observe(root, {childList:true, subtree:true});
  }

  function boot(){
    injectHidingCSS(); // <- oculta paleta en carrito y botones antiguos
    if(!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    scanInitial();
    observe();
  }

  onReady(boot);
});