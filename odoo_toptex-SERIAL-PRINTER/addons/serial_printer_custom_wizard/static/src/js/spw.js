/** addons/serial_printer_custom_wizard/static/src/js/spw.js
 *  - No toca nada de tu previsualización existente.
 *  - Arregla "Descargar PNG" (iOS abre vista previa; resto fuerza descarga).
 *  - Arregla "Añadir al carrito con personalización" (usa line_id devuelto, limpia base64, maneja errores claros).
 */
(function () {
  "use strict";

  // --- Helpers ---
  function $(sel) { return document.querySelector(sel); }
  function getCheckedValue(name) {
    const el = document.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : "";
  }
  function isIOS() {
    return /iphone|ipad|ipod/i.test(navigator.userAgent);
  }

  // Carga una <img> asegurando naturalWidth/Height
  function ensureLoaded(img) {
    return new Promise((resolve, reject) => {
      if (!img) return reject(new Error("Imagen no encontrada."));
      if (img.complete && img.naturalWidth) return resolve(img);
      img.addEventListener('load', () => resolve(img), { once: true });
      img.addEventListener('error', () => reject(new Error("No se pudo cargar la imagen.")), { once: true });
    });
  }

  // Construye un PNG a partir del estado visual (producto + logo)
  async function buildCompositeDataURL() {
    const baseImg = $('#spw_product_img');
    const logoImg = $('#spw_logo_preview');
    const rotationInput = $('#spw_rotation');

    await ensureLoaded(baseImg);
    // Si no hay logo visible, igualmente devolvemos solo el producto
    if (logoImg && !logoImg.complete) {
      try { await ensureLoaded(logoImg); } catch (_) {}
    }

    // Canvas del tamaño real del producto
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    const productW = baseImg.naturalWidth || baseImg.width;
    const productH = baseImg.naturalHeight || baseImg.height;
    canvas.width  = productW;
    canvas.height = productH;

    // Dibujar base
    ctx.drawImage(baseImg, 0, 0, productW, productH);

    // Dibujar logo si existe y está visible
    if (logoImg && logoImg.src && window.getComputedStyle(logoImg).display !== 'none' && logoImg.width > 0) {
      // Medimos posición en pantalla y la referenciamos al tamaño real del producto
      const baseRect = baseImg.getBoundingClientRect();
      const logoRect = logoImg.getBoundingClientRect();
      const ratio = productW / baseRect.width; // px reales / px mostrados

      const drawW = Math.max(1, Math.round(logoRect.width * ratio));
      const drawH = Math.max(1, Math.round(logoRect.height * ratio));
      const drawX = Math.round((logoRect.left - baseRect.left) * ratio);
      const drawY = Math.round((logoRect.top  - baseRect.top ) * ratio);

      // Rotación (en grados) desde el input
      const deg = rotationInput ? parseFloat(rotationInput.value || "0") : 0;
      const rad = deg * Math.PI / 180;

      // Rotamos alrededor del centro del logo
      const cx = drawX + drawW / 2;
      const cy = drawY + drawH / 2;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rad);
      ctx.drawImage(logoImg, -drawW / 2, -drawH / 2, drawW, drawH);
      ctx.restore();
    }

    return canvas.toDataURL('image/png'); // data:image/png;base64,....
  }

  // --- Descargar PNG ---
  async function onDownloadPNG(ev) {
    ev.preventDefault();
    try {
      const dataURL = await buildCompositeDataURL();

      // iOS: abrir en pestaña nueva para "Visualización" inmediata
      if (isIOS()) {
        window.open(dataURL, '_blank');
        return;
      }

      // Otros navegadores: forzamos descarga
      const a = document.createElement('a');
      a.href = dataURL;
      a.download = 'personalizacion.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      alert('No se pudo generar el PNG: ' + (e && e.message ? e.message : 'Error desconocido'));
    }
  }

  // --- Añadir al carrito con personalización ---
  async function onAddToCart(ev) {
    ev.preventDefault();

    const variantId = parseInt($('#spw_variant_id')?.value || "0", 10);
    const qty       = parseInt($('#spw_qty')?.value || "1", 10);
    const tech      = getCheckedValue('spw_tech');
    const svgColor  = getCheckedValue('spw_svg_color');
    const notes     = ($('#spw_notes')?.value || '').trim();

    if (!variantId || qty <= 0) {
      alert('Faltan datos: variante o cantidad.');
      return;
    }

    // PNG base64 (sin prefijo)
    let png_b64 = '';
    try {
      const dataURL = await buildCompositeDataURL();
      png_b64 = (dataURL.split(',')[1] || '').trim();
    } catch (e) {
      // Si falla la composición, seguimos sin PNG pero avisamos
      console.warn('PNG no disponible, se añade la línea sin adjunto:', e);
    }

    try {
      const res = await fetch('/spw/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          variant_id: variantId,
          qty: qty,
          tech: tech,
          svg_color: svgColor,
          notes: notes,
          png_b64: png_b64,
        }),
        credentials: 'same-origin',
      });

      // El controlador devuelve JSON
      const payload = await res.json().catch(() => ({}));
      if (!payload || payload.ok !== true) {
        const msg = (payload && payload.message) ? payload.message : 'No se pudo añadir al carrito.';
        alert(msg);
        return;
      }
      // Redirigir al carrito
      window.location.href = payload.cart_url || '/shop/cart';
    } catch (e) {
      alert('Error de red al añadir al carrito.');
    }
  }

  // --- Bind ---
  function bind() {
    const btnDownload = $('#spw_btn_download');
    const btnAddCart  = $('#spw_btn_add_cart');

    if (btnDownload && !btnDownload._spwBound) {
      btnDownload.addEventListener('click', onDownloadPNG);
      btnDownload._spwBound = true;
    }
    if (btnAddCart && !btnAddCart._spwBound) {
      btnAddCart.addEventListener('click', onAddToCart);
      btnAddCart._spwBound = true;
    }
  }

  document.addEventListener('DOMContentLoaded', bind);
  // Por si Odoo vuelve a inyectar contenido dinámicamente
  document.addEventListener('o_page_loaded', bind);
})();