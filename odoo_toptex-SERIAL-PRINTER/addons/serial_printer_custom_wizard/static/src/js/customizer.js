/** addons/serial_printer_custom_wizard/static/src/js/customizer.js
 * Previsualización del logo sobre la imagen (sin tocar nada más).
 * Seguro en cualquier página: sólo actúa si existe #spw_canvas.
 */
(function () {
  'use strict';

  function qs(sel) { return document.querySelector(sel); }

  function init() {
    const canvas = qs('#spw_canvas');
    if (!canvas) return; // No estamos en la página del customizer

    const logoInput = qs('#spw_logo_input');
    const logoImg   = qs('#spw_logo_preview');
    const sizeEl    = qs('#spw_size');
    const posXEl    = qs('#spw_pos_x');
    const posYEl    = qs('#spw_pos_y');
    const rotEl     = qs('#spw_rotation');

    // Estado inicial
    const state = {
      widthPct: parseInt(sizeEl?.value || '100', 10), // porcentaje respecto al ancho del lienzo
      dxPct: parseInt(posXEl?.value || '0', 10),      // -50 .. 50
      dyPct: parseInt(posYEl?.value || '10', 10),     // -50 .. 50
      rotDeg: parseInt(rotEl?.value || '0', 10),
    };

    function applyTransform() {
      if (!logoImg) return;
      // Base: centrado (-50%, -50%). Offset añadiendo dx/dy en porcentaje relativo al canvas
      const left = 50 + state.dxPct; // %
      const top  = 50 + state.dyPct; // %
      logoImg.style.left = left + '%';
      logoImg.style.top  = top + '%';

      // Ancho relativo al lienzo
      logoImg.style.width = state.widthPct + '%';

      // Rotación alrededor del centro del logo
      logoImg.style.transform = 'translate(-50%, -50%) rotate(' + state.rotDeg + 'deg)';
      logoImg.style.opacity = '1';
    }

    function reset() {
      if (sizeEl) sizeEl.value = '100';
      if (posXEl) posXEl.value = '0';
      if (posYEl) posYEl.value = '10';
      if (rotEl)  rotEl.value  = '0';
      state.widthPct = 100;
      state.dxPct = 0;
      state.dyPct = 10;
      state.rotDeg = 0;
      applyTransform();
    }

    // Exponer reset para el botón (ya usado en la vista)
    window.spwReset = reset;

    // Controles
    if (sizeEl)  sizeEl.addEventListener('input',  () => { state.widthPct = parseInt(sizeEl.value || '100', 10); applyTransform(); });
    if (posXEl)  posXEl.addEventListener('input',  () => { state.dxPct    = parseInt(posXEl.value || '0', 10);   applyTransform(); });
    if (posYEl)  posYEl.addEventListener('input',  () => { state.dyPct    = parseInt(posYEl.value || '10', 10);  applyTransform(); });
    if (rotEl)   rotEl.addEventListener('input',   () => { state.rotDeg   = parseInt(rotEl.value || '0', 10);    applyTransform(); });

    // Carga de logo
    if (logoInput && logoImg) {
      logoInput.addEventListener('change', (ev) => {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;

        // Validación tamaño (10MB)
        if (file.size > 10 * 1024 * 1024) {
          alert('El archivo supera 10MB.');
          return;
        }
        const mime = (file.type || '').toLowerCase();
        const isImage = mime.startsWith('image/');
        if (!isImage) {
          alert('Formato no soportado. Usa PNG, JPG o SVG.');
          return;
        }

        // Mostrar rápidamente con ObjectURL (va bien para PNG/JPG/SVG)
        try {
          const url = URL.createObjectURL(file);
          logoImg.src = url;
          logoImg.classList.remove('d-none');
          applyTransform();
        } catch (e) {
          // Fallback FileReader
          const reader = new FileReader();
          reader.onload = function (e2) {
            logoImg.src = e2.target.result;
            logoImg.classList.remove('d-none');
            applyTransform();
          };
          reader.readAsDataURL(file);
        }
      });
    }

    // Primera aplicación por si hay valores por defecto
    applyTransform();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();