/** serial_printer_custom_wizard/static/src/js/spw_cart_preview.inject.js **/
(function () {
  "use strict";

  // Ejecutar solo en carrito/checkout
  if (!/\/shop\/(cart|checkout)/.test(location.pathname)) return;

  function q(s, r){ return (r||document).querySelector(s); }
  function qa(s, r){ return Array.from((r||document).querySelectorAll(s)); }

  function getLineId(line){
    if (!line) return null;
    // Odoo 17 usa distintos contenedores; probamos varias fuentes:
    return line.getAttribute('data-line-id')
        || line.getAttribute('data-id')
        || ((q('input[name="line_id"]', line) || {}).value)
        || (function findInHref(){
              try{
                const a = line.closest('a[href*="line_id="]') || line.querySelector('a[href*="line_id="]');
                if(!a) return null;
                const u = new URL(a.getAttribute('href'), location.origin);
                return u.searchParams.get('line_id');
              } catch(e){ return null; }
            })()
        || null;
  }

  function findLines(){
    // Cubrimos plantillas de carrito y checkout
    const sel = [
      'tr.js_cart_line',
      '.o_wsale_cart_item',
      '.card.js_cart_item',
      '.o_cart_line',
      '.o_checkout_line'
    ].join(',');
    return qa(sel).filter(n => !!getLineId(n));
  }

  function infoContainer(line){
    // Donde inyectamos el bloque
    return q('.o_wsale_product_information', line)
        || q('.o_cart_product_info', line)
        || q('td.o_wsale_cart_description', line)
        || q('.media-body', line)
        || q('.o_wsale_cart_item_info', line)
        || line;
  }

  function detectHex(line){
    try{
      const cont = infoContainer(line);
      if(!cont) return null;
      const m = (cont.textContent || '').match(/#([0-9a-fA-F]{6})\b/);
      return m ? ('#'+m[1].toUpperCase()) : null;
    }catch(_){ return null; }
  }

  function insertPreview(line, pngSrc, hex){
    const id = getLineId(line); if(!id) return;

    // Limpia duplicados
    qa('.spw-cart-block[data-line="'+id+'"]', line).forEach(n => n.remove());

    const wrap = document.createElement('div');
    wrap.className = 'spw-cart-block';
    wrap.setAttribute('data-line', id);

    const img = new Image();
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.src = pngSrc;

    // Si el servidor devuelve 404, intentamos fallback inmediato (última sesión)
    img.onerror = function(){
      try{
        const lastId    = sessionStorage.getItem('spw_last_line_id');
        const lastPng   = sessionStorage.getItem('spw_last_png');
        const lastColor = sessionStorage.getItem('spw_last_color');
        if (lastId && lastPng && String(lastId) === String(id)) {
          img.src = lastPng; // dataURL
          if (!hex) hex = lastColor || hex;
        }
      }catch(_){}
    };

    wrap.appendChild(img);

    if (hex && /^#[0-9A-F]{6}$/i.test(hex)) {
      const sw = document.createElement('span');
      sw.className = 'spw-swatch';
      sw.title = hex;
      sw.style.background = hex;
      wrap.appendChild(sw);
    }

    (infoContainer(line) || line).appendChild(wrap);
  }

  function inject(){
    const lines = findLines();

    // Limpieza global
    qa('.spw-cart-block').forEach(n => {
      const lid = n.getAttribute('data-line');
      const alive = lines.some(l => getLineId(l) === lid);
      if(!alive) n.remove();
    });

    // Inserta/actualiza cada línea
    lines.forEach(line => {
      const id = getLineId(line);
      if(!id) return;
      const src = '/spw/line_preview/' + encodeURIComponent(id) + '.png?_=' + Date.now();
      const hex = detectHex(line);
      insertPreview(line, src, hex);
    });

    // No dependemos ya del parámetro ?spw_line_id=, pero si viene se respeta
    const wanted = (new URL(location.href)).searchParams.get('spw_line_id');
    if (wanted) {
      try{
        const lastId = sessionStorage.getItem('spw_last_line_id');
        const lastPng = sessionStorage.getItem('spw_last_png');
        const lastColor = sessionStorage.getItem('spw_last_color');
        if (lastId && lastPng && lastId === wanted) {
          const line = lines.find(l => getLineId(l) === wanted);
          if (line) insertPreview(line, lastPng, lastColor || detectHex(line));
        }
      }catch(_){}
    }
  }

  function boot(){
    // estilos mínimos (por si el theme no inyecta los del customizer)
    if (!q('#spw-cart-style')) {
      const s = document.createElement('style');
      s.id = 'spw-cart-style';
      s.textContent = `
        .spw-cart-block{margin-top:6px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
        .spw-cart-block img{max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px}
        .spw-swatch{width:16px;height:16px;border-radius:999px;border:1px solid #e5e7eb;display:inline-block}
      `;
      document.head.appendChild(s);
    }

    inject();
    const root = q('.js_cart_lines') || q('.o_wsale_cart') || q('main') || document.body;
    if (window.MutationObserver && root){
      const mo = new MutationObserver(() => requestAnimationFrame(inject));
      mo.observe(root, {childList:true, subtree:true});
    }
    setTimeout(inject, 400);
    setTimeout(inject, 1200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();