odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', ['web.dom_ready'], function (require) {
  'use strict';
  require('web.dom_ready');

  // ===== Utils mínimos y robustos =====
  function $(sel, root){ return (root||document).querySelector(sel); }
  function qa(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }
  function getParam(n){ try { return new URL(location.href).searchParams.get(n); } catch(_) { return null; } }

  function readHexFromText(line){
    const txt = (line.innerText || '').toUpperCase();
    const m = txt.match(/#([0-9A-F]{6})/);
    return m ? ('#' + m[1]) : null;
  }

  // Clave de línea: preferimos line_id; si no, product-id; si no, índice
  function buildLineKey(line, idx){
    const lid = line.getAttribute('data-line-id');
    if (lid) return 'L-'+lid;
    const pid = line.getAttribute('data-product-id');
    if (pid) return 'P-'+pid;
    return 'IDX-'+idx;
  }

  // Detecta líneas del carrito en distintos temas
  function findCartLines(){
    const sels = [
      'div.js_cart_line', 'tr.js_cart_line',
      '.o_wsale_cart_item', '.card.js_cart_item',
      '.js_cart_lines .row'   // fallback
    ];
    const nodes = [];
    sels.forEach(s => qa(s).forEach(n => { if (!nodes.includes(n)) nodes.push(n); }));
    return nodes;
  }

  function infoContainer(line){
    return line.querySelector(
      '.o_wsale_product_information, .o_wsale_cart_description, .media-body, .oe_cart_summary, .o_wsale_product_name'
    ) || line;
  }

  function previewUrlByLineId(line){
    // Si el DOM tiene data-line-id, usamos PNG por línea
    const lid = line.getAttribute('data-line-id');
    if (lid) return '/spw/line_preview/' + encodeURIComponent(lid) + '.png?_=' + Date.now();

    // Si venimos del configurador, usamos la última PNG guardada
    try {
      const wanted = getParam('spw_line_id');
      const lastId = sessionStorage.getItem('spw_last_line_id');
      const lastPng = sessionStorage.getItem('spw_last_png');
      if (wanted && lastId && wanted === lastId && lastPng) return lastPng;
    } catch(_){}
    return null;
  }

  // ===== Render =====
  function ensureBlock(line, key){
    // Evita duplicados: si ya existe, devuélvelo
    let block = line.querySelector('.spw-preview-block');
    if (block) return block;

    block = document.createElement('div');
    block.className = 'spw-preview-block';
    block.dataset.spwKey = key;
    block.style.marginTop = '6px';
    block.style.display = 'flex';
    block.style.alignItems = 'center';
    block.style.gap = '8px';
    block.style.flexWrap = 'wrap';

    // Imagen
    const img = new Image();
    img.className = 'spw-preview-img';
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.style.maxWidth = '120px';
    img.style.height = 'auto';
    img.style.border = '1px solid #e5e7eb';
    img.style.borderRadius = '6px';
    block.appendChild(img);

    // Píldora de color
    const pill = document.createElement('span');
    pill.className = 'spw-color-pill';
    pill.style.display = 'none';
    pill.style.width = '16px';
    pill.style.height = '16px';
    pill.style.borderRadius = '999px';
    pill.style.border = '1px solid #e5e7eb';
    block.appendChild(pill);

    // Insertar justo bajo la descripción
    const info = infoContainer(line);
    const anchor = info.querySelector('p:last-of-type') || info;
    anchor.insertAdjacentElement('afterend', block);

    return block;
  }

  function fillBlock(block, line){
    const img  = block.querySelector('.spw-preview-img');
    const pill = block.querySelector('.spw-color-pill');

    // Fuente de la miniatura
    let src = previewUrlByLineId(line);
    if (!src) {
      // Último recurso: si hay color pero no PNG, mantenemos sin imagen
      img.removeAttribute('src');
    } else if (img.src !== src) {
      img.src = src;
    }

    // Color: 1) sessionStorage del configurador 2) texto de la línea
    let hex = null;
    try {
      const wanted   = getParam('spw_line_id');
      const lastId   = sessionStorage.getItem('spw_last_line_id');
      const lastHex  = sessionStorage.getItem('spw_last_color');
      if (wanted && lastId && wanted === lastId && /^#[0-9A-F]{6}$/i.test(lastHex)) hex = lastHex;
    } catch(_){}

    if (!hex) hex = readHexFromText(line);

    if (hex && /^#[0-9A-F]{6}$/i.test(hex)){
      pill.style.display = 'inline-block';
      pill.style.background = hex;
      pill.title = hex;
    } else {
      pill.style.display = 'none';
    }
  }

  function injectAll(){
    if (!/\/shop\/cart/.test(location.pathname)) return;

    const lines = findCartLines();
    lines.forEach((line, idx) => {
      // Marca de seguridad para no re-crear
      if (line.dataset.spwApplied === '1') {
        const block = line.querySelector('.spw-preview-block');
        if (block) fillBlock(block, line);
        return;
      }

      const key = buildLineKey(line, idx);
      const block = ensureBlock(line, key);
      fillBlock(block, line);
      line.dataset.spwApplied = '1';
    });

    // Limpia el "último" después de usarlo
    try {
      const wanted = getParam('spw_line_id');
      const lastId = sessionStorage.getItem('spw_last_line_id');
      if (wanted && lastId && wanted === lastId){
        sessionStorage.removeItem('spw_last_line_id');
        sessionStorage.removeItem('spw_last_png');
        sessionStorage.removeItem('spw_last_color');
      }
    } catch(_){}
  }

  // ===== Boot =====
  try { console.debug('[SPW] cart inject loaded'); } catch(_){}
  injectAll();

  // Reinyecta si Odoo/OWL re-renderiza
  const root = $('.js_cart_lines') || $('.o_wsale_cart') || document.body;
  if (window.MutationObserver && root){
    const mo = new MutationObserver(() => { window.requestAnimationFrame(injectAll); });
    mo.observe(root, { childList:true, subtree:true });
  }
});