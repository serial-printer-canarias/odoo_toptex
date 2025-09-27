/* SP – Cart stock banner (solo UI) */
(function () {
  'use strict';

  const $ = (s, c = document) => c.querySelector(s);

  function isCartPage() {
    const p = location.pathname + location.search;
    return /\/shop\/cart(?:$|[?#/])/.test(p);
  }

  // ¿Hay avisos propios de Odoo sobre stock?
  function hasOdooStockWarnings(root = document) {
    return root.querySelector(
      [
        '.css_not_available_msg',           // warning típico de Odoo
        '.o_wsale_cart .alert-warning',
        '.oe_website_sale .alert-warning',
        '.js_cart_lines .text-warning',
        '.o_wsale_cart .text-warning'
      ].join(',')
    );
  }

  function placeBanner() {
    if (document.getElementById('sp-cart-stock-banner')) return;
    const host =
      $('.o_wsale_cart') ||
      $('.oe_website_sale') ||
      $('main .container') ||
      document.body;

    const div = document.createElement('div');
    div.id = 'sp-cart-stock-banner';
    div.className = 'alert alert-danger sp-cart-stock-banner';
    div.role = 'alert';
    div.textContent = 'Pendiente revisión de stock o próximas llegadas.';
    host.firstElementChild
      ? host.insertBefore(div, host.firstElementChild)
      : host.appendChild(div);
  }

  function removeBanner() {
    const b = document.getElementById('sp-cart-stock-banner');
    if (b) b.remove();
  }

  function run() {
    if (!isCartPage()) return;
    hasOdooStockWarnings() ? placeBanner() : removeBanner();
  }

  // Arranque
  (document.readyState === 'loading')
    ? document.addEventListener('DOMContentLoaded', run)
    : run();

  // Re-evaluar cuando el carrito cambie dinámicamente (qty +/-)
  const mo = new MutationObserver(() => run());
  mo.observe(document.documentElement, { subtree: true, childList: true, attributes: true });
})();