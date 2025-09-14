/** SPW - Previsualización de logo sobre la imagen del producto */
(function () {
  function qs(id) { return document.getElementById(id); }

  function initPreview() {
    const fileInput = qs('spw_logo_input');
    const canvas = qs('spw_canvas');
    const preview = qs('spw_logo_preview');

    if (!fileInput || !canvas || !preview) return;

    // Asegurar estilos base
    canvas.style.position = canvas.style.position || 'relative';
    preview.style.position = 'absolute';
    preview.style.left = '50%';
    preview.style.top = '60%';
    preview.style.transform = 'translate(-50%, -50%)';
    preview.style.pointerEvents = 'none';
    preview.style.zIndex = '5';
    preview.style.maxWidth = '80%';
    preview.style.maxHeight = '80%';
    preview.style.opacity = '1';

    function showPreviewFromFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function (e) {
        preview.src = e.target.result;   // DataURL (sirve PNG/JPG/SVG)
        preview.classList.remove('d-none');
      };
      reader.readAsDataURL(file);
    }

    fileInput.addEventListener('change', function (ev) {
      const f = ev.target.files && ev.target.files[0];
      showPreviewFromFile(f);
    });

    // Controles opcionales si existen (no obligatorios)
    const size = qs('spw_size');
    const posX = qs('spw_pos_x');
    const posY = qs('spw_pos_y');
    const rot  = qs('spw_rotation');

    function updateTransform() {
      if (!preview) return;
      const s = size ? (Number(size.value || 100) / 100) : 1;
      const x = posX ? Number(posX.value || 0) : 0;
      const y = posY ? Number(posY.value || 0) : 0;
      const r = rot  ? Number(rot.value  || 0) : 0;
      preview.style.transform =
        `translate(-50%, -50%) translate(${x}%, ${y}%) rotate(${r}deg) scale(${s})`;
    }

    [size, posX, posY, rot].forEach(ctrl => {
      if (ctrl) ctrl.addEventListener('input', updateTransform);
    });

    // Reset si existe window.spwReset
    window.spwReset = function () {
      preview.classList.add('d-none');
      preview.removeAttribute('src');
      if (size) size.value = 100;
      if (posX) posX.value = 0;
      if (posY) posY.value = 10;
      if (rot)  rot.value  = 0;
      updateTransform();
    };

    updateTransform();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPreview);
  } else {
    initPreview();
  }
})();

// === SPW: DESCARGA PNG + AÑADIR AL CARRITO (Solo añade; no toca lo demás) ===
(function () {
  function $(id) { return document.getElementById(id); }

  // Usa html2canvas (rápido con scale=2) y devuelve base64 (sin prefijo) para el servidor
  async function spwCanvasToBase64() {
    const node = $('spw_canvas');
    if (!node) throw new Error('No se encontró el canvas');

    const canvas = await html2canvas(node, {
      backgroundColor: null,
      scale: 2,
      useCORS: true,
      logging: false,
    });
    return canvas.toDataURL('image/png').split(',')[1];
  }

  // Descarga local (fuerza descarga en iOS/Android/desktop)
  async function onDownloadPng(ev) {
    ev.preventDefault();
    const btn = ev.currentTarget;
    btn.disabled = true;
    try {
      const node = $('spw_canvas');
      const canvas = await html2canvas(node, { backgroundColor: null, scale: 2, useCORS: true });
      const url = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url;
      a.download = 'personalizacion.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      alert('No se pudo descargar el PNG.\n' + (e && e.message ? e.message : e));
    } finally {
      btn.disabled = false;
    }
  }

  // Envío al carrito
  async function onAddToCart(ev) {
    ev.preventDefault();
    const btn = ev.currentTarget;
    btn.disabled = true;
    try {
      const variantId = parseInt(($('spw_variant_id') && $('spw_variant_id').value) || '0', 10);
      const qty = parseInt(($('spw_qty') && $('spw_qty').value) || '1', 10);
      const notes = ($('spw_notes') && $('spw_notes').value) || '';
      const techEl = document.querySelector('input[name="spw_tech"]:checked');
      const colorEl = document.querySelector('input[name="spw_svg_color"]:checked');
      const tech = techEl ? techEl.value : '';
      const svgColor = colorEl ? colorEl.value : '';

      if (!variantId) {
        alert('No se encontró la variante. Vuelve al producto y entra de nuevo.');
        return;
      }

      const png_b64 = await spwCanvasToBase64();

      const res = await fetch('/spw/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          variant_id: variantId,
          qty: qty,
          tech: tech,
          svg_color: svgColor,
          notes: notes,
          png_b64: png_b64,
        }),
      });

      if (!res.ok) {
        const t = await res.text();
        throw new Error('HTTP ' + res.status + ' ' + t);
      }
      const data = await res.json();
      if (!data.ok) throw new Error(data.message || 'Error desconocido');

      window.location.href = data.cart_url || '/shop/cart';
    } catch (e) {
      alert('No se pudo añadir al carrito.\n' + (e && e.message ? e.message : e));
    } finally {
      btn.disabled = false;
    }
  }

  // Enlazar botones sin romper nada de lo existente
  window.addEventListener('DOMContentLoaded', function () {
    const dl = $('spw_download_png');
    if (dl && !dl.__spw_bound) { dl.addEventListener('click', onDownloadPng); dl.__spw_bound = true; }
    const add = $('spw_add_to_cart');
    if (add && !add.__spw_bound) { add.addEventListener('click', onAddToCart); add.__spw_bound = true; }
  });
})();