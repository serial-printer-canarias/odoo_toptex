/* plain JS, no odoo.define ni @odoo-module */
(function () {
  function currentVariantId() {
    const el = document.querySelector("input[name='product_id']");
    return el && el.value ? el.value : null;
  }
  function currentTemplateId(btn) {
    // Preferimos el data- del propio botón; si no, intentamos localizarlo en el DOM
    return (
      btn.dataset.templateId ||
      (document.querySelector("input[name='product_template_id']") || {}).value ||
      null
    );
  }

  document.addEventListener("click", function (ev) {
    const btn = ev.target.closest("#spw_personalize_btn");
    if (!btn) return;

    // Evitamos navegar con el href si podemos construir la URL con la variante actual
    ev.preventDefault();

    const tmplId = currentTemplateId(btn);
    const variantId = currentVariantId() || btn.dataset.productId;

    if (!tmplId) {
      console.warn("[SPW] No se encontró template_id para el personalizador");
      // último recurso: seguir el href original
      window.location.href = btn.getAttribute("href") || "/";
      return;
    }

    const url =
      "/spw/customize/" + tmplId + (variantId ? "?variant_id=" + variantId : "");
    window.location.href = url;
  });
})();