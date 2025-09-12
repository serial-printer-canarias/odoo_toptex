document.addEventListener("click", function (ev) {
  const btn = ev.target.closest("#spw_personalize_btn");
  if (!btn) return;
  ev.preventDefault();

  const tmplId = btn.dataset.productTemplateId;
  const inputVariant = document.querySelector("form input[name='product_id']");
  const variantId = inputVariant && inputVariant.value;
  if (tmplId && variantId) {
    window.location.href = `/spw/customize/${tmplId}?variant_id=${variantId}`;
  }
});