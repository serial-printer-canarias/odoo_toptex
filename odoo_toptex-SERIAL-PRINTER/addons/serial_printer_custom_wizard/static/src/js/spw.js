odoo.define('serial_printer_custom_wizard/js/spw', [], function (require) {
  'use strict';

  function pickNameCell(row) {
    if (!row) return null;
    return (
      row.querySelector('.td-product_name') ||
      row.querySelector('.o_wsale_product_information') ||
      row.querySelector('.o_wsale_cart_item_info') ||
      row.querySelector('.o_cart_product_information') ||
      row.querySelector('.o_wsale_product_info') ||
      row
    );
  }

  function injectPreview() {
    if (!/\/shop\/cart/.test(location.pathname)) return;

    const dataUrl = sessionStorage.getItem('spw_last_png');
    if (!dataUrl) return;

    const lineId = sessionStorage.getItem('spw_last_line_id');   // ← NUEVO
    let container = null;

    if (lineId) {
      const row = document.querySelector('[data-line-id="' + lineId + '"]');
      container = pickNameCell(row);
    }

    // Fallback: primera celda de nombre del carrito
    if (!container) {
      container =
        document.querySelector('.js_cart_lines .td-product_name') ||
        document.querySelector('.td-product_name') ||
        document.querySelector('.css_description') ||
        document.querySelector('.oe_cart');
    }

    if (!container || container.querySelector('.spw-cart-preview')) return;

    const img = document.createElement('img');
    img.src = dataUrl;
    img.className = 'spw-cart-preview';
    img.style.maxWidth = '160px';
    img.style.border = '1px solid #eee';
    img.style.marginTop = '8px';
    container.appendChild(img);
  }

  document.addEventListener('DOMContentLoaded', function () {
    injectPreview();
    // Reinyectar si el DOM del carrito se recompone
    new MutationObserver(injectPreview).observe(document.body, { childList: true, subtree: true });
  });
});