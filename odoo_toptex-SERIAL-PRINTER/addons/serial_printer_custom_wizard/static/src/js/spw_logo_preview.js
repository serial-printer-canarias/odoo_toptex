/** @odoo-module **/

odoo.define('serial_printer_custom_wizard.spw_logo_preview', function (require) {
  'use strict';

  function onCustomizerPage() {
    return window.location.pathname.indexOf('/spw/customize/') === 0;
  }

  function init() {
    if (!onCustomizerPage()) return;

    const logoInput = document.getElementById('spw_logo_input');
    const logoImg   = document.getElementById('spw_logo_preview');
    const sizeR     = document.getElementById('spw_size');
    const posXR     = document.getElementById('spw_pos_x');
    const posYR     = document.getElementById('spw_pos_y');
    const rotR      = document.getElementById('spw_rotation');

    if (!logoInput || !logoImg) return;

    // Estado
    let size = parseInt(sizeR ? sizeR.value : 100, 10);   // porcentaje del ancho base
    let posX = parseInt(posXR ? posXR.value : 0, 10);     // porcentaje extra respecto al centro
    let posY = parseInt(posYR ? posYR.value : 10, 10);
    let rot  = parseInt(rotR ? rotR.value  : 0, 10);

    function apply() {
      // ancho como % para que sea intuitivo
      logoImg.style.width = size + '%';
      // centrado + offsets porcentuales
      logoImg.style.left = (50 + posX) + '%';
      logoImg.style.top  = (50 + posY) + '%';
      logoImg.style.transform = `translate(-50%, -50%) rotate(${rot}deg)`;
    }

    // Exponer reset (usado por el botón Reset de la vista)
    window.spwReset = function () {
      size = 100; posX = 0; posY = 10; rot = 0;
      if (sizeR) sizeR.value = size;
      if (posXR) posXR.value = posX;
      if (posYR) posYR.value = posY;
      if (rotR)  rotR.value  = rot;
      apply();
    };

    // Cargar imagen local (PNG/JPG/SVG) como DataURL
    logoInput.addEventListener('change', function () {
      const file = this.files && this.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function (e) {
        logoImg.src = e.target.result;   // DataURL
        logoImg.classList.remove('d-none');
        apply();
      };
      reader.readAsDataURL(file);
    });

    // Sliders
    if (sizeR) sizeR.addEventListener('input', (e) => { size = parseInt(e.target.value || '100', 10); apply(); });
    if (posXR) posXR.addEventListener('input', (e) => { posX = parseInt(e.target.value || '0', 10);   apply(); });
    if (posYR) posYR.addEventListener('input', (e) => { posY = parseInt(e.target.value || '10', 10);  apply(); });
    if (rotR)  rotR.addEventListener('input',  (e) => { rot  = parseInt(e.target.value || '0', 10);   apply(); });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
});