(function () {
  "use strict";

  function bind() {
    const btn = document.getElementById("spw_customize_btn");
    if (!btn) return;
    btn.addEventListener("click", (ev) => {
      ev.preventDefault();
      const variantInput = document.querySelector("form#add_to_cart input[name='product_id']");
      const variantId = variantInput ? variantInput.value : "";
      const tmplId = btn.dataset.ptmplId || btn.getAttribute("data-ptmpl-id") || "";
      const url = `/spw/customizer?product_id=${encodeURIComponent(tmplId)}&variant_id=${encodeURIComponent(variantId)}`;
      window.location.href = url;
    });
  }

  const onReady = () => bind();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }
  document.addEventListener("DOMNodeInserted", onReady);
})();