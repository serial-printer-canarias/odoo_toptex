/* SP – Cart stock banner (robusto, solo UI, sin tocar metodología) */
(function () {
  'use strict';

  const $  = (s, c = document) => c.querySelector(s);
  const $$ = (s, c = document) => Array.from(c.querySelectorAll(s));
  const log = (...a) => console.log('[SP CART]', ...a);

  /* 1) ¿Estamos en carrito? (cubrir /shop/cart y variantes) */
  function isCartPage() {
    const p = (location.pathname + location.search).toLowerCase();
    return /\/(shop|website_sale)\/cart(?:$|[?#/])/.test(p);
  }

  /* 2) Dónde insertar el banner (varios temas) */
  function getCartHost() {
    return (
      $('.o_wsale_cart') ||
      $('.oe_website_sale') ||
      $('#wrapwrap .container') ||
      $('#wrapwrap') ||
      $('main .container') ||
      $('main') ||
      document.body
    );
  }

  /* 3) Detección de avisos nativos de stock (múltiples temas/idiomas) */
  function hasStockWarnings(root = document) {
    // A) Selectores de warning/danger habituales en carrito
    const selectors = [
      '.css_not_available_msg',                   // website_sale_stock clásico
      '.o_wsale_cart .alert-warning',
      '.o_wsale_cart .alert-danger',
      '.oe_website_sale .alert-warning',
      '.oe_website_sale .alert-danger',
      '.js_cart_lines .text-warning',
      '.js_cart_lines .text-danger',
      '.o_website_sale_stock_warning',            // variantes en temas
      '.o_wsale_cart .o_wsale_alert_stock',
      '.o_not_enough_qty',
      '[data-stock-warning="1"]',
      '.o_notification_manager .o_notification'   // toasts OWL (algunos temas los dejan en DOM)
    ];
    if (root.querySelector(selectors.join(','))) return true;

    // B) Alerts genéricas con texto de stock (multi-idioma)
    const scope = $('#wrapwrap') || $('.o_wsale_cart') || $('.oe_website_sale') || document;
    const alertNodes = $$('[role="alert"], .alert, .text-warning, .text-danger', scope);
    const hayTexto = (el) => {
      const t = (el.textContent || '').toLowerCase();
      if (!t) return false;
      const pats = [
        // ES
        'sin stock', 'no hay stock', 'no disponible', 'agotado', 'stock insuficiente',
        'no hay suficientes', 'próximas llegadas', 'pendiente revisión de stock',
        // EN
        'out of stock', 'not enough', 'unavailable', 'backorder', 'on backorder',
        // FR
        'rupture de stock', 'non disponible', 'précommande',
        // PT/IT
        'sem stock', 'esgotado', 'non disponibile', 'disponibile a breve'
      ];
      return pats.some(p => t.includes(p));
    };
    if (alertNodes.some(hayTexto)) return true;

    // C) Íconos de alerta junto a líneas (temas FA 5/6)
    const iconWarn = scope.querySelector('.fa-exclamation-triangle, .fa-triangle-exclamation, .oi-alert, .bi-exclamation-triangle-fill');
    return !!iconWarn;
  }

  /* 4) Pintar / quitar banner */
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
    host.firstElementChild
      ? host.insertBefore(div, host.firstElementChild)
      : host.appendChild(div);
    log('banner mostrado');
  }
  function removeBanner() {
    const b = document.getElementById('sp-cart-stock-banner');
    if (b) { b.remove(); log('banner ocultado'); }
  }

  /* 5) Ejecutar (incluye reintentos por render diferido y observador DOM) */
  function evaluate() {
    if (!isCartPage()) return;
    hasStockWarnings() ? placeBanner() : removeBanner();
  }

  function start() {
    if (!isCartPage()) return;
    // Pasadas escalonadas para contenidos que llegan tarde
    evaluate();
    setTimeout(evaluate, 120);
    setTimeout(evaluate, 400);
    setTimeout(evaluate, 1000);

    // Mutations (qty +/- por AJAX, cupones, etc.)
    const root = $('#wrapwrap') || document.documentElement;
    const mo = new MutationObserver(() => evaluate());
    mo.observe(root, { subtree: true, childList: true, attributes: true });
    log('observador activo');
  }

  (document.readyState === 'loading')
    ? document.addEventListener('DOMContentLoaded', start, { once: true })
    : start();

  // Por si el tema añade contenido en onload
  window.addEventListener('load', () => setTimeout(evaluate, 0), { once: true });
})();