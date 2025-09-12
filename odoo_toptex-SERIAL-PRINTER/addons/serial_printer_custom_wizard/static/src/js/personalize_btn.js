/** Navega al customizador con plantilla y variante correctas, sin romper nada más. */
(function () {
  function handleClick(ev) {
    ev.preventDefault();
    const btn = ev.currentTarget;
    const tmplId = btn.dataset.productTemplateId;
    if (!tmplId) return;

    // Buscar el <form> padre y tomar la variante actual del hidden input name="product_id"
    const form = btn.closest('form');
    let variantId = "";
    if (form) {
      const vInput = form.querySelector('input[name="product_id"]');
      if (vInput && vInput.value) variantId = vInput.value;
    }

    const url = `/spw/customize/${tmplId}` + (variantId ? `?variant_id=${variantId}` : "");
    window.location.href = url;
  }

  // Delegación por si Odoo re-renderiza
  document.addEventListener('click', function (e) {
    const target = e.target.closest('#spw_personalize_btn');
    if (target) handleClick.call(target, e);
  }, { passive: false });
})();