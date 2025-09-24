odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', function (require) {
  'use strict';
  require('web.dom_ready');

  function $(sel, root){ return (root||document).querySelector(sel); }
  function qa(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }

  function getParam(name){
    try { return new URL(window.location.href).searchParams.get(name); }
    catch(_) { return null; }
  }

  function parseLineId(line){
    if (!line) return null;
    if (line.getAttribute('data-line-id')) return line.getAttribute('data-line-id');

    const inp = line.querySelector('input[name="line_id"]');
    if (inp && inp.value) return inp.value;

    const anchor = line.querySelector('a[href*="line_id="]') || line.querySelector('form[action*="line_id="]');
    if (anchor){
      try {
        const href = anchor.href || anchor.action;
        const u = new URL(href, location.origin);
        return u.searchParams.get('line_id');
      } catch(_){}
    }
    return null;
  }

  function findCartLines(){
    // Soporta varias plantillas de Odoo / temas
    const lines = qa('.js_cart_lines .o_wsale_cart_item, tr.js_cart_line, .o_wsale_cart_item, .card.js_cart_item');
    return lines.length ? lines : qa('.js_cart_lines .row');
  }

  function pickInfoContainer(line){
    return line.querySelector('.o_wsale_product_information, .o_wsale_cart_description, .media-body, .oe_cart_summary, .o_wsale_product_name')
           || line;
  }

  function parseHexFromText(el){
    if (!el) return null;
    const txt = el.innerText || '';
    const m = txt.match(/#([0-9a-f]{6})/i);
    return m ? ('#' + m[1].toUpperCase()) : null;
  }

  function previewUrl(lineId){
    return '/spw/line_preview/' + encodeURIComponent(lineId) + '.png?_=' + Date.now();
  }

  function insertForLine(line){
    const id = parseLineId(line);
    if (!id) return;

    // Evitar duplicados en esa línea
    qa('.spw-preview-block', line).forEach((n) => { if (n.dataset.lineId === id) n.remove(); });

    // Preferir el PNG recién generado si venimos de añadir al carrito
    const wanted = getParam('spw_line_id');
    let lastId=null, lastPng=null, lastColor=null;
    try{
      lastId   = sessionStorage.getItem('spw_last_line_id') || null;
      lastPng  = sessionStorage.getItem('spw_last_png') || null;
      lastColor= sessionStorage.getItem('spw_last_color') || null;
    }catch(_){}

    const src = (wanted && lastId && wanted === lastId && lastPng) ? lastPng : previewUrl(id);
    const hex = lastColor || parseHexFromText(line);

    const wrap = document.createElement('div');
    wrap.className = 'spw-preview-block';
    wrap.dataset.lineId = id;
    wrap.style.marginTop = '6px';
    wrap.style.display = 'flex';
    wrap.style.alignItems = 'center';
    wrap.style.gap = '8px';

    const img = new Image();
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.src = src;
    img.style.maxWidth = '120px';
    img.style.height = 'auto';
    img.style.border = '1px solid #e5e7eb';
    img.style.borderRadius = '6px';
    wrap.appendChild(img);

    // Píldora de color, si hay HEX
    if (hex && /^#[0-9A-F]{6}$/i.test(hex)){
      const pill = document.createElement('span');
      pill.title = hex;
      pill.style.display = 'inline-block';
      pill.style.width = '16px';
      pill.style.height = '16px';
      pill.style.borderRadius = '999px';
      pill.style.border = '1px solid #e5e7eb';
      pill.style.background = hex;
      wrap.appendChild(pill);
    }

    // Colocar justo debajo del texto descriptivo del producto
    const info = pickInfoContainer(line);
    const after = info.querySelector('p:last-of-type') || info;
    after.insertAdjacentElement('afterend', wrap);
  }

  function injectAll(){
    if (!/\/shop\/cart/.test(location.pathname)) return;

    const lines = findCartLines();
    lines.forEach(insertForLine);

    // Limpiar los "last_*" tras usarlo 1 vez
    const wanted = getParam('spw_line_id');
    try{
      const lastId = sessionStorage.getItem('spw_last_line_id');
      if (wanted && lastId && wanted === lastId){
        sessionStorage.removeItem('spw_last_line_id');
        sessionStorage.removeItem('spw_last_png');
        sessionStorage.removeItem('spw_last_color');
      }
    }catch(_){}
  }

  // Arranque + observar cambios del carrito (ajax re-render)
  injectAll();
  if (window.MutationObserver){
    const root = $('.js_cart_lines') || $('.o_wsale_cart') || document.body;
    let t = null;
    new MutationObserver(function(){
      clearTimeout(t);
      t = setTimeout(injectAll, 120);
    }).observe(root, {childList:true, subtree:true});
  }
});