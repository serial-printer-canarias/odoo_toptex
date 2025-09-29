/** SPW – Cart preview (multi-foto + nombre y código de color debajo) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // ------------ ready ------------
  function onReady(cb){ if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',cb,{once:true});} else cb(); }

  // ------------ selectores ------------
  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  // ------------ paleta (hex -> nombre) ------------
  const NAME_BY_HEX = {
    '#FFFFFF':'Blanco','#F7F3E8':'Hueso pastel','#FFF2CC':'Crema','#FFF5A8':'Amarillo suave',
    '#FFD9B3':'Melocotón','#FAD0E4':'Rosa pastel','#E6E0F8':'Lavanda','#D7C4F3':'Lila','#C7B8EA':'Malva',
    '#93C5FD':'Azul cielo','#BDE0FE':'Azul pastel','#60A5FA':'Azul medio','#7DD3FC':'Turquesa','#22D3EE':'Cian',
    '#A7F3D0':'Menta','#C7EFCF':'Verde pastel','#34D399':'Verde medio','#A3E635':'Lima','#EAB308':'Mostaza',
    '#FB923C':'Naranja','#FB7185':'Coral','#EF4444':'Rojo','#991B1B':'Granate','#8B5E34':'Marrón',
    '#A8A29E':'Topo','#E5E7EB':'Gris claro','#9CA3AF':'Gris medio','#4B5563':'Gris oscuro','#1E3A8A':'Azul marino',
    '#000000':'Negro',
  };
  const ts = () => Date.now();

  // ------------ utils ------------
  function addQuery(url, params) {
    const u = new URL(url, window.location.origin);
    Object.entries(params || {}).forEach(([k, v]) => u.searchParams.set(k, v));
    return u.pathname + (u.search ? u.search : '');
  }
  function urlLineId() {
    const m = location.search.match(/[?&]spw_line_id=(\d+)/); return m ? m[1] : null;
  }
  function getLineId(lineEl) {
    if (!lineEl) return urlLineId();
    const c = lineEl.getAttribute('data-line-id') ? lineEl :
      lineEl.querySelector('[data-line-id]') ||
      lineEl.querySelector('input[name="line_id"]') ||
      lineEl.querySelector('button[data-line-id], a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || urlLineId() || null;
  }

  // Detecta todas las apariciones de #HEX en la descripción y les asigna nombre
  function parsePersonalizations(text) {
    if (!text) return [];
    const out = [];
    const re = /#([0-9a-fA-F]{3,8})/g; // reconoce cualquier #HEX
    let m, i = 0;
    while ((m = re.exec(text))) {
      const hex = ('#' + m[1]).toUpperCase();
      out.push({ idx: i++, hex, name: NAME_BY_HEX[hex] || null });
    }
    return out.length ? out : [{ idx: 0, hex: null, name: null }];
  }

  // Candidatos de URL por índice (soporta multi-imagen por línea)
  function buildUrlCandidates(lineId, idx) {
    const n = idx + 1;
    const base = `/spw/line_preview/${lineId}`;
    const exts = ['png','webp','jpg','jpeg'];
    const indexedBases = [`${base}-${n}`,`${base}/${n}`,`${base}_${n}`];
    const urls = [];
    for (const b of indexedBases) for (const ext of exts) urls.push(addQuery(`${b}.${ext}`, { v: ts() }));
    for (const ext of exts) urls.push(addQuery(`${base}.${ext}`, { i: n, v: ts() }));
    urls.push(addQuery(base, { i: n, v: ts() }));
    for (const ext of exts) urls.push(addQuery(`${base}.${ext}`, { i: n, fb: 1, v: ts() }));
    return [...new Set(urls)];
  }

  // Contenedor por línea
  function ensureWrap(info) {
    let wrap = info.querySelector('.spw-cart-preview');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-top:8px';
      info.appendChild(wrap);
    }
    return wrap;
  }

  // Carga la primera URL válida
  function tryLoad(img, candidates) {
    let k = 0;
    function next(){ if (k >= candidates.length) { img.remove(); return; } const url=candidates[k++]; img.onerror=next; img.onload=null; img.src=url; }
    next();
  }

  // Render de una línea del carrito
  function renderLine(lineEl) {
    const info = lineEl.querySelector(INFO_SEL) || lineEl; if (!info) return;
    const lineId = getLineId(lineEl); if (!lineId) return;

    const wrap = ensureWrap(info);
    wrap.innerHTML = ''; // reset

    const persos = parsePersonalizations(info.textContent || '');

    persos.forEach(({ idx, hex, name }) => {
      // item vertical (imagen + pie con nombre/código)
      const item = document.createElement('div');
      item.className = 'spw-item';
      item.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px';

      // imagen
      const img = new Image();
      img.alt = 'Personalización';
      img.loading = 'lazy';
      img.style.cssText = 'max-width:140px;height:auto;border:1px solid #e5e7eb;border-radius:8px;background:#fff';
      item.appendChild(img);

      const candidates = buildUrlCandidates(lineId, idx);
      tryLoad(img, candidates);

      // pie (píldora + nombre + código)
      const cap = document.createElement('div');
      cap.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:12px;color:#374151';
      const dot = document.createElement('span');
      dot.style.cssText = 'width:12px;height:12px;border-radius:9999px;border:1px solid rgba(0,0,0,.15);display:inline-block;background:' + (hex || '#fff');
      const label = document.createElement('span');
      label.textContent = (name || '') + (hex ? (name ? `  ${hex}` : hex) : '');
      if (!name && !hex) label.textContent = '—';
      cap.appendChild(dot);
      cap.appendChild(label);

      item.appendChild(cap);
      wrap.appendChild(item);
    });
  }

  function initialInject(){ document.querySelectorAll(LINE_SEL).forEach(renderLine); }

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

  function boot(){
    if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    initialInject();
    observeMutations();
    console.log('[SPW] cart preview: imagen + nombre y código por color');
  }

  onReady(boot);
});