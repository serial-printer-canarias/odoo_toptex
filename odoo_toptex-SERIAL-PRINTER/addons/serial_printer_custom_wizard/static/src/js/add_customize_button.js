/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SpwCustomizeBtn = publicWidget.Widget.extend({
    selector: "body",

    start() {
        this._injectOrUpdate();
        this._watchDom();
        return this._super(...arguments);
    },

    // Observa cambios (cambio de variante, renders del DOM, etc.)
    _watchDom() {
        const target =
            document.querySelector(".o_wsale_product_form")
            || document.querySelector('form[action*="/shop/cart/update"]')
            || document;

        this._mo = new MutationObserver(() => this._injectOrUpdate());
        this._mo.observe(target, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["value", "class"],
        });

        // Por si el tema dispara eventos de variante propios
        window.addEventListener("odoo:variant-changed", () => this._injectOrUpdate());
        document.addEventListener("change", (e) => {
            if (e.target && e.target.name === "product_id") {
                this._injectOrUpdate();
            }
        });
    },

    // Lee ids actuales de template y variante
    _getIds() {
        const tmplInput =
            document.querySelector('input[name="product_template_id"]')
            || document.querySelector('input[name="product_template"]');

        const productInput = document.querySelector('input[name="product_id"]');

        const tmplId =
            (tmplInput && tmplInput.value)
            || document.body.getAttribute("data-product-template-id")
            || null;

        const productId = (productInput && productInput.value) || null;

        return { tmplId, productId };
    },

    // Inserta/actualiza el botón junto a "Add to cart"
    _injectOrUpdate() {
        const { tmplId, productId } = this._getIds();
        if (!tmplId) return;

        const addBtn = document.querySelector('button[name="add_to_cart"]');

        // Contenedor de respaldo si cambia el markup del tema
        const fallbackContainer =
            (addBtn && addBtn.parentElement)
            || document.querySelector(
                ".o_wsale_product_buttons, .o_wsale_product_btns, .o_wsale_product_btn"
            )
            || document.querySelector(".o_wsale_product_form")
            || document.querySelector('form[action*="/shop/cart/update"]');

        if (!fallbackContainer) return;

        let btn = document.querySelector("#spw_customize_btn_qweb");
        const href = `/personalizar/${tmplId}${productId ? `?vid=${productId}` : ""}`;

        if (!btn) {
            btn = document.createElement("a");
            btn.id = "spw_customize_btn_qweb";
            btn.className = "btn btn-outline-primary ms-2";
            btn.innerHTML = '<i class="fa fa-magic me-1"></i><span>Personalizar</span>';
            fallbackContainer.appendChild(btn);
        }

        if (btn.getAttribute("href") !== href) {
            btn.setAttribute("href", href);
        }
    },
});