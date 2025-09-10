odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
  'use strict';

  const publicWidget = require('web.public.widget');

  function firstSelector(list) {
    for (let i = 0; i < list.length; i++) {
      const el = document.querySelector(list[i]);
      if (el) return el;
    }
    return null;
  }

  function getProductIdFromUrl() {
    const m = window.location.pathname.match(/\/shop\/product\/[^/]*-(\d+)(?:\/|$)/);
    return m ? m[1] : null;
  }

  function ensureBadge() {
    if (document.getElementById('spw_js_ok')) return;
    const badge = document.createElement('div');
    badge.id = 'spw_js_ok';
    badge.textContent = 'SPW JS OK';
    badge.style.cssText =
      'position:fixed;right:8px;bottom:8px;padding:6px 10px;border-radius:8px;' +
      'background:#e9eefc;border:1px solid #d0d7ff;font:12px/1.2 system-ui;z-index:9999';
    document.body.appendChild(badge);
  }

  function placeButton(container) {
    if (document.getElementById('spw_customize_btn')) return;

    const pid = getProductIdFromUrl();
    if (!pid) return;

    const btn = document.createElement('a');
    btn.id = 'spw_customize_btn';
    btn.className = 'btn btn-outline-secondary mt-3 w-100';
    btn.textContent = 'Personalizar';
    btn.href = '/spw/personalizar/' + pid;

    // Debajo del Add to cart si existe
    const addToCart = container.querySelector('form[action*="/shop/cart/update"] .btn, .o_wsale_product_information .btn-primary');
    if (addToCart && addToCart.parentElement) {
      addToCart.parentElement.appendChild(btn);
    } else {
      // Fallback: al final del contenedor principal
      container.appendChild(btn);
    }
  }

  publicWidget.registry.SPWAddCustomizeButton = publicWidget.Widget.extend({
    selector: 'body',
    start: function () {
      // Ejecuta en carga y reintenta por si el DOM tarda
      const run = () => {
        const pid = getProductIdFromUrl();
        if (!pid) return;
        const container = firstSelector([
          '.o_wsale_product_information',
          '#product_details',
          '.o_wsale_product_page',
          '.product_main',
          '#wrap .container',
          '#wrap',
        ]);
        if (!container) return;
        placeButton(container);
        ensureBadge();
      };
      run();
      setTimeout(run, 500);
      setTimeout(run, 1500);
      return this._super.apply(this, arguments);
    },
  });
});