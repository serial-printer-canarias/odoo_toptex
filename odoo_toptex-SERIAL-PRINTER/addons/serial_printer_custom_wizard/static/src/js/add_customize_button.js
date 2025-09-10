/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.spwAddCustomizeBtn = publicWidget.Widget.extend({
    selector: "body",

    start() {
        // Reintentar cuando cambia dinámicamente el DOM (variantes, etc.)
        this._observer = new MutationObserver(() => this._insertButton());
        this._observer.observe(document.body, { childList: true, subtree: true });
        this._insertButton();
        return this._super(...arguments);
    },

    _insertButton() {
        // Evitar duplicados
        if (document.getElementById("spw_customize_btn")) return;

        // id del producto en la ficha
        const productInput = document.querySelector("form[action*='/shop'] input[name='product_id']");
        if (!productInput) return;
        const productId = productInput.value;

        // Botón "Add to cart" o su contenedor
        const addBtn = document.querySelector("form[action*='/shop'] button[name='add']")
            || document.querySelector("form[action*='/shop'] button[name='add_to_cart']");
        if (!addBtn) return;
        const container = addBtn.parentElement || addBtn.closest(".o_wsale_product_buttons") || addBtn.closest(".o_wsale_product_btns");
        if (!container) return;

        // Crear botón
        const a = document.createElement("a");
        a.id = "spw_customize_btn";
        a.className = "btn btn-outline-primary ms-2";
        a.href = `/personalizar/${productId}`;
        a.innerHTML = `<i class="fa fa-magic me-1"></i><span>Personalizar</span>`;
        container.appendChild(a);
    },
});