(function () {
  "use strict";

  function getVariantId() {
    const hidden = document.querySelector("form input[name='product_id']");
    if (hidden && hidden.value) {
      const n = parseInt(hidden.value, 10);
      return isNaN(n) ? null : n;
    }
    return null;
  }

  document.addEventListener("click", function (ev) {
    const btn = ev.target.closest("#spw_personalize_btn");
    if (!btn) return;

    ev.preventDefault();

    const tmplId = btn.dataset.tmplId;
    const variantId = getVariantId();

    if (!tmplId) return;

    let url = `/spw/customize/${tmplId}`;
    if (variantId) url += `?variant_id=${variantId}`;

    window.location.href = url;
  });
})();