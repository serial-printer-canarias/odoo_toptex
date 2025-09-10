/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SPWCustomizeButton = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page, .oe_website_sale",
    disabledInEditableMode: false,

    start() {
        // Inserta el botón cuando carga la página
        this._insertButton();
        // Y por si hay variantes que cambian dinámicamente:
        this._observeDOM();
        return this._super(...arguments);
    },

    _observeDOM() {
        const obs = new MutationObserver(() => this._insertButton());
        obs.observe(this.el, { childList: true, subtree: true });
    },

    _insertButton() {
        // si ya existe, no duplicar
        if (this.el.querySelector("#spw_customize_btn")) return;

        const productIdInput = this.el.querySelector('input[name="product_id"]');
        if (!productIdInput) {
            console.warn("SPW: no se encontró input[name=product_id]");
            return;
        }
        const productId = productIdInput.value;

        // sitio razonable junto al "Add to cart"
        const cartBtn = this.el.querySelector(".o_wsale_add_to_cart, button[name='add_to_cart']");
        const target = cartBtn?.parentElement || this.el.querySelector(".o_wsale_product_buttons") || this.el;

        const a = document.createElement("a");
        a.id = "spw_customize_btn";
        a.className = "btn btn-outline-secondary ms-2";
        a.href = `/personalizar/${productId}`;
        a.innerHTML = `<i class="fa fa-magic me-1"></i><span>Personalizar</span>`;

        target.appendChild(a);
        console.log("SPW: botón insertado", a.href);
    },
});