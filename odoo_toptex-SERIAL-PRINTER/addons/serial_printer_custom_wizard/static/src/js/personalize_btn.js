/** @odoo-module **/
(function () {
  // Navegación del botón "Personalizar" sin dependencias
  function getVariantId() {
    const v1 = document.querySelector('input[name="product_template_variant_id"]');
    if (v1 && v1.value) return v1.value;
    const v2 = document.querySelector('form[action*="/shop/cart/update"] input[name="product_id"]');
    return (v2 && v2.value) || "";
  }

  function getTemplateId() {
    const t1 = document.querySelector('input[name="product_template_id"]');
    if (t1 && t1.value) return t1.value;
    const t2 = document.querySelector('form[action*="/shop/cart/update"] input[name="product_template_id"]');
    return (t2 && t2.value) || "";
  }

  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("#spw_personalize_btn");
    if (!btn) return;
    ev.preventDefault();

    const tplId = getTemplateId() || btn.dataset.productId || "";
    const variantId = getVariantId();
    if (!tplId) return;

    const url = `/spw/customize/${encodeURIComponent(tplId)}${
      variantId ? `?variant_id=${encodeURIComponent(variantId)}` : ""
    }`;
    window.location.assign(url);
  });
})();