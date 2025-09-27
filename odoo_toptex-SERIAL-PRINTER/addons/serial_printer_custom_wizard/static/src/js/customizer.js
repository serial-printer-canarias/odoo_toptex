/* Previsualización del logo sobre la imagen del producto + Añadir al carrito (con PNG por línea) */
(function () {
  'use strict';

  // ------------------------ helpers ------------------------
  function $(s, r){ return (r||document).querySelector(s); }
  function $val(id, d){ var el=$("#"+id); return el ? el.value : d; }

  function loadImage(src){
    return new Promise(function(resolve, reject){
      var im = new Image();
      im.onload = function(){ resolve(im); };
      im.onerror = reject;
      // la base suele venir de /web/image -> same-origin
      im.crossOrigin = "anonymous";
      im.src = src;
    });
  }
  function readAsDataURL(file){
    return new Promise(function(resolve, reject){
      var r = new FileReader();
      r.onload = function(){ resolve(r.result); };
      r.onerror = reject;
      r.readAsDataURL(file);
    });
  }
  async function postJSON(url, payload){
    try{
      var resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
        body: JSON.stringify(payload)
      });
      var txt = await resp.text();
      var data=null; try{ data = JSON.parse(txt); }catch(_){}
      return { ok: !!(data && (data.ok===true || data.ok==="true")), data: data, status: resp.status, raw: txt };
    }catch(e){ return { ok:false, data:null, status:0, raw:String(e) }; }
  }
  async function postForm(url, payload){
    try{
      var fd = new FormData();
      Object.keys(payload||{}).forEach(function(k){ fd.append(k, payload[k]); });
      var resp = await fetch(url, { method:"POST", body:fd, credentials:"same-origin" });
      var txt = await resp.text();
      var data=null; try{ data = JSON.parse(txt); }catch(_){}
      return { ok: resp.ok && (!!data ? (data.ok===true || data.ok==="true") : true), data:data||{}, status:resp.status, raw:txt };
    }catch(e){ return { ok:false, data:null, status:0, raw:String(e) }; }
  }

  // ------------------------ estado / preview ------------------------
  var els = {
    canvas:     null,
    logoInput:  null,
    logoImg:    null,
    sizeEl:     null,
    posXEl:     null,
    posYEl:     null,
    rotEl:      null,
    baseImg:    null, // #spw_product_img
    baseInt:    null  // #spw-base-img (si existe)
  };

  var state = {
    widthPct: 100,
    dxPct:    0,
    dyPct:    10,
    rotDeg:   0
  };

  function applyTransform(){
    if (!els.logoImg) return;
    els.logoImg.style.position = 'absolute';
    els.logoImg.style.left     = (50 + state.dxPct) + '%';
    els.logoImg.style.top      = (50 + state.dyPct) + '%';
    els.logoImg.style.width    = state.widthPct + '%';
    els.logoImg.style.transform= 'translate(-50%, -50%) rotate(' + state.rotDeg + 'deg)';
    els.logoImg.style.zIndex   = '999';
    els.logoImg.style.opacity  = '1';
    els.logoImg.classList.remove('d-none');
  }

  // ------------------------ render PNG (para adjuntar a la línea) ------------------------
  async function renderPNGDataURL(){
    // 1) escoger mejor base same-origin
    var baseSrc =
      (els.baseInt && els.baseInt.getAttribute('src')) ||
      (els.baseImg && els.baseImg.getAttribute('src'));
    if(!baseSrc) throw new Error('Sin imagen base');

    var baseIm = await loadImage(baseSrc);

    // 2) preparar canvas al tamaño real de la base
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    canvas.width  = baseIm.naturalWidth  || baseIm.width;
    canvas.height = baseIm.naturalHeight || baseIm.height;
    ctx.drawImage(baseIm, 0, 0, canvas.width, canvas.height);

    // 3) dibujar logo si existe
    var logoEl = els.logoImg;
    if (logoEl && logoEl.src){
      // Pasamos de porcentajes visuales a coordenadas reales del canvas
      var bw = (els.baseImg && els.baseImg.clientWidth)  || canvas.width;
      var bh = (els.baseImg && els.baseImg.clientHeight) || canvas.height;

      // centro relativo (en % visual) -> normalizado [0..1]
      var cx_norm = (50 + state.dxPct) / 100;
      var cy_norm = (50 + state.dyPct) / 100;
      var w_norm  = state.widthPct / 100;

      var cx = cx_norm * canvas.width;
      var cy = cy_norm * canvas.height;
      var drawW = w_norm * canvas.width;

      var logoIm = await loadImage(logoEl.src);
      var ratio = (logoIm.naturalHeight || logoIm.height) / (logoIm.naturalWidth || logoIm.width);
      var drawH = drawW * ratio;

      var rot = (state.rotDeg * Math.PI) / 180;

      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      ctx.drawImage(logoIm, -drawW/2, -drawH/2, drawW, drawH);
      ctx.restore();
    }

    return canvas.toDataURL('image/png');
  }

  // ------------------------ añadir al carrito ------------------------
  async function addToCart(){
    var variantId = ($val('spw_variant_id','')||'').trim();
    if(!variantId){ alert('Falta la variante del producto.'); return; }

    var qty      = parseInt($val('spw_qty','1'),10)||1;
    var tech     = ((document.querySelector("input[name='spw_tech']:checked")||{}).value)||'';
    var svgColor = ((document.querySelector("input[name='spw_svg_color']:checked")||{}).value)||'';
    var notes    = ($val('spw_notes','')||'').trim();

    // 1) PNG local (para mostrar inmediatamente al volver al carrito)
    var pngDataURL = '';
    try{
      pngDataURL = await renderPNGDataURL();
      sessionStorage.setItem('spw_last_png',   pngDataURL || '');
      sessionStorage.setItem('spw_last_color', svgColor   || '');
    }catch(_){}

    // 2) crear línea con meta -> devuelve line_id
    var r1 = await postJSON('/spw/add_to_cart_meta', {
      variant_id: parseInt(variantId,10),
      qty: qty, tech: tech, svg_color: svgColor, notes: notes
    });
    if(!r1.ok){
      r1 = await postForm('/spw/add_to_cart_meta_http', {
        variant_id: variantId,
        qty: qty, tech: tech, svg_color: svgColor, notes: notes
      });
    }
    if(!r1.ok || !(r1.data && r1.data.line_id)){
      alert((r1.data && r1.data.message) ? r1.data.message : 'No se pudo añadir.');
      return;
    }

    var lineId = String(r1.data.line_id || '');
    try{ sessionStorage.setItem('spw_last_line_id', lineId); }catch(_){}

    // 3) adjuntar PNG a ESA línea (clave para varias personalizaciones mismo SKU)
    if(pngDataURL){
      var b64 = pngDataURL.split('base64,')[1] || '';
      if (b64){
        var r2 = await postJSON('/spw/attach_png', { line_id: lineId, png_b64: b64 });
        if(!r2.ok){ await postForm('/spw/attach_png_http', { line_id: lineId, png_b64: b64 }); }
      }
    }

    // 4) redirigir al carrito apuntando esa línea
    var cart = (r1.data && r1.data.cart_url) || '/shop/cart';
    var url  = cart + (cart.indexOf('?')===-1?'?':'&') + 'spw_line_id=' + encodeURIComponent(lineId);
    window.location.href = url;
  }

  // ------------------------ init ------------------------
  function init(){
    els.canvas    = $('#spw_canvas');
    if (!els.canvas) return;

    els.logoInput = $('#spw_logo_input');
    els.logoImg   = $('#spw_logo_preview');
    els.sizeEl    = $('#spw_size');
    els.posXEl    = $('#spw_pos_x');
    els.posYEl    = $('#spw_pos_y');
    els.rotEl     = $('#spw_rotation');
    els.baseImg   = $('#spw_product_img');
    els.baseInt   = $('#spw-base-img'); // opcional

    state.widthPct = parseInt((els.sizeEl && els.sizeEl.value) || '100', 10);
    state.dxPct    = parseInt((els.posXEl && els.posXEl.value) || '0',   10);
    state.dyPct    = parseInt((els.posYEl && els.posYEl.value) || '10',  10);
    state.rotDeg   = parseInt((els.rotEl  && els.rotEl.value)  || '0',   10);

    // Controles
    if (els.sizeEl) els.sizeEl.addEventListener('input', function(){ state.widthPct = parseInt(els.sizeEl.value||'100',10); applyTransform(); });
    if (els.posXEl) els.posXEl.addEventListener('input', function(){ state.dxPct    = parseInt(els.posXEl.value||'0',  10); applyTransform(); });
    if (els.posYEl) els.posYEl.addEventListener('input', function(){ state.dyPct    = parseInt(els.posYEl.value||'10', 10); applyTransform(); });
    if (els.rotEl)  els.rotEl.addEventListener('input',  function(){ state.rotDeg   = parseInt(els.rotEl.value ||'0',  10); applyTransform(); });

    // Subida de logo
    if (els.logoInput && els.logoImg) {
      els.logoInput.addEventListener('change', function(ev){
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;
        if (file.size > 10 * 1024 * 1024) { alert('El archivo supera 10MB.'); return; }
        var mime = (file.type || '').toLowerCase();
        if (!mime.startsWith('image/')) { alert('Formato no soportado. Usa PNG, JPG o SVG.'); return; }

        readAsDataURL(file).then(function(dataURL){
          els.logoImg.src = dataURL;
          els.logoImg.removeAttribute('loading');
          els.logoImg.decoding = 'sync';
          applyTransform();
          try{ els.logoImg.scrollIntoView({ behavior:'smooth', block:'center' }); }catch(_){}
        });
      });
    }

    // Botón "Añadir al carrito con esta personalización"
    var addBtn = $('#spw_add_to_cart');
    if (addBtn) addBtn.addEventListener('click', addToCart);

    applyTransform();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();