odoo.define('serial_printer_custom_wizard/js/spw', [], function (require) {
  'use strict';

  function findRowByProductId(pid) {
    if (!pid) return null;

    // Busca el elemento de la línea según distintos temas/plantillas
    const probes = [
      '.js_cart_lines [data-product-id="%ID%"]',
      '.js_cart_lines .js_quantity[data-product-id="%ID%"]',
      '.js_cart_lines input[name="product_id"][value="%ID%"]',
      '[data-product-id="%ID%"]',
      'input[name="product_id"][value="%ID%"]',
    ];

    for (const p of probes) {
      const el = document.querySelector(p.replace('%ID%', pid));
      if (el) {
        const row =
          el.closest('[data-line-id]') ||
          el.closest('tr') ||
          el.closest('.o_cart_line') ||
          el.closest('.oe_website_sale') ||
          el.closest('div');
        if (row) return row;
      }
    }
    return null;
  }

  function getNameCell(row) {
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

    const pid = sessionStorage.getItem('spw_last_product_id');
    let container = null;

    if (pid) {
      const row = findRowByProductId(pid);
      container = getNameCell(row);
    }

    // Fallback: primera celda de nombre
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
    // Si el DOM del carrito se repinta, reinyecta
    const mo = new MutationObserver(injectPreview);
    mo.observe(document.body, { childList: true, subtree: true });
  });
});