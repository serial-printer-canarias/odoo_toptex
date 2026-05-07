/** SPW – Opciones: ocultar botones antiguos en el customizer y la paleta en carrito (versión segura) */
odoo.define('serial_printer_custom_wizard.spw_options', [], function () {
  'use strict';

  function ready(cb){
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', cb, { once: true });
    } else cb();
  }

  function isCustomizer(){
    return /\/spw\/customizer\b/.test(location.pathname);
  }
  function isCart(){
    return !!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines');
  }

  /* ---- 1) Customizer: ocultar SOLO la fila de “puntos” antigua ---- */
  function hideLegacyColorDots(){
    if (!isCustomizer()) return;

    // a) Clases conocidas (no destructivo)
    const known = document.querySelectorAll(
      '.spw-quick-colors, .spw_quick_colors, .spw-old-color-buttons, .spw-color-shortcuts'
    );
    if (known.length) {
      known.forEach(el => el.style.display = 'none');
      return;
    }

    // b) Heurística MUY defensiva: cerca del texto “Se aplica solo a logos SVG”
    const label = Array.from(document.querySelectorAll('*'))
      .find(el => /Se aplica\s+solo\s+a\s+logos\s+SVG/i.test(el.textContent || ''));
    if (!label) return;

    // Busca un hermano inmediato que sea una fila de “píldoras” pequeñas
    const container =
      label.nextElementSibling ||
      label.parentElement?.querySelector(':scope > div, :scope > ul');

    if (!container) return;

    // Validar: 3–10 elementos redondos y pequeños
    const items = Array.from(container.children).filter(ch => {
      const cs = getComputedStyle(ch);
      const w = ch.offsetWidth, h = ch.offsetHeight;
      const br = parseFloat(cs.borderRadius) || 0;
      const tagOk = /^(BUTTON|SPAN|A|LI)$/.test(ch.tagName);
      const sizeOk = w > 8 && w <= 28 && h > 8 && h <= 28 && Math.abs(w - h) <= 6;
      const roundOk = br >= Math.min(w, h) / 2 - 2;
      return tagOk && sizeOk && roundOk;
    });

    if (items.length >= 3 && items.length <= 10) {
      container.style.display = 'none'; // no eliminar nodos
    }
  }

  /* ---- 2) Carrito: ocultar cualquier paleta de colores si se coló ---- */
  function hidePaletteInCart(){
    if (!isCart()) return;
    const style = document.createElement('style');
    style.textContent = `
      #o_cart .spw-color-palette,
      #o_cart [data-spw="palette"],
      #o_cart .spw_palette,
      #o_cart .spw-colors,
      #o_cart .spw-colors-grid,
      .o_wsale_cart_summary .spw-color-palette,
      .o_wsale_cart_summary [data-spw="palette"],
      .o_wsale_cart_summary .spw_palette,
      .o_wsale_cart_summary .spw-colors,
      .o_wsale_cart_summary .spw-colors-grid {
        display: none !important;
      }
    `;
    document.head.appendChild(style);
  }

  function boot(){
    hideLegacyColorDots();
    hidePaletteInCart();
  }

  ready(boot);
});