/** serial_printer_custom_wizard/static/src/js/personalize_btn.js
 *  Acción del botón "Personalizar" en la ficha de producto (Odoo 18).
 *  - NO depende de widgets.
 *  - Usa delegación de eventos (funciona aunque el botón se reinyecte).
 *  - Lee data-product-template-id del botón y el product_id (variante) del <form>.
 */
(function () {
  'use strict';

  // Delegación: capturamos clicks en todo el documento y filtramos el botón
  document.addEventListener('click', function (ev) {
    var btn = ev.target && ev.target.closest && ev.target.closest('#spw_personalize_btn');
    if (!btn) return;

    ev.preventDefault();

    // product template id desde el data- attribute (100% seguro con getAttribute)
    var tmplId = btn.getAttribute('data-product-template-id');

    // Variante seleccionada: hidden input name="product_id" dentro del <form> más cercano
    var form = btn.closest('form');
    var variantId = null;
    if (form) {
      var input = form.querySelector("input[name='product_id']");
      if (input && input.value) variantId = input.value;
    }

    // Fallback por si algún tema elimina el data- del botón
    if (!tmplId) {
      var meta = document.querySelector("meta[name='product_template_id']");
      if (meta) tmplId = meta.getAttribute('content');
    }

    if (!tmplId) {
      // No rompemos la navegación: dejamos un log y salimos.
      console.warn('[SPW] No se pudo resolver el product template id.');
      return;
    }

    var url = '/spw/customize/' + encodeURIComponent(tmplId);
    if (variantId) url += '?variant_id=' + encodeURIComponent(variantId);

    window.location.assign(url);
  });

})();