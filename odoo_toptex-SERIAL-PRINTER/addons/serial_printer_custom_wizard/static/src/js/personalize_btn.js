// Vanilla JS. Sin odoo.define, sin dependencias.
// Navega a la página de personalización con plantilla y variante.
(function () {
  document.addEventListener('click', function (ev) {
    const btn = ev.target.closest('#spw_personalize_btn');
    if (!btn) return;

    ev.preventDefault();

    const tmplId = btn.dataset.productTemplateId;
    const variantInput = document.querySelector('input[name="product_id"]');
    const variantId = variantInput ? variantInput.value : '';

    if (!tmplId) return;
    const url = '/spw/customize/' + tmplId + (variantId ? ('?variant_id=' + variantId) : '');
    window.location.href = url;
  }, { passive: false });
})();