(function () {
  function findVariantId() {
    const candidates = [
      document.querySelector('.js_product input[name="product_id"]'),
      document.querySelector('form[action*="/shop/cart/update"] input[name="product_id"]'),
      document.querySelector('input[name="product_id"]'),
    ].filter(Boolean);

    for (const el of candidates) {
      const v = parseInt(el.value || '0', 10);
      if (v > 0) return v;
    }

    const ds = document.querySelector('.js_product[data-product-product-id]')?.dataset
      || document.querySelector('[data-product-product-id]')?.dataset
      || null;

    if (ds?.productProductId) {
      const v = parseInt(ds.productProductId || '0', 10);
      if (v > 0) return v;
    }
    return 0;
  }

  function onClick(ev) {
    const btn = ev.target.closest('#spw_customize_btn');
    if (!btn) return;

    ev.preventDefault();

    const tmplId = parseInt(btn.dataset.ptmplId || '0', 10);
    const variantId = findVariantId();
    if (!tmplId) return;

    const params = new URLSearchParams();
    params.set('product_id', String(tmplId));
    if (variantId) params.set('variant_id', String(variantId));

    window.location.href = `/spw/customizer?${params.toString()}`;
  }

  document.addEventListener('click', onClick, true);
})();
