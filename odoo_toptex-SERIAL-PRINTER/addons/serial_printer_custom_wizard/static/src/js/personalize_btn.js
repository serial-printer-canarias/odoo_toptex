// JS plano para evitar errores del module loader
document.addEventListener("click", function (ev) {
  const btn = ev.target.closest("#spw_personalize_btn");
  if (!btn) return;

  ev.preventDefault();
  const tmplId = btn.dataset.productTemplateId;
  const productIdInput = document.querySelector("form input[name='product_id']");
  const variantId = productIdInput && productIdInput.value;

  if (tmplId && variantId) {
    window.location.href = `/spw/customize/${tmplId}?variant_id=${variantId}`;
  }
});