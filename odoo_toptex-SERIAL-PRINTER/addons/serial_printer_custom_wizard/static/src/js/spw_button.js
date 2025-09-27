(function () {
  'use strict';
  function ready(fn){ if(document.readyState !== 'loading'){ fn(); } else { document.addEventListener('DOMContentLoaded', fn); } }

  ready(function(){
    const btn = document.getElementById('spw_personalize_btn');
    if (!btn) return;

    btn.addEventListener('click', function(ev){
      ev.preventDefault();

      // 1) Tomar la variante actual desde el <form> (input hidden name=product_id)
      const form = btn.closest('form') || document.querySelector('form[action*="/shop/cart/update"]') || document.querySelector('form');
      let variantId = null;
      if (form) {
        const hidden = form.querySelector('input[name="product_id"]');
        if (hidden && hidden.value) variantId = parseInt(hidden.value, 10) || null;
      }

      // 2) Tomar el template id del data-atributo del propio botón
      const tmplId = parseInt(btn.getAttribute('data-product-template-id'), 10) || null;
      if (!tmplId) { console.error('SPW: falta data-product-template-id en el botón'); return; }

      // 3) Construir URL
      let url = '/spw/customize/' + tmplId;
      if (variantId) url += '?variant_id=' + variantId;

      window.location.href = url;
    });
  });
})();