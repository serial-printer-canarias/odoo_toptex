/** Simple injector – Odoo 17/18 compatible, no imports */
(function () {
  if (window.__spw_btn_loaded__) return;
  window.__spw_btn_loaded__ = true;

  const BTN_ID = "spw_customize_btn";

  function insertButton() {
    // Evitar duplicados
    if (document.getElementById(BTN_ID)) return;

    // Necesitamos el ID del producto
    const pidInput = document.querySelector('input[name="product_id"]');
    if (!pidInput || !pidInput.value) return;
    const productId = pidInput.value;

    // Contenedor junto al "Add to cart" (varía por tema/versión)
    const container =
      document.querySelector(".o_wsale_product_buttons") ||
      document.querySelector(".o_wsale_product_btns") ||
      document.querySelector('form[action*="/shop/cart/update"]') ||
      document.querySelector(".js_add_to_cart_form");
    if (!container) return;

    // Crear el botón
    const a = document.createElement("a");
    a.id = BTN_ID;
    a.href = `/personalizar/${productId}`;
    a.className = "btn btn-outline-primary ms-2";
    a.innerHTML = `<i class="fa fa-magic me-1"></i><span>Personalizar</span>`;

    // Colocarlo pegado al botón de carrito si existe
    const addBtn =
      container.querySelector('button[name="add_to_cart"]') ||
      container.querySelector('.btn-primary[name="add_to_cart"]') ||
      container.querySelector('a[name="add_to_cart"]');

    (addBtn && addBtn.parentElement ? addBtn.parentElement : container).appendChild(a);
  }

  // Primer intento cuando cargue el DOM
  document.addEventListener("DOMContentLoaded", insertButton);
  // Reintentos si el DOM cambia (cambio de variantes, lazy load, etc.)
  if ("MutationObserver" in window) {
    const mo = new MutationObserver(insertButton);
    mo.observe(document.body, { childList: true, subtree: true });
  }
  // Navegación interna (paginación/ajax del website)
  window.addEventListener("popstate", insertButton);
})();