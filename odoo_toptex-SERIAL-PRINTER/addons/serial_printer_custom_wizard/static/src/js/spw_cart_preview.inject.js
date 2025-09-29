/** SPW – Cart preview (multi imagen + píldora + texto por bloque) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  // ---------- ready ----------
  function onReady(cb){ document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }

  // ---------- selectores (muy permisivos para todos los temas) ----------
  const LINE_SEL = '.o_cart_product, .o_wsale_cart_item, .js_cart_lines tr, .cart_line';
  const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  // ---------- utils ----------
  const ts = () => Date.now();

  function getLineId(root){
    if(!root) return null;
    const c = root.getAttribute('data-line-id') ? root :
      root.querySelector('[data-line-id]') ||
      root.querySelector('input[name="line_id"]') ||
      root.querySelector('button[data-line-id],a[data-line-id]');
    return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || null;
  }

  // Extrae bloques en el formato “— Personalización N — …”
  function parseBlocks(text){
    const out = [];
    if(!text) return out;
    const re = /—\s*Personalización\s*(\d+)\s*—([\s\S]*?)(?=—\s*Personalización\s*\d+\s*—|$)/g;
    let m;
    while((m = re.exec(text))){
      const seq = parseInt(m[1],10);
      const body = m[2] || '';
      const tech  = (body.match(/Técnica:\s*([^\n]+)/i) || [])[1]?.trim() || '';
      const color = (body.match(/Color\s*SVG:\s*(#[0-9a-fA-F]{3,8})/i) || [])[1]?.trim() || '';
      const notes = (body.match(/Observaciones:\s*([\s\S]+)/i) || [])[1]?.trim() || '';
      out.push({seq, tech, color, notes});
    }
    // Compatibilidad: si no hay bloques, intenta un único color suelto
    if(!out.length){
      const color = (text.match(/Color\s*SVG:\s*(#[0-9a-fA-F]{3,8})/i) || [])[1];
      const tech  = (text.match(/Técnica:\s*([^\n]+)/i) || [])[1];
      const notes = (text.match(/Observaciones:\s*([\s\S]+)/i) || [])[1];
      if(color || tech || notes){ out.push({seq:1, tech:tech||'', color:color||'', notes:notes||''}); }
    }
    // Ordena por N por si el texto llegó mezclado
    out.sort((a,b)=>a.seq-b.seq);
    return out;
  }

  function ensureWrap(info){
    let wrap = info.querySelector('.spw-cart-preview');
    if(!wrap){
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'display:flex;flex-direction:column;gap:10px;margin-top:10px';
      info.appendChild(wrap);
    }
    return wrap;
  }

  function renderBlock(container, lineId, blk){
    const row = document.createElement('div');
    row.className = 'spw-row';
    row.style.cssText = 'display:flex;gap:10px;align-items:flex-start';

    // IMG de esa personalización (solo url indexada)
    const img = new Image();
    img.alt = `Personalización ${blk.seq}`;
    img.loading = 'lazy';
    img.style.cssText = 'width:120px;height:auto;border:1px solid #e5e7eb;border-radius:8px;background:#fff';
    img.onerror = ()=> row.remove(); // si no hay PNG N, quitamos el bloque
    img.src = `/spw/line_preview/${lineId}-${blk.seq}.png?v=${ts()}`;

    // Texto + píldora
    const text = document.createElement('div');
    text.style.cssText = 'font-size:12px;line-height:1.3;display:flex;flex-direction:column;gap:4px';

    // Píldora + hex
    if(blk.color){
      const pillWrap = document.createElement('div');
      pillWrap.style.cssText = 'display:flex;align-items:center;gap:8px';
      const pill = document.createElement('span');
      pill.title = blk.color;
      pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block;background:'+blk.color;
      const hex = document.createElement('span');
      hex.textContent = blk.color;
      hex.style.cssText = 'font-weight:500';
      pillWrap.appendChild(pill);
      pillWrap.appendChild(hex);
      text.appendChild(pillWrap);
    }

    if(blk.tech){
      const t = document.createElement('div');
      t.textContent = `Técnica: ${blk.tech}`;
      text.appendChild(t);
    }
    if(blk.notes){
      const n = document.createElement('div');
      n.textContent = `Observaciones: ${blk.notes}`;
      text.appendChild(n);
    }

    row.appendChild(img);
    row.appendChild(text);
    container.appendChild(row);
  }

  function renderLine(lineEl){
    const info = lineEl.querySelector(INFO_SEL) || lineEl;
    const lineId = getLineId(lineEl);
    if(!info || !lineId) return;

    const wrap = ensureWrap(info);
    wrap.innerHTML = ''; // limpiar antes de pintar

    const text = info.textContent || '';
    const blocks = parseBlocks(text);
    if(!blocks.length) return;

    blocks.forEach(blk => renderBlock(wrap, lineId, blk));
  }

  function initial(){ document.querySelectorAll(LINE_SEL).forEach(renderLine); }

  function observe(){
    const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
    new MutationObserver(ms=>{
      for(const m of ms){
        m.addedNodes && m.addedNodes.forEach(n=>{
          if(n instanceof HTMLElement){
            if(n.matches?.(LINE_SEL)) renderLine(n);
            n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
          }
        });
      }
    }).observe(root, {childList:true, subtree:true});
  }

  function boot(){
    if(!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    initial(); observe();
    console.log('[SPW] cart preview listo (multi N, sin fallback no indexado)');
  }

  onReady(boot);
});