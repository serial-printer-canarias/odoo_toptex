/** SPW – Inject "Personalizar" button next to "Add to cart" (theme-agnostic) **/
(function () {
    "use strict";

    const BTN_ID = "spw_customize_btn_qweb";

    function getIds() {
        const tmpl =
            document.querySelector('input[name="product_template_id"]') ||
            document.querySelector('input[name="product_template"]');

        const variant = document.querySelector('input[name="product_id"]');

        const tmplId = tmpl && tmpl.value ? tmpl.value : null;
        const productId = variant && variant.value ? variant.value : null;

        return { tmplId, productId };
    }

    function findAddToCartButton() {
        // Intentos comunes en Odoo 16/17/18 y temas
        return (
            document.querySelector('button[name="add_to_cart"]') ||
            document.querySelector(".o_add_to_cart_btn") ||
            document.querySelector(".btn.o_wsale_add_to_cart")
        );
    }

    function findContainer(addBtn) {
        // Contenedores habituales junto al botón
        return (
            (addBtn && addBtn.parentElement) ||
            document.querySelector(".o_wsale_product_buttons") ||
            document.querySelector(".o_wsale_product_btns") ||
            document.querySelector(".o_wsale_product_btn") ||
            document.querySelector(".o_wsale_product_form") ||
            document.querySelector('form[action*="/shop/cart/update"]') ||
            addBtn && addBtn.closest("form") ||
            document.body
        );
    }

    function currentHref(tmplId, productId) {
        if (!tmplId) return null;
        return `/personalizar/${tmplId}${productId ? `?vid=${productId}` : ""}`;
    }

    function injectOrUpdate() {
        const addBtn = findAddToCartButton();
        if (!addBtn) return; // aún no está en DOM

        const { tmplId, productId } = getIds();
        if (!tmplId) return; // aún no renderizó inputs hidden

        const href = currentHref(tmplId, productId);
        if (!href) return;

        let btn = document.getElementById(BTN_ID);

        if (!btn) {
            btn = document.createElement("a");
            btn.id = BTN_ID;
            btn.className = "btn btn-outline-primary ms-2";
            btn.innerHTML = '<i class="fa fa-magic me-1"></i><span>Personalizar</span>';

            // Colócalo justo después del Add to cart si es posible,
            // si no, al final del contenedor.
            try {
                addBtn.insertAdjacentElement("afterend", btn);
            } catch (e) {
                findContainer(addBtn).appendChild(btn);
            }
        }

        if (btn.getAttribute("href") !== href) {
            btn.setAttribute("href", href);
        }
    }

    function startObservers() {
        // Inyección inicial cuando el DOM esté listo
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", injectOrUpdate);
        } else {
            injectOrUpdate();
        }

        // Observa cambios de DOM (cambios de variante, renders)
        const root = document.querySelector(".o_wsale_product_form") || document;
        const mo = new MutationObserver(() => injectOrUpdate());
        mo.observe(root, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ["value", "class", "href"],
        });

        // Por si el tema lanza eventos propios al cambiar variantes
        window.addEventListener("odoo:variant-changed", injectOrUpdate, { passive: true });
        document.addEventListener("change", (ev) => {
            const t = ev.target;
            if (!t) return;
            if (t.name === "product_id" || t.name === "product_template_id") {
                injectOrUpdate();
            }
        }, { passive: true });
    }

    // Arrancamos
    startObservers();
})();