/** SPW – Cart preview injector (fotos + píldoras + texto) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // -------- ready sin dependencias --------
  function onReady(cb){ if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',cb,{once:true});}else cb(); }

  // -------- selectores --------
  const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  // -------- utils --------
  const ts = () => Date.now();
  function addQuery(url, params){ const u=new URL(url, window.location.origin); Object.entries(params||{}).forEach(([k,v])=>u.searchParams.set(k,v)); return u.pathname + (u.search?u.search:''); }
  function urlLineId(){ const m=location.search.match(/[?&]spw_line_id=(\d+)/); return m?m[1]:null; }

  function getLineId(lineEl){
    if(!lineEl) return urlLineId();
    const c = lineEl.getAttribute('data-line-id') ? lineEl :
      lineEl.querySelector('[data-line-id]') ||
      lineEl.querySelector('input[name="line_id"]') ||
      lineEl.querySelector('button[data-line-id], a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || urlLineId() || null;
  }

  // De la descripción del carrito extraemos pares por personalización:
  //  "Técnica: X ... Color SVG: #HEX ... Observaciones: Y"
  function parseEntries(text){
    if(!text) return [];
    const t = text.replace(/\s+/g,' ').trim();
    const re = /(?:T[eé]cnica:\s*([^|#\n]+))?.*?Color\s*SVG:\s*(#(?:[0-9a-fA-F]{3,8})).*?(?:Observaciones?:\s*([^|#\n]+))?/gi;
    const out = []; let m, i=0;
    while((m=re.exec(t))){
      out.push({
        idx:i++,
        tech:(m[1]||'').trim(),
        hex:(m[2]||'').trim(),
        notes:(m[3]||'').trim()
      });
    }
    // si no encontramos entradas, al menos devolvemos 1 vacía para no romper pairing
    return out.length ? out : [{ idx:0, tech:'', hex:'', notes:'' }];
  }

  // candidatos de URL por índice (1..n)
  function buildUrlCandidates(lineId, idx){
    const n = idx+1;
    const base = `/spw/line_preview/${lineId}`;
    const exts = ['png','webp','jpg','jpeg'];
    const indexedBases = [`${base}-${n}`, `${base}/${n}`, `${base}_${n}`];
    const urls = [];
    for(const b of indexedBases) for(const ext of exts) urls.push(addQuery(`${b}.${ext}`, {v:ts()}));
    for(const ext of exts) urls.push(addQuery(`${base}.${ext}`, {i:n, v:ts()}));
    urls.push(addQuery(base, {i:n, v:ts()}));
    for(const ext of exts) urls.push(addQuery(`${base}.${ext}`, {i:n, fb:1, v:ts()}));
    return [...new Set(urls)];
  }

  function ensureWrap(info){
    let wrap = info.querySelector('.spw-cart-preview');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'display:flex;flex-wrap:wrap;gap:12px;margin-top:8px';
      info.appendChild(wrap);
    }
    return wrap;
  }

  // carga el primer candidato válido; si ninguno responde, elimina el <img>
  function tryLoad(img, candidates){
    let k=0;
    function next(){
      if(k>=candidates.length){ img.remove(); return; }
      const url=candidates[k++]; img.onerror=next; img.onload=null; img.src=url;
    }
    next();
  }

  function renderLine(lineEl){
    const info = lineEl.querySelector(INFO_SEL) || lineEl;
    if(!info) return;
    const lineId = getLineId(lineEl);
    if(!lineId) return;

    const wrap = ensureWrap(info);
    wrap.innerHTML = '';

    const entries = parseEntries(info.textContent || '');

    entries.forEach(({idx, tech, hex, notes})=>{
      // card (img + pill + caption)
      const card = document.createElement('div');
      card.className = 'spw-card';
      card.style.cssText='display:flex;flex-direction:column;align-items:center;gap:6px;max-width:140px';

      // imagen
      const img = new Image();
      img.alt = 'Personalización';
      img.loading = 'lazy';
      img.style.cssText='max-width:140px;height:auto;border:1px solid #e5e7eb;border-radius:6px;display:block';
      card.appendChild(img);

      // píldora debajo de la imagen
      const pill = document.createElement('span');
      pill.title = hex || '—';
      pill.style.cssText='width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
      if(hex) pill.style.background = hex;
      card.appendChild(pill);

      // caption con técnica + observaciones
      const cap = document.createElement('div');
      cap.className = 'spw-caption';
      cap.style.cssText='font-size:12px;line-height:1.25;color:#6b7280;text-align:center;word-break:break-word';
      cap.innerHTML = [
        tech ? `Técnica: ${tech}` : '',
        notes ? `${notes}` : ''
      ].filter(Boolean).map(s=>`<div>${s}</div>`).join('');
      if(cap.innerHTML) card.appendChild(cap);

      wrap.appendChild(card);

      // carga imagen correspondiente al índice
      tryLoad(img, buildUrlCandidates(lineId, idx));
    });
  }

  function initialInject(){ document.querySelectorAll(LINE_SEL).forEach(renderLine); }

  function observeMutations(){
    const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    new MutationObserver(ms=>{
      for(const m of ms){
        m.addedNodes && m.addedNodes.forEach(n=>{
          if(n instanceof HTMLElement){
            if(n.matches?.(LINE_SEL)) renderLine(n);
            else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
          }
        });
      }
    }).observe(root,{childList:true,subtree:true});
  }

  function boot(){
    if(!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    initialInject();
    observeMutations();
    console.log('[SPW] injector listo (multi-foto + pildora + caption por línea)');
  }

  onReady(boot);
});