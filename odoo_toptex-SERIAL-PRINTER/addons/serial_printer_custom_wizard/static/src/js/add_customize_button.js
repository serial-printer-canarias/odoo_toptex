/** @odoo-module **/

// Inserta el botón "Personalizar" junto al "Add to cart" en la ficha de producto.
// Sin publicWidget ni QWeb: DOM directo + MutationObserver (robusto ante recargas ajax).

function findButtonsContainer() {
    return (
        document.querySelector(".o_wsale_product_buttons") ||
        document.querySelector(".o_wsale_product_btns") ||
        document.querySelector(".o_wsale_product_btn")
    );
}

function currentProductId() {
    const input = document.querySelector('input[name="product_id"]');
    if (input && input.value) return input.value;

    // Fallback: intenta sacar el id de la URL /shop/product/<slug>-<id>
    const m = location.pathname.match(/\/shop\/product\/.*-(\d+)/);
    return m ? m[1] : null;
}

function insertCustomizeButton() {
    const container = findButtonsContainer();
    if (!container) return;

    if (document.getElementById("spw_customize_btn_qweb")) return;

    const pid = currentProductId();
    if (!pid) return;

    const a = document.createElement("a");
    a.id = "spw_customize_btn_qweb";
    a.className = "btn btn-outline-primary ms-2";
    a.href = `/personalizar/${pid}`;
    a.innerHTML = `<i class="fa fa-magic me-1"></i><span>Personalizar</span>`;
    container.appendChild(a);
}

document.addEventListener("DOMContentLoaded", () => {
    insertCustomizeButton();

    // Reintenta si cambian variantes/DOM (Odoo repinta la zona)
    const target =
        document.querySelector(".o_wsale_product_information") ||
        document.body;
    const obs = new MutationObserver(() => insertCustomizeButton());
    obs.observe(target, { childList: true, subtree: true });
});