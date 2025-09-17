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

    let container = null;

    // 1) Si tenemos line_id, vamos directos a esa fila
    const lineId = sessionStorage.getItem('spw_last_line_id');
    if (lineId) {
      const row = document.querySelector('[data-line-id="' + lineId + '"]') ||
                  document.querySelector('tr[data-line-id="' + lineId + '"]') ||
                  document.querySelector('div[data-line-id="' + lineId + '"]');
      container = pickNameCell(row);
    }

    // 2) Fallback por product_id si no hay line_id
    if (!container) {
      const pid = sessionStorage.getItem('spw_last_product_id');
      if (pid) {
        const el = document.querySelector('.js_quantity[data-product-id="' + pid + '"]') ||
                   document.querySelector('[data-product-id="' + pid + '"]') ||
                   document.querySelector('input[name="product_id"][value="' + pid + '"]');
        if (el) container = pickNameCell(el.closest('[data-line-id]') || el.closest('tr') || el.closest('div'));
      }
    }

    // 3) Último fallback: primera celda del carrito
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
    new MutationObserver(injectPreview).observe(document.body, { childList: true, subtree: true });
  });
});