odoo.define('serial_printer_custom_wizard.personalizar_preview', function (require) {
  'use strict';

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    const base = document.getElementById('spw-base');
    const logo = document.getElementById('spw-logo');
    const input = document.getElementById('spw_logo_input');
    const posSel = document.getElementById('posicion');
    const thumbs = document.querySelectorAll('.spw-thumb');
    const variantInput = document.getElementById('variant_id');

    // Logo preview
    if (input) {
      input.addEventListener('change', function (ev) {
        const f = ev.target.files && ev.target.files[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = () => {
          logo.src = reader.result;
          logo.style.display = 'block';
          applyPos();
        };
        reader.readAsDataURL(f);
      });
    }

    // Posicionamiento simple
    function applyPos() {
      if (!logo) return;
      const v = (posSel && posSel.value) || 'pecho';
      const map = {
        pecho:            { top: '22%', left: '35%', width: '30%' },
        espalda:          { top: '38%', left: '30%', width: '40%' },
        manga_izquierda:  { top: '25%', left: '18%', width: '16%' },
        manga_derecha:    { top: '25%', left: '66%', width: '16%' },
      };
      const s = map[v] || map.pecho;
      Object.assign(logo.style, { top: s.top, left: s.left, width: s.width });
    }
    if (posSel) posSel.addEventListener('change', applyPos);

    // Cambiar imagen base al pulsar miniatura de variante
    thumbs.forEach(function (t) {
      t.addEventListener('click', function () {
        const vid = t.dataset.variant_id;
        if (vid && base) {
          base.src = `/web/image/product.product/${vid}/image_1920`;
          if (variantInput) variantInput.value = vid;
        }
      });
    });

    // Primera aplicación por si ya hay valor
    applyPos();
  });
});