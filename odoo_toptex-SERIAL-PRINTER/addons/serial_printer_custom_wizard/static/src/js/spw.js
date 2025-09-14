/** addons/serial_printer_custom_wizard/static/src/js/spw.js */
(function () {
  const $ = (sel) => document.querySelector(sel);

  const state = {
    fileIsSvg: false,
    svgText: '',
    svgColor: '#000000',
    size: 100,
    posX: 0,
    posY: 10,
    rotation: 0,
  };

  let elBase, elLogo, elInput, elSize, elX, elY, elRot, elQty, elNotes;

  function init() {
    elBase = $('#spw_product_img');
    elLogo = $('#spw_logo_preview');
    elInput = $('#spw_logo_input');
    elSize = $('#spw_size');
    elX = $('#spw_pos_x');
    elY = $('#spw_pos_y');
    elRot = $('#spw_rotation');
    elQty = $('#spw_qty');
    elNotes = $('#spw_notes');

    if (!elBase) return;

    // File input
    elInput && elInput.addEventListener('change', onFile);

    // Sliders
    [elSize, elX, elY, elRot].forEach((r) => {
      r && r.addEventListener('input', () => {
        state.size = parseFloat(elSize.value);
        state.posX = parseFloat(elX.value);
        state.posY = parseFloat(elY.value);
        state.rotation = parseFloat(elRot.value);
        applyTransform();
      });
    });

    // Técnica / color (solo SVG)
    document.querySelectorAll('input[name="spw_svg_color"]').forEach((r) => {
      r.addEventListener('change', () => {
        state.svgColor = r.value;
        if (state.fileIsSvg) recolorSvgAndShow();
      });
    });

    // Reset global
    window.spwReset = () => {
      elSize.value = 100; elX.value = 0; elY.value = 10; elRot.value = 0;
      state.size = 100; state.posX = 0; state.posY = 10; state.rotation = 0;
      applyTransform();
    };

    // Botones
    const btnPng = $('#spw_btn_png');
    const btnCart = $('#spw_btn_add_cart');
    btnPng && btnPng.addEventListener('click', handleDownload);
    btnCart && btnCart.addEventListener('click', handleAddToCart);

    // Valores iniciales
    state.size = parseFloat(elSize.value);
    state.posX = parseFloat(elX.value);
    state.posY = parseFloat(elY.value);
    state.rotation = parseFloat(elRot.value);
    state.svgColor = (document.querySelector('input[name="spw_svg_color"]:checked') || {}).value || '#000000';
    applyTransform();
  }

  // --- Cargar archivo ---
  function onFile(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const isSvg = /image\/svg\+xml|\.svg$/i.test(file.type || file.name);
    state.fileIsSvg = !!isSvg;

    const reader = new FileReader();
    if (isSvg) {
      reader.onload = () => {
        state.svgText = String(reader.result || '');
        recolorSvgAndShow();
      };
      reader.readAsText(file);
    } else {
      reader.onload = () => {
        elLogo.src = reader.result;
        elLogo.classList.remove('d-none');
        elLogo.style.opacity = '1';
        applyTransform();
      };
      reader.readAsDataURL(file);
    }
  }

  // --- Pintar SVG con el color elegido y mostrarlo como dataURL ---
  function recolorSvgAndShow() {
    if (!state.svgText) return;
    let svg = state.svgText;

    // Forzamos fill/stroke al color seleccionado
    // (muy básico, pero suficiente para logos monocromo)
    svg = svg.replace(/fill="[^"]*"/gi, `fill="${state.svgColor}"`);
    svg = svg.replace(/stroke="[^"]*"/gi, `stroke="${state.svgColor}"`);

    const encoded = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    elLogo.src = encoded;
    elLogo.classList.remove('d-none');
    elLogo.style.opacity = '1';
    applyTransform();
  }

  // --- Aplica transformaciones CSS a la previsualización ---
  function applyTransform() {
    if (!elLogo) return;
    const scale = state.size / 100;
    elLogo.style.transform = `translate(-50%, -50%) translate(${state.posX}%, ${state.posY}%) rotate(${state.rotation}deg) scale(${scale})`;
  }

  // --- Componer PNG final desde lo que se ve ---
  function buildCompositePNG() {
    return new Promise((resolve, reject) => {
      try {
        const base = new Image();
        base.crossOrigin = 'anonymous';
        base.onload = () => {
          const baseW = base.naturalWidth || elBase.width;
          const baseH = base.naturalHeight || elBase.height;
          const canvas = document.createElement('canvas');
          canvas.width = baseW;
          canvas.height = baseH;
          const ctx = canvas.getContext('2d');

          // Dibujar base
          ctx.drawImage(base, 0, 0, baseW, baseH);

          // Si no hay logo, devolver sólo la base
          if (!elLogo || !elLogo.src) {
            return resolve(canvas.toDataURL('image/png'));
          }

          // Medidas/posiciones relativas de lo que se ve en pantalla
          const rectBase = elBase.getBoundingClientRect();
          const rectLogo = elLogo.getBoundingClientRect();

          const fracW = rectLogo.width / rectBase.width;
          const fracH = rectLogo.height / rectBase.height;

          const cxFrac = (rectLogo.left - rectBase.left + rectLogo.width / 2) / rectBase.width;
          const cyFrac = (rectLogo.top - rectBase.top + rectLogo.height / 2) / rectBase.height;

          const logoW = fracW * baseW;
          const logoH = fracH * baseH;
          const cx = cxFrac * baseW;
          const cy = cyFrac * baseH;
          const rad = (state.rotation * Math.PI) / 180;

          const logoImg = new Image();
          logoImg.crossOrigin = 'anonymous';
          logoImg.onload = () => {
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(rad);
            ctx.drawImage(logoImg, -logoW / 2, -logoH / 2, logoW, logoH);
            ctx.restore();
            resolve(canvas.toDataURL('image/png'));
          };
          logoImg.onerror = () => resolve(canvas.toDataURL('image/png'));
          logoImg.src = elLogo.src;
        };
        base.onerror = () => reject(new Error('No se pudo cargar la imagen base'));
        base.src = elBase.src;
      } catch (err) {
        reject(err);
      }
    });
  }

  // --- Descargar PNG ---
  async function handleDownload() {
    try {
      const dataUrl = await buildCompositePNG();
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = 'personalizacion.png';
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (e) {
      console.error(e);
      alert('No se pudo generar el PNG.');
    }
  }

  // --- Añadir al carrito con personalización ---
  async function handleAddToCart() {
    const variantId = parseInt($('#spw_variant_id')?.value || 0);
    const qty = parseInt(elQty?.value || '1', 10) || 1;
    const tech = (document.querySelector('input[name="spw_tech"]:checked') || {}).value || '';
    const svgColor = (document.querySelector('input[name="spw_svg_color"]:checked') || {}).value || '';
    const notes = elNotes?.value || '';

    if (!variantId) {
      alert('Falta la variante del producto.');
      return;
    }

    let pngB64 = '';
    try {
      const dataUrl = await buildCompositePNG();
      pngB64 = (dataUrl || '').split(',')[1] || '';
    } catch (e) {
      console.warn('PNG no crítico para el carrito:', e);
    }

    try {
      const resp = await fetch('/spw/add_to_cart', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          variant_id: variantId,
          qty: qty,
          tech: tech,
          svg_color: state.fileIsSvg ? svgColor : '',
          notes: notes,
          png_b64: pngB64,
        }),
      });
      const data = await resp.json();
      if (data && data.ok) {
        window.location.href = data.cart_url || '/shop/cart';
      } else {
        alert((data && data.message) || 'No se pudo añadir al carrito.');
      }
    } catch (e) {
      console.error(e);
      alert('Error de red al añadir al carrito.');
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();