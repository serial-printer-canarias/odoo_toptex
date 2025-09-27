(function () {
  "use strict";

  const onProductPage = () => location.pathname.indexOf("/shop/") !== -1;

  function bindOpen() {
    const btn = document.getElementById("spw_customize_btn");
    if (!btn) return;

    btn.addEventListener("click", (ev) => {
      ev.preventDefault();

      // Odoo mantiene el variant_id seleccionado en el input oculto del form add_to_cart
      const variantInput = document.querySelector("form#add_to_cart input[name='product_id']");
      const variantId = variantInput ? variantInput.value : "";
      const tmplId = btn.dataset.ptmplId || btn.getAttribute("data-ptmpl-id") || "";

      // Redirección al route público del customizer (ya lo tienes en tus controllers)
      const url = `/spw/customizer?product_id=${encodeURIComponent(tmplId)}&variant_id=${encodeURIComponent(variantId)}`;
      window.location.href = url;
    });
  }

  function safeBind() {
    if (!onProductPage()) return;
    bindOpen();
  }

  window.addEventListener("load", safeBind);

  // Por si Odoo recompone el DOM al cambiar variante
  document.addEventListener("DOMNodeInserted", safeBind);
})();