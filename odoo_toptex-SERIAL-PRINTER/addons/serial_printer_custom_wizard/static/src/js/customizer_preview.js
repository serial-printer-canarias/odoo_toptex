/**
 * serial_printer_custom_wizard/static/src/js/customizer_preview.js
 * Vista de personalización – previsualización en <canvas>
 * Sin dependencias de Odoo. Carga y manipula un logo sobre la imagen base.
 */
(function () {
  const $ = (sel, root = document) => root.querySelector(sel);

  const canvas   = $('#spw_canvas');
  if (!canvas) return; // No estamos en la página de personalización

  const ctx      = canvas.getContext('2d');
  const baseImgEl = $('#spw_base_img') || $('#spw_base_holder img') || $('.spw-base img');

  // Controles (si faltan, el código sigue funcionando con valores por defecto)
  const fileInput = $('#spw_file') || $('input[type="file"][name="spw_file"]');
  const sizeInput = $('#spw_size') || $('input[type="range"][name="spw_size"]');
  const rotInput  = $('#spw_rotate') || $('input[type="range"][name="spw_rotate"]');
  const posXInput = $('#spw_pos_x') || $('input[type="range"][name="spw_pos_x"]');
  const posYInput = $('#spw_pos_y') || $('input[type="range"][name="spw_pos_y"]');

  const S = {
    base: null,     // Image()
    logo: null,     // Image() del archivo subido
    scale: sizeInput ? Number(sizeInput.value)/100 : 0.25,
    rot:   rotInput ? Number(rotInput.value) * Math.PI/180 : 0,
    x:     posXInput ? Number(posXInput.value) : 0,
    y:     posYInput ? Number(posYInput.value) : 0,
    dragging: false,
    dragOffX: 0,
    dragOffY: 0,
  };

  function fitCanvasToBase() {
    if (!S.base) return;
    const r = baseImgEl.getBoundingClientRect();
    const w = Math.round(r.width  || S.base.naturalWidth);
    const h = Math.round(r.height || S.base.naturalHeight);
    canvas.width = w;
    canvas.height = h;
  }

  function render() {
    if (!S.base) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(S.base, 0, 0, canvas.width, canvas.height);
    if (S.logo) {
      const w = S.logo.naturalWidth  * S.scale;
      const h = S.logo.naturalHeight * S.scale;
      ctx.save();
      ctx.translate(S.x, S.y);
      ctx.rotate(S.rot);
      ctx.drawImage(S.logo, -w/2, -h/2, w, h);
      ctx.restore();
    }
  }

  function loadLogoFromFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        S.logo = img;
        // Valores por defecto: centrado y tamaño relativo al lienzo
        S.x = canvas.width / 2;
        S.y = canvas.height / 2;
        if (sizeInput && !sizeInput.dataset.userTouched) {
          const rel = Math.min(0.5, (canvas.width * 0.25) / img.naturalWidth);
          S.scale = rel;
          sizeInput.value = Math.round(S.scale * 100);
        }
        render();
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  }

  // Sliders
  if (sizeInput) sizeInput.addEventListener('input', (e) => {
    sizeInput.dataset.userTouched = '1';
    S.scale = Math.max(0.05, (Number(e.target.value) || 0) / 100);
    render();
  });

  if (rotInput) rotInput.addEventListener('input', (e) => {
    S.rot = (Number(e.target.value) || 0) * Math.PI / 180;
    render();
  });

  if (posXInput) posXInput.addEventListener('input', (e) => {
    S.x = Number(e.target.value) || 0;
    render();
  });

  if (posYInput) posYInput.addEventListener('input', (e) => {
    S.y = Number(e.target.value) || 0;
    render();
  });

  // Subida de archivo
  if (fileInput) {
    fileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      loadLogoFromFile(f);
    });
  }

  // Arrastrar el logo encima del canvas (puntero / táctil)
  function pointFromEvent(ev) {
    const rect = canvas.getBoundingClientRect();
    const t = ev.touches ? ev.touches[0] : ev;
    return { x: t.clientX - rect.left, y: t.clientY - rect.top };
  }

  canvas.addEventListener('pointerdown', (ev) => {
    if (!S.logo) return;
    const p = pointFromEvent(ev);
    const w = S.logo.naturalWidth  * S.scale;
    const h = S.logo.naturalHeight * S.scale;

    // Invertir rotación para testear colisión
    const cos = Math.cos(-S.rot), sin = Math.sin(-S.rot);
    const dx = p.x - S.x, dy = p.y - S.y;
    const rx = dx * cos - dy * sin;
    const ry = dx * sin + dy * cos;

    if (rx >= -w/2 && rx <= w/2 && ry >= -h/2 && ry <= h/2) {
      S.dragging = true;
      S.dragOffX = rx;
      S.dragOffY = ry;
      canvas.setPointerCapture(ev.pointerId);
    }
  });

  canvas.addEventListener('pointermove', (ev) => {
    if (!S.dragging) return;
    const p = pointFromEvent(ev);
    const cos = Math.cos(S.rot), sin = Math.sin(S.rot);
    S.x = p.x - (S.dragOffX * cos - S.dragOffY * sin);
    S.y = p.y - (S.dragOffX * sin + S.dragOffY * cos);
    if (posXInput) posXInput.value = Math.round(S.x);
    if (posYInput) posYInput.value = Math.round(S.y);
    render();
  });

  function endDrag(ev) {
    if (!S.dragging) return;
    S.dragging = false;
    try { canvas.releasePointerCapture(ev.pointerId); } catch (_) {}
  }
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('pointerleave', endDrag);

  // Inicialización
  function init() {
    if (!baseImgEl) return;
    const src = baseImgEl.getAttribute('src');
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      S.base = img;
      fitCanvasToBase();
      if (posXInput) posXInput.max = canvas.width;
      if (posYInput) posYInput.max = canvas.height;
      if (!S.x) S.x = canvas.width / 2;
      if (!S.y) S.y = canvas.height / 2;
      render();
    };
    img.src = src;
  }

  window.addEventListener('resize', () => {
    if (S.base) {
      fitCanvasToBase();
      render();
    }
  });

  init();
})();