odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', ['web.dom_ready'], function (require) {
  'use strict';
  require('web.dom_ready');

  // ------------ utils ------------
  function $(sel, root){ return (root||document).querySelector(sel); }
  function qa(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }
  function getParam(name){
    try { return new URL(window.location.href).searchParams.get(name); } catch(_) { return null; }
  }

  function getLineId(line){
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
    // Cubrimos distintos layouts: tu tema usa div.js_cart_line
    const sels = [
      'div.js_cart_line', 'tr.js_cart_line',
      '.o_wsale_cart_item', '.card.js_cart_item',
      '.js_cart_lines .row'
    ];
    const nodes = [];
    sels.forEach(s => qa(s).forEach(n => { if (!nodes.includes(n)) nodes.push(n); }));
    return nodes;
  }

  function infoContainer(line){
    return line.querySelector('.o_wsale_product_information, .o_wsale_cart_description, .media-body, .oe_cart_summary, .o_wsale_product_name') || line;
  }

  function previewUrl(id){
    return '/spw/line_preview/' + encodeURIComponent(id) + '.png?_=' + Date.now();
  }

  function readHexFromText(line){
    const txt = (line.innerText || '').toUpperCase();
    const m = txt.match(/#([0-9A-F]{6})/);
    return m ? ('#' + m[1]) : null;
  }

  // ------------ render ------------
  function ensureBlock(line, id){
    let block = line.querySelector('.spw-preview-block[data-line-id="' + id + '"]');
    if (block) return block;

    block = document.createElement('div');
    block.className = 'spw-preview-block';
    block.dataset.lineId = id;
    block.style.marginTop = '6px';
    block.style.display = 'flex';
    block.style.alignItems = 'center';
    block.style.gap = '8px';

    const img = new Image();
    img.className = 'spw-preview-img';
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.style.maxWidth = '120px';
    img.style.height = 'auto';
    img.style.border = '1px solid #e5e7eb';
    img.style.borderRadius = '6px';
    block.appendChild(img);

    const pill = document.createElement('span');
    pill.className = 'spw-color-pill';
    pill.style.display = 'none';
    pill.style.width = '16px';
    pill.style.height = '16px';
    pill.style.borderRadius = '999px';
    pill.style.border = '1px solid #e5e7eb';
    block.appendChild(pill);

    const info = infoContainer(line);
    const anchor = info.querySelector('p:last-of-type') || info;
    anchor.insertAdjacentElement('afterend', block);
    return block;
  }

  function fillBlock(block, id, line){
    const img = block.querySelector('.spw-preview-img');
    const pill = block.querySelector('.spw-color-pill');

    const wanted = getParam('spw_line_id');
    let lastId=null, lastPng=null, lastColor=null;
    try {
      lastId    = sessionStorage.getItem('spw_last_line_id');
      lastPng   = sessionStorage.getItem('spw_last_png');
      lastColor = sessionStorage.getItem('spw_last_color');
    } catch(_){}

    const src = (wanted && lastId && wanted === lastId && lastPng) ? lastPng : previewUrl(id);
    if (img.src !== src) img.src = src;

    const hex = (lastColor && /^#[0-9A-F]{6}$/i.test(lastColor)) ? lastColor : readHexFromText(line);
    if (hex){
      pill.style.display = 'inline-block';
      pill.style.background = hex;
      pill.title = hex;
    } else {
      pill.style.display = 'none';
    }
  }

  function injectAll(){
    if (!/\/shop\/cart/.test(location.pathname)) return;

    findCartLines().forEach((line) => {
      const id = getLineId(line);
      if (!id) return;
      const block = ensureBlock(line, id);   // crea una sola vez
      fillBlock(block, id, line);            // y solo actualiza contenido
    });

    // Limpiar sesión tras usar la última previa
    const wanted = getParam('spw_line_id');
    try {
      const lastId = sessionStorage.getItem('spw_last_line_id');
      if (wanted && lastId && wanted === lastId){
        sessionStorage.removeItem('spw_last_line_id');
        sessionStorage.removeItem('spw_last_png');
        sessionStorage.removeItem('spw_last_color');
      }
    } catch(_){}
  }

  // ------------ boot ------------
  injectAll();
  if (window.MutationObserver){
    const root = $('.js_cart_lines') || $('.o_wsale_cart') || document.body;
    const mo = new MutationObserver(function(){ window.requestAnimationFrame(injectAll); });
    mo.observe(root, { childList:true, subtree:true });
  }
});