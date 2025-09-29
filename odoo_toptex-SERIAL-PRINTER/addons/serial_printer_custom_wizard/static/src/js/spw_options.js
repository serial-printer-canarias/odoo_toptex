/** SPW – limpiar UI de personalización: quitar botones antiguos y ocultar paleta en carrito */
odoo.define('serial_printer_custom_wizard.spw_options', [], function () {
  'use strict';

  function onReady(cb){
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', cb, { once: true });
    } else cb();
  }

  function removeEl(el){ if (el && el.remove) el.remove(); }

  // Quita la fila de “puntos de color” antigua del customizer
  function removeLegacyColorDots(){
    // Solo en la página de personalización
    if (!/\/spw\/customizer\b/.test(location.pathname)) return;

    const root = document.querySelector('.spw_customize, .spw-customizer, .o_main_components-container, main') || document.body;

    // 1) Clases conocidas (si existen en tu tema)
    root.querySelectorAll(
      '.spw-quick-colors, .spw_quick_colors, .spw-old-color-buttons, .spw-color-shortcuts'
    ).forEach(removeEl);

    // 2) Heurística: fila de “píldoras” pequeñas justo bajo el texto “Se aplica solo a logos SVG”
    const label = Array.from(root.querySelectorAll('*'))
      .find(el => /Se aplica\s+solo\s+a\s+logos\s+SVG/i.test(el.textContent || ''));

    if (label) {
      // busca un contenedor cercano con ≥3 botones/esferas pequeñas y elimínalo
      let scope = label.parentElement;
      for (let i = 0; i < 4 && scope; i++) {
        const row = scope.querySelector(':scope > div, :scope > ul, :scope > section');
        if (row) {
          const dots = row.querySelectorAll('button, span, a, li');
          const smallRound = Array.from(dots).filter(d => {
            const cs = getComputedStyle(d);
            const w = d.offsetWidth, h = d.offsetHeight;
            const br = parseFloat(cs.borderRadius) || 0;
            return w && h && w <= 24 && h <= 24 && br >= 10;
          });
          if (smallRound.length >= 3) { row.remove(); break; }
        }
        scope = scope.parentElement;
      }
    }
  }

  // No queremos la paleta en el carrito (solo en customizer)
  function hidePaletteInCart(){
    if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
    document.querySelectorAll('.spw-color-palette, [data-spw="palette"], .spw_palette, .spw-colors, .spw-colors-grid')
      .forEach(removeEl);
  }

  function boot(){
    removeLegacyColorDots();
    hidePaletteInCart();
  }

  onReady(boot);
});