/** SPW – Cart preview (vertical, multi-personalización) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // ---------- ready ----------
  function onReady(cb){ document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }

  // ---------- selectores ----------
  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  // ---------- paleta (HEX -> nombre) ----------
  const PALETTE = [
    ['#FFFFFF','Blanco'],['#F7F5E8','Hueso pastel'],['#FFF2CC','Crema'],
    ['#FFF5A6','Amarillo suave'],['#F7D3B8','Melocotón'],['#FADDE4','Rosa pastel'],
    ['#E9D5FF','Lila'],['#EDE9FE','Lavanda'],['#93C5FD','Azul cielo'],
    ['#60A5FA','Azul medio'],['#7DD3FC','Turquesa'],['#20C3E8','Cian'],
    ['#A7F3D0','Menta'],['#C7EFCF','Verde pastel'],['#34D399','Verde medio'],
    ['#A3E635','Lima'],['#EAB308','Mostaza'],['#FB923C','Naranja'],
    ['#FB7185','Coral'],['#EF4444','Rojo'],['#991B1B','Granate'],
    ['#8B5E34','Marrón'],['#A8A29E','Topo'],['#E5E7EB','Gris claro'],
    ['#9CA3AF','Gris medio'],['#4B5563','Gris oscuro'],['#1E3A8A','Azul marino'],
    ['#172554','Azul noche'],['#000000','Negro'],
  ];
  const HEX2NAME = Object.fromEntries(PALETTE.map(([h,n]) => [h.toUpperCase(), n]));
  const colorName = hex => HEX2NAME[(hex||'').toUpperCase()] || null;

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

  function card(item){
    const root = document.createElement('div');
    root.className = 'spw-one';
    root.style.cssText = 'display:flex;flex-direction:column;gap:6px;align-items:flex-start;border:1px solid #e5e7eb;border-radius:10px;padding:8px;max-width:220px;background:#fff';

    const img = new Image();
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.decoding = 'async';
    img.src = item.img;
    img.style.cssText = 'width:100%;height:auto;border-radius:8px;object-fit:contain;background:#fff';
    root.appendChild(img);

    const row = document.createElement('div');
    row.style.cssText = 'display:flex;align-items:center;gap:8px';
    const pill = document.createElement('span');
    pill.title = item.color || '';
    pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
    if(item.color) pill.style.background = item.color;
    row.appendChild(pill);

    const label = document.createElement('span');
    const name = item.color ? colorName(item.color) : null;
    label.textContent = item.color ? (name ? `${name} · ${item.color}` : item.color) : '';
    label.style.cssText = 'font-size:12px;color:#374151';
    row.appendChild(label);
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
      // console.warn('[SPW] fallo al obtener personalizaciones', e);
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

  // --- Ocultar paleta si apareciera en el carrito (sin tocar el customizer) ---
  function hidePaletteInCart(){
    const cart = document.querySelector('#o_cart, .o_wsale_cart_summary');
    if(!cart) return;
    const css = `
      #o_cart .spw-color-palette,
      #o_cart .spw_color_palette,
      #o_cart .spw-colors,
      #o_cart .spw_colors,
      #o_cart .spw-palette,
      #o_cart .spw_palette { display:none !important; }`;
    const tag = document.createElement('style');
    tag.setAttribute('data-spw','hide-palette-cart');
    tag.textContent = css;
    document.head.appendChild(tag);
    cart.querySelectorAll('.spw-color-palette, .spw_color_palette, .spw-colors, .spw_colors, .spw-palette, .spw_palette')
        .forEach(el => el.style.display = 'none');
  }

  function boot(){
    if(!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    hidePaletteInCart();   // << sólo este añadido
    scanInitial();
    observe();
    // console.log('[SPW] cart preview vertical listo');
  }

  onReady(boot);
});