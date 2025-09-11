// static/src/js/add_customize_button.js
// Muestra SIEMPRE el botón "Personalizar" en la ficha de producto (website_sale – Odoo 18)
// No requiere publicWidget. Funciona con DOMContentLoaded y con cambios dinámicos del DOM.

(function () {
  const BTN_ID = "spw_customize_btn";

  // Contenedores típicos donde viven los botones de compra en website_sale
  const BUTTONS_WRAPPER_SELECTORS = [
    ".o_wsale_product_buttons",
    ".o_wsale_product_btns",
    ".o_wsale_buttons",
    ".o_wsale_product_form .o_wsale_product_buttons",
    "form[action*='/shop/cart/update'] .o_wsale_product_buttons"
  ].join(",");

  function isProductPage() {
    // señales habituales en la página de producto
    return !!(
      document.querySelector(".oe_website_sale") ||
      document.querySelector(".o_wsale_product_page") ||
      document.querySelector("form[action*='/shop/cart/update']")
    );
  }

  function getVariantId() {
    // Variante seleccionada (product.product)
    const v =
      document.querySelector("input[name='product_id']") ||
      document.querySelector("input[name='product_product_id']");
    const val = v && v.value ? parseInt(v.value, 10) : null;
    return Number.isFinite(val) ? val : null;
  }

  function getTemplateId() {
    // Template (product.template)
    const t =
      document.querySelector("input[name='product_template_id']") ||
      document.querySelector("input[name='product_tmpl_id']");
    const val = t && t.value ? parseInt(t.value, 10) : null;
    return Number.isFinite(val) ? val : null;
  }

  function buildCustomizeUrl() {
    const variantId = getVariantId();
    const tmplId = getTemplateId() || variantId; // fallback si no encontramos template
    if (!tmplId) return null;
    // Pasamos variant_id para que el lienzo muestre la imagen de la variante
    const params = variantId ? `?variant_id=${variantId}` : "";
    return `/personalizar/${tmplId}${params}`;
  }

  function makeButton() {
    const btn = document.createElement("button");
    btn.id = BTN_ID;
    btn.type = "button";
    btn.className = "btn btn-outline-primary ms-2";
    btn.innerHTML = `<span class="me-1">🎨</span>Personalizar`;
    btn.addEventListener("click", () => {
      const url = buildCustomizeUrl();
      if (!url) {
        // Si por cualquier motivo no detectamos ids, reintentamos tras un tick
        setTimeout(() => {
          const retryUrl = buildCustomizeUrl();
          if (retryUrl) window.location.href = retryUrl;
          else alert("No se pudo determinar la variante/plantilla del producto.");
        }, 50);
        return;
      }
      window.location.href = url;
    });
    return btn;
  }

  function insertButton() {
    if (!isProductPage()) return;

    // Si ya existe, no duplicamos
    if (document.getElementById(BTN_ID)) return;

    // Buscamos el contenedor y el botón "Add to cart" para insertar a continuación
    const wrapper =
      document.querySelector(BUTTONS_WRAPPER_SELECTORS) ||
      document.querySelector("form[action*='/shop/cart/update']");
    if (!wrapper) return;

    // “Add to cart” (nombre estándar en website_sale)
    const addToCartBtn =
      wrapper.querySelector("button[name='add_to_cart']") ||
      wrapper.querySelector("button[type='submit']");

    const btn = makeButton();

    if (addToCartBtn && addToCartBtn.parentElement) {
      addToCartBtn.parentElement.insertBefore(btn, addToCartBtn.nextSibling);
    } else {
      // fallback: lo metemos al final del wrapper
      wrapper.appendChild(btn);
    }
  }

  // Observamos cambios de DOM para reinsertar el botón cuando Odoo refresca la vista
  let observer = null;
  function startObserver() {
    if (observer) return;
    observer = new MutationObserver((mutations) => {
      // Reintentamos cuando cambian inputs, botones o el contenedor
      const relevant = mutations.some((m) => {
        return (
          m.addedNodes.length ||
          (m.target && (m.target.matches?.(BUTTONS_WRAPPER_SELECTORS) ||
            m.target.matches?.("input[name='product_id'], input[name='product_template_id']")))
        );
      });
      if (relevant) {
        // Pequeño delay para dejar terminar a los scripts de website_sale
        setTimeout(insertButton, 30);
      }
    });
    observer.observe(document.documentElement || document.body, {
      childList: true,
      subtree: true,
      attributes: false
    });
  }

  // Lanzamos en cuanto carga el DOM
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      insertButton();
      startObserver();
    });
  } else {
    insertButton();
    startObserver();
  }

  // Reintentos por si los IDs aparecen tarde tras seleccionar atributos
  ["change", "click"].forEach((evt) => {
    document.addEventListener(evt, (e) => {
      if (
        e.target &&
        (e.target.matches("input[name^='attr'], select[name^='attr']") ||
          e.target.matches("input[name='product_id'], input[name='product_template_id']"))
      ) {
        setTimeout(insertButton, 50);
      }
    });
  });
})();