/* SP – Cart stock banner (solo UI, no toca metodología) */
(function () {
  'use strict';

  const $ = (s, c = document) => c.querySelector(s);

  // Detectar si estamos en /shop/cart
  function isCartPage() {
    return /\/shop\/cart(?:$|[?#/])/.test(location.pathname + location.search);
  }

  // Raíz donde insertar el banner (seguro en la mayoría de temas)
  function getCartHost() {
    return (
      $('.o_wsale_cart') ||
      $('.oe_website_sale') ||
      $('main .container') ||
      $('main') ||
      document.body
    );
  }

  // Heurística robusta: ¿hay avisos/alertas de Odoo relacionados con stock?
  function hasOdooStockWarnings(root = document) {
    // 1) Selectores típicos de Odoo/temas (warning/danger en carrito)
    const node =
      root.querySelector(
        [
          '.css_not_available_msg',                    // website_sale_stock clásico
          '.o_wsale_cart .alert-warning',
          '.o_wsale_cart .alert-danger',
          '.oe_website_sale .alert-warning',
          '.oe_website_sale .alert-danger',
          '.js_cart_lines .text-warning',
          '.js_cart_lines .text-danger',
          '.o_website_sale_stock_warning',             // variantes en temas
          '.o_wsale_cart .o_wsale_alert_stock',       // nombres custom frecuentes
        ].join(',')
      );

    if (node) return true;

    // 2) Patrón por texto (multi-idioma). Escaneo ligero del carrito
    const container =
      $('.o_wsale_cart') || $('.oe_website_sale') || $('#wrapwrap') || document;
    const txt = (container.textContent || '').toLowerCase();

    const patterns = [
      // ES
      'no hay suficientes', 'sin stock', 'no disponible',
      'agotado', 'stock insuficiente', 'disponible próximamente',
      // EN
      'not enough', 'out of stock', 'backorder', 'on backorder', 'unavailable',
      // FR
      'rupture de stock', 'non disponible', 'précommande',
      // PT/IT
      'sem stock', 'esgotado', 'non disponibile', 'disponibile a breve',
    ];
    return patterns.some(p => txt.includes(p));
  }

  function placeBanner() {
    if (document.getElementById('sp-cart-stock-banner')) return;
    const host = getCartHost();

    const div = document.createElement('div');
    div.id = 'sp-cart-stock-banner';
    div.className = 'alert alert-danger sp-cart-stock-banner';
    div.role = 'alert';
    div.style.marginBottom = '1rem';
    div.textContent = 'Pendiente revisión de stock o próximas llegadas.';

    // Insertar al inicio del contenedor
    if (host.firstElementChild) host.insertBefore(div, host.firstElementChild);
    else host.appendChild(div);
  }

  function removeBanner() {
    const b = document.getElementById('sp-cart-stock-banner');
    if (b) b.remove();
  }

  function runOnce() {
    if (!isCartPage()) return;
    hasOdooStockWarnings() ? placeBanner() : removeBanner();
  }

  // Arranque (incluye doble pasada para contenidos que cargan tarde)
  function start() {
    if (!isCartPage()) return;
    runOnce();
    // Reintento corto y medio por si hay render diferido
    setTimeout(runOnce, 120);
    setTimeout(runOnce, 500);

    // Re-evaluar cambios dinámicos (qty +/- AJAX, cupones, etc.)
    const root = $('#wrapwrap') || document.documentElement;
    const mo = new MutationObserver(() => runOnce());
    mo.observe(root, { subtree: true, childList: true, attributes: true });
  }

  (document.readyState === 'loading')
    ? document.addEventListener('DOMContentLoaded', start, { once: true })
    : start();
})();