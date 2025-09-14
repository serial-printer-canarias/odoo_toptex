/* === SPW PATCH: Descargar PNG + Añadir al carrito === */
(function () {
  const $id = (i) => document.getElementById(i);
  const $qs = (s) => document.querySelector(s);

  function onReady(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn, { once: true });
  }

  function safeBind(el, fn) {
    if (!el) return;
    el.addEventListener('click', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      Promise.resolve().then(fn).catch((err) => {
        // Nunca lanzar errores crudos (evita el error "error.stack.split")
        console.error('[SPW] Acción falló:', err);
      });
    });
  }

  async function spwDownloadPNG() {
    const base = $id('spw_product_img');
    const logo = $id('spw_logo_preview');
    if (!base || !logo || !logo.src) return;

    // Canvas con tamaño visual (lo que ves = lo que descargas)
    const w = base.clientWidth || base.naturalWidth;
    const h = base.clientHeight || Math.round(w * (base.naturalHeight / base.naturalWidth));
    const cvs = document.createElement('canvas');
    cvs.width = w;
    cvs.height = h;
    const ctx = cvs.getContext('2d');

    // Base
    if (!base.complete && base.decode) await base.decode().catch(() => {});
    ctx.drawImage(base, 0, 0, w, h);

    // Posición/dimensión actuales del logo según DOM (coincide con lo que ves)
    const rBase = base.getBoundingClientRect();
    const rLogo = logo.getBoundingClientRect();
    const x = rLogo.left - rBase.left;
    const y = rLogo.top - rBase.top;
    const lw = rLogo.width;
    const lh = rLogo.height;

    // Rotación (si existe el slider)
    const rotDeg = parseFloat(($id('spw_rotation') && $id('spw_rotation').value) || '0');
    const cx = x + lw / 2;
    const cy = y + lh / 2;

    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = logo.src;
    if (!img.complete && img.decode) await img.decode().catch(() => {});

    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((rotDeg * Math.PI) / 180);
    ctx.drawImage(img, -lw / 2, -lh / 2, lw, lh);
    ctx.restore();

    // Descargar
    const a = document.createElement('a');
    a.download = 'personalizacion.png';
    a.href = cvs.toDataURL('image/png');
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  async function spwAddToCart() {
    const variantId = parseInt(($id('spw_variant_id') && $id('spw_variant_id').value) || '0', 10);
    const qty = Math.max(1, parseInt(($id('spw_qty') && $id('spw_qty').value) || '1', 10));
    if (!variantId) {
      console.warn('[SPW] No hay variant_id para carrito');
      return;
    }

    // Intento vía JSON-RPC (sin necesidad de CSRF)
    const payload = { product_id: variantId, add_qty: qty };
    try {
      if (window.ajax && typeof window.ajax.jsonRpc === 'function') {
        await window.ajax.jsonRpc('/shop/cart/update_json', 'call', payload);
      } else {
        // Fallback: fetch JSON (mismo origen)
        await fetch('/shop/cart/update_json', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          credentials: 'same-origin',
        });
      }
      // Ir al carrito
      window.location.href = '/shop/cart';
    } catch (e) {
      console.error('[SPW] add_to_cart error:', e);
    }
  }

  onReady(() => {
    // Botones (enganchamos varios ids por si el markup ya existía con otro nombre)
    const downloadBtn = $id('spw_download_png') || $id('spw_btn_download') || $qs('[data-spw="download"]');
    const cartBtn = $id('spw_add_to_cart') || $id('spw_btn_add_cart') || $qs('[data-spw="add_to_cart"]');

    safeBind(downloadBtn, spwDownloadPNG);
    safeBind(cartBtn, spwAddToCart);

    // Reset (si ya lo tenías implementado como window.spwReset lo reutilizamos)
    const resetBtn = $id('spw_reset');
    safeBind(resetBtn, () => { if (window.spwReset) window.spwReset(); });
  });
})();