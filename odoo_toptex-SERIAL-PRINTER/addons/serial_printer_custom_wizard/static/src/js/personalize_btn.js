/** @odoo-module **/

// Navegar al customizer con el product_id y la variante seleccionada
document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("#spw_personalize_btn");
    if (!btn) return;

    ev.preventDefault();
    const pId = btn.dataset.productId;
    const vInput = document.querySelector("input[name='product_id']");
    const variantId = vInput && vInput.value;

    if (!pId || !variantId) return;
    window.location.href = `/spw/customize/${pId}?variant_id=${variantId}`;
});