/** simple DOM script - no module system **/
document.addEventListener('click', function (ev) {
  const btn = ev.target.closest('#spw_personalize_btn');
  if (!btn) return;
  ev.preventDefault();
  const tmpl = btn.dataset.templateId;
  const variant = btn.dataset.variantId || btn.dataset.productId;
  if (tmpl && variant) {
    window.location.href = `/spw/customize/${tmpl}?variant_id=${variant}`;
  }
});