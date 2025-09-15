/* addons/serial_printer_custom_wizard/static/src/js/spw.js */
(function () {
  const $ = (sel, root) => (root || document).querySelector(sel);
  const byId = (id) => document.getElementById(id);

  // === Referencias UI (mantiene tus IDs/clases actuales) ===
  const imgBase = byId('spw_product_img');      // imagen del producto (base)
  const logoImg = byId('spw_logo_preview');     // overlay del logo
  const inFile  = byId('spw_logo_input');
  const inSize  = byId('spw_size');
  const inX     = byId('spw_pos_x');
  const inY     = byId('spw_pos_y');
  const inRot   = byId('spw_rotation');
  const inQty   = byId('spw_qty');              // cantidad
  const inNotes = byId('spw_notes');            // observaciones
  const btnCar  = byId('spw_add_to_cart_btn');  // botón "Añadir al carrito"
  const btnPNG  = byId('spw_download_png');     // botón "Descargar PNG"

  // === Estado interno mínimo ===
  let logoLoaded = false;        // si hay logo cargado
  let logoIsSVG  = false;        // si el logo es SVG (para color)
  let lastDataURL = '';          // dataURL del logo (png/jpg/svg)
  let baseNatural = {w:0, h:0};  // tamaño natural de la base (para composición)

  function readNaturalSize(img, cb) {
    if (!img) return cb && cb({w:0,h:0});
    if (img.naturalWidth && img.naturalHeight) {
      return cb && cb({w: img.naturalWidth, h: img.naturalHeight});
    }
    const tmp = new Image();
    tmp.onload = () => cb && cb({w: tmp.naturalWidth, h: tmp.naturalHeight});
    tmp.src = img.src;
  }

  // === PREVIEW ===
  function applyTransform() {
    if (!logoImg) return;
    const size = parseInt(inSize?.value || '100', 10);  // % del ancho de la base visible
    const x    = parseInt(inX?.value    || '0', 10);    // -50..50 (relativo)
    const y    = parseInt(inY?.value    || '10', 10);
    const rot  = parseInt(inRot?.value  || '0', 10);

    // Ancho del overlay relativo al ancho mostrado de la imagen base
    const baseRect = imgBase?.getBoundingClientRect?.() || {width: 0, height: 0};
    if (baseRect.width) {
      logoImg.style.width = Math.max(10, Math.min(200, size)) + '%';
    }
    // pos central + desplazamiento (en % para que sea consistente en móvil)
    logoImg.style.transform =
      `translate(calc(-50% + ${x}%), calc(-50% + ${y}%)) rotate(${rot}deg)`;
    logoImg.style.opacity = logoLoaded ? '1' : '0';
    logoImg.classList.toggle('d-none', !logoLoaded);
  }

  function handleFile(e) {
    const f = (e.target.files || [])[0];
    if (!f) return;
    const ext = (f.name.split('.').pop() || '').toLowerCase();
    logoIsSVG = ext === 'svg';
    const reader = new FileReader();
    reader.onload = () => {
      lastDataURL = reader.result;
      logoImg.src = lastDataURL;
      logoLoaded = true;
      applyTransform();
    };
    reader.readAsDataURL(f);
  }

  // === EXPORTACIÓN A CANVAS (rápida) ===
  async function spwExportCanvas() {
    // 1) tamaños reales de base y overlay en pantalla
    const baseRect = imgBase?.getBoundingClientRect?.();
    if (!baseRect || !baseRect.width || !baseRect.height) return null;

    // 2) canvas con tamaño del DOM mostrado (rápido y suficiente para pedido)
    const canvas = document.createElement('canvas');
    canvas.width  = Math.round(baseRect.width);
    canvas.height = Math.round(baseRect.height);
    const ctx = canvas.getContext('2d');

    // 3) cargar imágenes con seguridad misma-origen (son /web/image y dataURL)
    const base = new Image();
    base.crossOrigin = 'anonymous';
    const logo = new Image();
    logo.crossOrigin = 'anonymous';

    const p1 = new Promise((res, rej) => { base.onload = res; base.onerror = rej; base.src = imgBase.src; });
    const p2 = new Promise((res, rej) => {
      if (!lastDataURL) { res(); return; }
      logo.onload = res; logo.onerror = rej; logo.src = lastDataURL;
    });

    // 4) esperar
    try { await Promise.all([p1, p2]); } catch(e) { /* ignore */ }

    // 5) pintar base
    ctx.drawImage(base, 0, 0, canvas.width, canvas.height);

    // 6) pintar logo si corresponde, respetando la posición/rotación/escala de la UI
    if (lastDataURL && logoLoaded) {
      // calcular destino a partir de bounding rects
      const logoRect = logoImg.getBoundingClientRect();
      const cx = logoRect.left - baseRect.left + logoRect.width/2;
      const cy = logoRect.top  - baseRect.top  + logoRect.height/2;

      ctx.save();
      ctx.translate(cx, cy);
      const rot = parseInt(inRot?.value || '0', 10) * Math.PI/180;
      ctx.rotate(rot);
      // drawer con el mismo ancho/alto que en pantalla
      ctx.drawImage(
        logo,
        -logoRect.width/2, -logoRect.height/2,
        logoRect.width,     logoRect.height
      );
      ctx.restore();
    }
    return canvas;
  }

  async function spwExportPNGBase64() {
    const canvas = await spwExportCanvas();
    if (!canvas) return '';
    // más rápido con toDataURL (para el adjunto)
    const dataURL = canvas.toDataURL('image/png');
    return (dataURL || '').replace(/^data:image\/png;base64,/, '');
  }

  async function spwDownloadPNGFast() {
    const canvas = await spwExportCanvas();
    if (!canvas) return;
    if (canvas.toBlob) {
      canvas.toBlob(function (blob) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'personalizacion.png';
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }, 'image/png');
    } else {
      // Fallback
      const a = document.createElement('a');
      a.href = canvas.toDataURL('image/png');
      a.download = 'personalizacion.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    }
  }

  // === AÑADIR AL CARRITO ===
  async function spwAddToCart() {
    try {
      const variantId = parseInt(byId('spw_variant_id')?.value || '0', 10);
      const qty       = parseInt(inQty?.value || '1', 10);
      const tech      = ($('input[name="spw_tech"]:checked')?.value) || '';
      const svgColor  = ($('input[name="spw_svg_color"]:checked')?.value) || '';
      const notes     = inNotes?.value || '';

      let png_b64 = '';
      // Generamos PNG en base64 (sin prefijo) para adjuntar en la línea de venta
      try { png_b64 = await spwExportPNGBase64(); } catch (e) { png_b64 = ''; }

      const payload = { variant_id: variantId, qty, tech, svg_color: svgColor, notes, png_b64 };

      const res = await fetch('/spw/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',                   // NECESARIO para la cookie de sesión
        body: JSON.stringify(payload),
      });

      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch (_) { data = { ok:false, message: text || 'Respuesta no válida' }; }

      if (data && data.ok) {
        window.location.href = data.cart_url || '/shop/cart';
      } else {
        alert('No se pudo añadir al carrito.\n' + (data && data.message ? data.message : ''));
      }
    } catch (err) {
      alert('No se pudo añadir al carrito.\n' + (err && err.message ? err.message : String(err)));
    }
  }

  // === RESET (mantén tu botón que llama window.spwReset) ===
  function spwReset() {
    try { inFile && (inFile.value = ''); } catch(e) {}
    if (logoImg) {
      logoImg.src = '';
      logoLoaded = false;
      applyTransform();
    }
    if (inSize) inSize.value = 100;
    if (inX)    inX.value = 0;
    if (inY)    inY.value = 10;
    if (inRot)  inRot.value = 0;
    if (inNotes) inNotes.value = '';
    if (inQty)   inQty.value = 1;
    const tech = $('input[name="spw_tech"]');
    if (tech) {
      const first = document.querySelector('input[name="spw_tech"]');
      if (first) first.checked = true;
    }
    const col = $('input[name="spw_svg_color"]');
    if (col) {
      const firstC = document.querySelector('input[name="spw_svg_color"]');
      if (firstC) firstC.checked = true;
    }
  }

  // === Eventos ===
  document.addEventListener('DOMContentLoaded', function () {
    // Guardamos tamaño natural de la base (no imprescindible, pero útil)
    readNaturalSize(imgBase, (sz) => { baseNatural = sz || {w:0,h:0}; });

    if (inFile) inFile.addEventListener('change', handleFile);
    if (inSize) inSize.addEventListener('input', applyTransform);
    if (inX)    inX.addEventListener('input', applyTransform);
    if (inY)    inY.addEventListener('input', applyTransform);
    if (inRot)  inRot.addEventListener('input', applyTransform);
    // Delegación para botones (no rompe nada)
    document.addEventListener('click', function (ev) {
      const b1 = ev.target.closest('#spw_add_to_cart_btn');
      if (b1) { ev.preventDefault(); spwAddToCart(); }
      const b2 = ev.target.closest('#spw_download_png');
      if (b2) { ev.preventDefault(); spwDownloadPNGFast(); }
    });
  });

  // Exponer utilidades en window (compatibilidad con tu template)
  window.spwReset = spwReset;
  window.spwExportCanvas = spwExportCanvas;
  window.spwExportPNGBase64 = spwExportPNGBase64;

})();