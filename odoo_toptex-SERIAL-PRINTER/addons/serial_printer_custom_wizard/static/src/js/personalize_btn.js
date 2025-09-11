/** Build personalize URL with selected variant_id */
document.addEventListener("click", (ev) => {
  const btn = ev.target.closest("#spw_personalize_btn");
  if (!btn) return;

  const form =
    document.querySelector("form.o_wsale_product_form") ||
    document.getElementById("product_form");

  if (!form) return;

  // En Odoo web sale hay un input oculto con el product_id (variant)
  const variantInput =
    form.querySelector("input[name='product_id']") ||
    form.querySelector("input[name='product_template_id']");

  const variantId = variantInput ? variantInput.value : "";
  const url = new URL(btn.getAttribute("href"), window.location.origin);
  if (variantId) url.searchParams.set("variant_id", variantId);
  btn.setAttribute("href", url.pathname + url.search);
});