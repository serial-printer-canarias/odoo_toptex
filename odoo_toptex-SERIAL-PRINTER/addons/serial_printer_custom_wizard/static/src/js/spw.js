/** addons/serial_printer_custom_wizard/static/src/js/spw.js */
(function () {
  const byId = (id) => document.getElementById(id);

  const $productImg   = byId('spw_product_img');
  const $logoInput    = byId('spw_logo_input');
  const $logoPreview  = byId('spw_logo_preview');

  const $size   = byId('spw_size');
  const $posX   = byId('spw_pos_x');
  const $posY   = byId('spw_pos_y');
  const $rot    = byId('spw_rotation');

  const $notes  = byId('spw_notes');
  const $addBtn = byId('spw_add_to_cart');
  const $dlBtn  = byId('spw_download_png');

  const $templateId = byId('spw_template_id');
  const $variantId  = byId('spw_variant_id');
  const $palette    = byId('spw_color_palette');

  let rawSVGText = null;       // si el archivo subido es SVG
  let isSVG = false;

  /** Construye la paleta NS-300 si está disponible */
  function buildPalette() {
    if (!$palette || !window.NS300_COLORS) return;
    $palette.innerHTML = '';
    window.NS300_COLORS.forEach((c, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'spw-color-dot';
      btn.title = c.name;
      btn.style.setProperty('--spw-dot', c.hex);
      if (idx === 0) btn.classList.add('is-active');
      btn.addEventListener('click', () => {
        [...$palette.querySelectorAll('.spw-color-dot')].forEach(n => n.classList.remove('is-active'));
        btn.classList.add('is-active');
        if (isSVG && rawSVGText) recolorSVG(c.hex);
      });
      $palette.appendChild(btn);
    });
  }

  /** Carga de logo y previsualización */
  $logoInput && $logoInput.addEventListener('change', async (ev) => {
    const f = ev.target.files && ev.target.files[0];
    if (!f) return;

    const url = URL.createObjectURL(f);

    isSVG = (f.type === 'image/svg+xml') || /\.svg$/i.test(f.name);
    rawSVGText = null;

    if (isSVG) {
      // Leer texto del SVG para poder recolorear
      rawSVGText = await f.text();
      $logoPreview.src = url; // vista rápida
    } else {
      $logoPreview.src = url;
    }

    $logoPreview.classList.remove('d-none');
    $logoPreview.style.opacity = '1';
    applyTransforms();
  });

  /** Aplica transformaciones de sliders al overlay */
  function applyTransforms() {
    const scale = (parseInt($size.value, 10) || 100) / 100; // 1 = 100%
    const x = parseInt($posX.value, 10) || 0;
    const y = parseInt($posY.value, 10) || 0;
    const r = parseInt($rot.value, 10) || 0;

    // Posición respecto al centro 50/60 ya seteados en CSS
    $logoPreview.style.transform =
      `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) rotate(${r}deg) scale(${scale})`;
  }

  [$size, $posX, $posY, $rot].forEach(el => {
    el && el.addEventListener('input', applyTransforms);
  });

  /** Recolorear SVG subido con un hex dado */
  function recolorSVG(hex) {
    // Reemplazo simple de fill/stroke. Si tu SVG trae estilos embebidos más complejos,
    // esto cubre la mayoría de casos.
    let txt = rawSVGText || '';
    // normalizamos (quita fills previos y aplica nuevo)
    txt = txt
      .replace(/fill\s*=\s*["']#[0-9A-Fa-f]{3,8}["']/g, '')
      .replace(/stroke\s*=\s*["']#[0-9A-Fa-f]{3,8}["']/g, '');

    // añade fill por defecto al primer <svg ...>
    txt = txt.replace(/<svg([^>]*)>/i, (m, attrs) => `<svg${attrs} fill="${hex}" stroke="${hex}">`);

    const blob = new Blob([txt], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    $logoPreview.src = url;
  }

  /** Devuelve datos de la UI */
  function readUI() {
    const technique = (document.querySelector('input[name="spw_technique"]:checked') || {}).value || 'Serigrafía';
    // color activo (si hay paleta)
    let color = null;
    const active = $palette && $palette.querySelector('.spw-color-dot.is-active');
    if (active) color = getComputedStyle(active).getPropertyValue('--spw-dot').trim();

    return {
      technique,
      color,
      size: parseInt($size.value, 10) || 100,
      pos_x: parseInt($posX.value, 10) || 0,
      pos_y: parseInt($posY.value, 10) || 10,
      rotation: parseInt($rot.value, 10) || 0,
      notes: ($notes && $notes.value) || '',
    };
  }

  /** Genera un PNG de la composición en un <canvas> */
  async function renderCompositePNG() {
    const baseURL = $productImg.src;
    const logoURL = $logoPreview.src;

    if (!baseURL) throw new Error('Falta imagen del producto');
    if (!logoURL || $logoPreview.classList.contains('d-none')) throw new Error('Falta logo');

    const baseImg = await loadImage(baseURL);
    const logoImg = await loadImage(logoURL);

    const canvas = document.createElement('canvas');
    // Canvas del tamaño visual actual del producto (para que se vea igual que en pantalla)
    const rect = $productImg.getBoundingClientRect();
    const scaleRatio = baseImg.naturalWidth / rect.width; // para convertir px de UI a px reales de imagen

    canvas.width = baseImg.naturalWidth;
    canvas.height = baseImg.naturalHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(baseImg, 0, 0, canvas.width, canvas.height);

    // Calcular posición absoluta del logo en píxeles de la imagen
    const ui = readUI();
    const baseCenterX = rect.width * 0.5;
    const baseCenterY = rect.height * 0.60;

    const posXpx = (ui.pos_x || 0);
    const posYpx = (ui.pos_y || 0);
    const scale = (ui.size || 100) / 100;

    // tamaño del logo en proporción al ancho de la imagen del producto
    const maxLogoW = rect.width * 0.8; // como en CSS
    const drawW_UI = Math.min(logoImg.width, maxLogoW) * scale;
    const drawH_UI = (logoImg.height * drawW_UI) / logoImg.width;

    // centro en UI → a coords imagen
    const drawX = (baseCenterX + posXpx - drawW_UI / 2) * scaleRatio;
    const drawY = (baseCenterY + posYpx - drawH_UI / 2) * scaleRatio;
    const drawW = drawW_UI * scaleRatio;
    const drawH = drawH_UI * scaleRatio;

    // rotación alrededor del centro del logo
    ctx.save();
    ctx.translate(drawX + drawW / 2, drawY + drawH / 2);
    ctx.rotate((ui.rotation || 0) * Math.PI / 180);
    ctx.drawImage(logoImg, -drawW / 2, -drawH / 2, drawW, drawH);
    ctx.restore();

    return canvas.toDataURL('image/png');
  }

  function loadImage(src) {
    return new Promise((res, rej) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.onload = () => res(img);
      img.onerror = rej;
      img.src = src;
    });
  }

  /** Descargar PNG localmente */
  $dlBtn && $dlBtn.addEventListener('click', async () => {
    try {
      const dataURL = await renderCompositePNG();
      const a = document.createElement('a');
      a.href = dataURL;
      a.download = 'personalizacion.png';
      a.click();
    } catch (e) {
      console.error(e);
      alert('Sube un logo para descargar la previsualización.');
    }
  });

  /** Añadir al carrito (guarda PNG + JSON como adjuntos) */
  $addBtn && $addBtn.addEventListener('click', async () => {
    try {
      $addBtn.disabled = true;

      const ui = readUI();
      let composedPng = null;
      try {
        composedPng = await renderCompositePNG();
      } catch (e) {
        // si no hay logo, igualmente permitimos crear línea con notas
        composedPng = null;
      }

      const payload = {
        template_id: parseInt($templateId.value, 10),
        variant_id: $variantId.value ? parseInt($variantId.value, 10) : null,
        qty: 1,
        customization: {
          ...ui,
          preview_png: composedPng,         // dataURL (si hay)
          is_svg: !!isSVG
        }
      };

      const resp = await fetch('/spw/add_to_cart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!resp.ok || !data || !data.ok) throw new Error('No se pudo añadir al carrito');

      // Ir al carrito
      window.location.href = '/shop/cart';
    } catch (e) {
      console.error(e);
      alert('No se pudo añadir al carrito. Revisa que hayas subido un logo.');
    } finally {
      $addBtn.disabled = false;
    }
  });

  /** Reset público (lo usa el botón Reset) */
  window.spwReset = function () {
    if ($logoPreview) {
      $logoPreview.classList.add('d-none');
      $logoPreview.removeAttribute('src');
    }
    $size && ($size.value = 100);
    $posX && ($posX.value = 0);
    $posY && ($posY.value = 10);
    $rot && ($rot.value = 0);
    $notes && ($notes.value = '');
    applyTransforms();
  };

  // init
  buildPalette();
  applyTransforms();
})();