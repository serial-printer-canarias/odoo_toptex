/* Previsualización del logo sobre la imagen del producto */
(function () {
  'use strict';
  function $(s){ return document.querySelector(s); }

  function init(){
    const canvas = $('#spw_canvas');
    if (!canvas) return;

    const logoInput = $('#spw_logo_input');     // <input type="file" ... id="spw_logo_input">
    const logoImg   = $('#spw_logo_preview');   // <img id="spw_logo_preview">
    const sizeEl    = $('#spw_size');
    const posXEl    = $('#spw_pos_x');
    const posYEl    = $('#spw_pos_y');
    const rotEl     = $('#spw_rotation');

    const state = {
      widthPct: parseInt((sizeEl && sizeEl.value) || '100', 10),
      dxPct:    parseInt((posXEl && posXEl.value) || '0',   10),
      dyPct:    parseInt((posYEl && posYEl.value) || '10',  10),
      rotDeg:   parseInt((rotEl  && rotEl.value)  || '0',   10),
    };

    function applyTransform(){
      if (!logoImg) return;
      logoImg.style.position = 'absolute';
      logoImg.style.left     = (50 + state.dxPct) + '%';
      logoImg.style.top      = (50 + state.dyPct) + '%';
      logoImg.style.width    = state.widthPct + '%';
      logoImg.style.transform= 'translate(-50%, -50%) rotate(' + state.rotDeg + 'deg)';
      logoImg.style.zIndex   = '999';
      logoImg.style.opacity  = '1';
      logoImg.classList.remove('d-none');
    }

    // Controles
    if (sizeEl) sizeEl.addEventListener('input', () => { state.widthPct = parseInt(sizeEl.value || '100', 10); applyTransform(); });
    if (posXEl) posXEl.addEventListener('input', () => { state.dxPct    = parseInt(posXEl.value || '0',   10); applyTransform(); });
    if (posYEl) posYEl.addEventListener('input', () => { state.dyPct    = parseInt(posYEl.value || '10',  10); applyTransform(); });
    if (rotEl)  rotEl.addEventListener('input', () => { state.rotDeg   = parseInt(rotEl.value  || '0',   10); applyTransform(); });

    // Subida de logo (siempre FileReader para máxima compatibilidad)
    if (logoInput && logoImg) {
      logoInput.addEventListener('change', (ev) => {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;

        if (file.size > 10 * 1024 * 1024) { alert('El archivo supera 10MB.'); return; }
        const mime = (file.type || '').toLowerCase();
        if (!mime.startsWith('image/')) { alert('Formato no soportado. Usa PNG, JPG o SVG.'); return; }

        const reader = new FileReader();
        reader.onload = (e) => {
          logoImg.src = e.target.result;        // dataURL
          logoImg.removeAttribute('loading');
          logoImg.decoding = 'sync';
          applyTransform();
          try { logoImg.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch(e) {}
        };
        reader.readAsDataURL(file);
      });
    }

    applyTransform();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();