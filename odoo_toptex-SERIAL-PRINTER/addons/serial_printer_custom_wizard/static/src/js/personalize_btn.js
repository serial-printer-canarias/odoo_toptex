(function () {
  'use strict';

  function goToCustomizer(evt) {
    evt.preventDefault();
    try {
      const btn = evt.currentTarget;
      const tmplId = btn.getAttribute('data-product-id'); // product.template id
      if (!tmplId) return;

      // el hidden que Odoo mantiene con la variante actual
      const variantInput = document.querySelector("input[name='product_id']");
      const variantId = variantInput && variantInput.value ? parseInt(variantInput.value, 10) : null;

      const url = variantId
        ? `/spw/customize/${tmplId}?variant_id=${variantId}`
        : `/spw/customize/${tmplId}`;

      window.location.href = url;
    } catch (e) {
      console.error('SPW personalize_btn error:', e);
    }
  }

  function attach() {
    const btn = document.getElementById('spw_personalize_btn');
    if (btn && !btn.dataset.spwBound) {
      btn.addEventListener('click', goToCustomizer);
      btn.dataset.spwBound = '1';
    }
  }

  // Bind en carga y cuando el DOM cambia (editores, etc.)
  document.addEventListener('DOMContentLoaded', attach);
  document.addEventListener('o_page_loaded', attach);
})();