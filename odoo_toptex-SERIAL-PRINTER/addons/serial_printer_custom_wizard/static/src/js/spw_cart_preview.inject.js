/** SPW – Cart preview injector (fotos + píldoras + NOMBRE DE COLOR) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // ---- ready ----
  function onReady(cb){ document.readyState==='loading'
    ? document.addEventListener('DOMContentLoaded', cb, {once:true})
    : cb(); }

  // ---- selectores estables de líneas/info ----
  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  // ---- mapa HEX -> nombre (mantenlo en sync con tu paleta) ----
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
  const nameFromHex = (hex) => HEX2NAME[(hex||'').toUpperCase()] || null;

  const ts = () => Date.now();
  function addQuery(url, params){
    const u = new URL(url, window.location.origin);
    Object.entries(params||{}).forEach(([k,v]) => u.searchParams.set(k,v));
    return u.pathname + (u.search?u.search:'');
  }
  function urlLineId(){
    const m = location.search.match(/[?&]spw_line_id=(\d+)/);
    return m ? m[1] : null;
  }
  function getLineId(lineEl){
    if (!lineEl) return urlLineId();
    const c = lineEl.getAttribute('data-line-id') ? lineEl :
      lineEl.querySelector('[data-line-id]') ||
      lineEl.querySelector('input[name="line_id"]') ||
      lineEl.querySelector('button[data-line-id], a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || urlLineId() || null;
  }
  function parsePersonalizations(text){
    if (!text) return [];
    const out = [];
    const re = /Color\s*SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
    let m, i = 0;
    while ((m = re.exec(text))) out.push({ idx:i++, hex:'#'+m[1] });
    return out.length ? out : [{ idx:0, hex:null }];
  }
  function buildUrlCandidates(lineId, idx){
    const n = idx+1, base = `/spw/line_preview/${lineId}`, exts=['png','webp','jpg','jpeg'];
    const indexedBases=[`${base}-${n}`,`${base}/${n}`,`${base}_${n}`];
    const urls=[];
    for (const b of indexedBases) for (const ext of exts) urls.push(addQuery(`${b}.${ext}`,{v:ts()}));
    for (const ext of exts) urls.push(addQuery(`${base}.${ext}`,{i:n,v:ts()}));
    urls.push(addQuery(base,{i:n,v:ts()}));
    for (const ext of exts) urls.push(addQuery(`${base}.${ext}`,{i:n,fb:1,v:ts()}));
    return [...new Set(urls)];
  }
  function tryLoad(img, candidates){
    let k=0; function next(){ if (k>=candidates.length){ img.remove(); return; }
      const url=candidates[k++]; img.onerror=next; img.onload=null; img.src=url; }
    next();
  }
  function ensureWrap(info){
    let wrap = info.querySelector('.spw-cart-preview');
    if (!wrap){
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'display:flex;flex-direction:column;gap:12px;margin-top:8px';
      info.appendChild(wrap);
    }
    return wrap;
  }

  function renderLine(lineEl){
    const info = lineEl.querySelector(INFO_SEL) || lineEl;
    if (!info) return;
    const lineId = getLineId(lineEl);
    if (!lineId) return;

    const wrap = ensureWrap(info);
    wrap.innerHTML = '';

    const persos = parsePersonalizations(info.textContent || '');
    persos.forEach(({ idx, hex }) => {
      const block = document.createElement('div');
      block.className = 'spw-item';
      block.style.cssText = 'display:flex;align-items:flex-start;gap:10px';

      // imagen
      const img = new Image();
      img.alt = 'Personalización';
      img.loading = 'lazy';
      img.style.cssText = 'width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
      block.appendChild(img);
      tryLoad(img, buildUrlCandidates(lineId, idx));

      // meta (píldora + nombre + código)
      const meta = document.createElement('div');
      meta.style.cssText = 'display:flex;flex-direction:column;gap:6px;min-width:120px';
      const pillRow = document.createElement('div');
      pillRow.style.cssText = 'display:flex;align-items:center;gap:8px';
      const pill = document.createElement('span');
      pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block;background:'+ (hex||'transparent');
      pill.title = hex || '—';
      pillRow.appendChild(pill);

      const name = nameFromHex(hex);
      const nameEl = document.createElement('span');
      nameEl.textContent = name ? `${name}` : (hex||'—');
      nameEl.style.cssText = 'font-size:12px;color:#374151';
      pillRow.appendChild(nameEl);

      const codeEl = document.createElement('div');
      codeEl.textContent = hex || '';
      codeEl.style.cssText = 'font-size:11px;color:#6B7280';

      meta.appendChild(pillRow);
      if (hex) meta.appendChild(codeEl);
      block.appendChild(meta);

      wrap.appendChild(block);
    });
  }

  function initialInject(){ document.querySelectorAll(LINE_SEL).forEach(renderLine); }
  function observeMutations(){
    const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    new MutationObserver(ms=>{
      for (const m of ms){
        m.addedNodes && m.addedNodes.forEach(n=>{
          if (n instanceof HTMLElement){
            if (n.matches?.(LINE_SEL)) renderLine(n);
            else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
          }
        });
      }
    }).observe(root,{childList:true,subtree:true});
  }
  function boot(){
    // Sólo arrancar en páginas de carrito
    if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    initialInject(); observeMutations();
    console.log('[SPW] injector listo (foto+píldora+nombre de color)');
  }
  onReady(boot);
});