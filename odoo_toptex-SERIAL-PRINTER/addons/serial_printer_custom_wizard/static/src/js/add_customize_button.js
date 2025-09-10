(function () {
  'use strict';

  function firstSelector(list) {
    for (var i = 0; i < list.length; i++) {
      var el = document.querySelector(list[i]);
      if (el) return el;
    }
    return null;
  }

  function getProductIdFromUrl() {
    var m = window.location.pathname.match(/\/shop\/product\/[^/]*-(\d+)(?:\/|$)/);
    return m ? m[1] : null;
  }

  function placeButton(container) {
    if (document.getElementById('spw_customize_btn')) return;

    var pid = getProductIdFromUrl();
    if (!pid) return;

    var btn = document.createElement('a');
    btn.id = 'spw_customize_btn';
    btn.className = 'btn btn-outline-secondary mt-3 w-100';
    btn.textContent = 'Personalizar';
    btn.href = '/spw/personalizar/' + pid;

    // 1) debajo del botón "Add to cart"
    var addToCart = container.querySelector('form[action*="/shop/cart/update"] .btn-primary, .o_wsale_product_information .btn-primary');
    if (addToCart && addToCart.parentElement) {
      addToCart.parentElement.appendChild(btn);
      return;
    }
    // 2) debajo del enlace wishlist (si existe)
    var wishlist = container.querySelector('a[href*="wishlist"]');
    if (wishlist && wishlist.parentElement && wishlist.parentElement.parentElement) {
      wishlist.parentElement.parentElement.insertBefore(btn, wishlist.parentElement.nextSibling);
      return;
    }
    // 3) fallback: al final del contenedor
    container.appendChild(btn);
  }

  function addButton() {
    var pid = getProductIdFromUrl();
    if (!pid) return;

    var container = firstSelector([
      '.o_wsale_product_information',
      '#product_details',
      '.o_wsale_product_page',
      '.product_main',
      '#wrap .container',
      '#wrap'
    ]);
    if (!container) return;

    placeButton(container);

    // Badge de diagnóstico
    if (!document.getElementById('spw_js_ok')) {
      var badge = document.createElement('div');
      badge.id = 'spw_js_ok';
      badge.textContent = 'SPW JS OK';
      badge.style.cssText = 'position:fixed;right:8px;bottom:8px;padding:6px 10px;border-radius:8px;background:#e9eefc;border:1px solid #d0d7ff;font:12px/1.2 system-ui;z-index:9999';
      document.body.appendChild(badge);
    }
  }

  // Ejecutar al cargar y reintentar un poco por si el DOM tarda
  function boot() {
    addButton();
    setTimeout(addButton, 500);
    setTimeout(addButton, 1500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();