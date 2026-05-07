/* SPW – Fuerza el botón "Personalizar" en la ficha de producto (robusto) */
(function () {
  "use strict";

  const onProductPage = () =>
    !!(document.querySelector('form[action*="/shop/cart/update"]') || document.querySelector(".oe_website_sale"));

  const Q  = (s, r = document) => r.querySelector(s);

  function getIds(root = document) {
    // Template ID
    let pt = Q('input[name="product_template_id"], input[name="product_template"]', root);
    let ptid = pt && pt.value ? pt.value : null;
    if (!ptid) {
      const form = Q('form[action*="/shop/cart/update"]', root);
      ptid = form?.dataset?.productTemplateId || form?.getAttribute?.("data-product-template-id") || null;
    }
    // Variant ID
    let v = Q('input[name="product_id"]', root);
    let vid = v && v.value ? v.value : null;
    if (!vid) {
      const form = Q('form[action*="/shop/cart/update"]', root);
      vid = form?.dataset?.productId || form?.getAttribute?.("data-product-id") || null;
    }
    return { ptid, vid };
  }

  function ensureStyles() {
    if (Q("#spw_cbtn_css")) return;
    const st = document.createElement("style");
    st.id = "spw_cbtn_css";
    st.textContent = `
      #spw_customize_btn { white-space: nowrap; }
      .spw-cbtn-gap { margin-left:.5rem; }
      @media (max-width:576px){
        .spw-cbtn-gap { display:block; margin:.5rem 0 0 0; width:100%; }
        #spw_customize_btn { width:100%; }
      }
    `;
    document.head.appendChild(st);
  }

  function placeButton() {
    if (!onProductPage()) return;

    ensureStyles();

    const addBtn =
      Q('button[name="add_to_cart"]') ||
      Q('button[name="add_to_cart_json"]') ||
      Q(".o_wsale_add_to_cart") ||
      Q('.btn[name="add_to_cart"]');

    const { ptid, vid } = getIds();
    if (!addBtn || !ptid) return;

    // Crear/recuperar botón
    let btn = Q("#spw_customize_btn");
    if (!btn) {
      btn = document.createElement("a");
      btn.id = "spw_customize_btn";

      // Heredamos clases del Add to cart cuando existen
      const base = addBtn.className || "btn btn-primary";
      const classy = base.replace(/\bbtn-primary\b/, "btn-outline-primary");
      btn.className = `${classy} spw-cbtn-gap`;

      btn.innerHTML = `<i class="fa fa-magic me-1"></i><span>Personalizar</span>`;
      addBtn.insertAdjacentElement("afterend", btn);
    }

    // Href siempre actualizado
    let href = `/personalizar/${encodeURIComponent(ptid)}`;
    if (vid) href += `?vid=${encodeURIComponent(vid)}`;
    btn.setAttribute("href", href);
  }

  function init() {
    if (!onProductPage()) return;
    placeButton();

    // Reinsertar/actualizar si Odoo re-renderiza o cambian atributos
    const target =
      Q("#product_details") ||
      Q('form[action*="/shop/cart/update"]') ||
      document.body;

    const obs = new MutationObserver(() => placeButton());
    obs.observe(target, { childList: true, subtree: true, attributes: true });

    document.addEventListener(
      "change",
      (ev) => {
        const n = ev.target?.name || "";
        if (n === "product_id" || n.startsWith("attribute_")) placeButton();
      },
      true
    );

    // Por si la página llega cacheada
    window.addEventListener("load", placeButton);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();