// Inserta SIEMPRE el botón "Personalizar" en la ficha de producto,
// y lo re-calcula cuando cambias de variante / se actualiza el DOM.
// No depende de QWeb. Funciona con cualquier tema de Odoo 17/18.

(function () {
  const BTN_ID = "spw_customize_btn";

  const BTN_HTML = (url) => `
    <a id="${BTN_ID}" class="btn btn-outline-primary ms-2" href="${url}">
      <i class="fa fa-magic me-1"></i><span>Personalizar</span>
    </a>
  `;

  function getVariantId(root = document) {
    // Variante activa (Odoo la pone en un hidden)
    const inp = root.querySelector('input[name="product_id"]');
    if (inp && inp.value) return parseInt(inp.value, 10);

    // Fall-back: algunos temas ponen data-product-id en el form
    const form = root.querySelector('form[action="/shop/cart/update"]');
    const pid = form?.dataset?.productId || form?.getAttribute("data-product-id");
    if (pid) return parseInt(pid, 10);

    return null;
  }

  function getTemplateId(root = document) {
    const inp = root.querySelector('input[name="product_template_id"]');
    return inp && inp.value ? parseInt(inp.value, 10) : null;
  }

  function getButtonsContainer(root = document) {
    // Contenedores habituales de los botones en website_sale + temas
    let el = root.querySelector(
      ".o_wsale_product_buttons, .o_wsale_product_btns, .o_wsale_product_btn"
    );
    if (el) return el;

    // Si no existe, nos pegamos al botón de añadir al carrito
    const add = root.querySelector('button[name="add_to_cart"]');
    if (add) return add.parentElement || add.closest("div");

    // Último recurso: el form de carrito
    return root.querySelector('form[action="/shop/cart/update"]');
  }

  function onProductPage() {
    // Estamos en la ficha de producto si existe el form de carrito
    return !!document.querySelector('form[action="/shop/cart/update"]');
  }

  function insertOrUpdate() {
    if (!onProductPage()) return;

    const id = getVariantId() ?? getTemplateId();
    const container = getButtonsContainer();
    if (!id || !container) return;

    const url = `/personalizar/${id}`;

    let btn = document.getElementById(BTN_ID);
    if (!btn) {
      // Evita duplicados por si el contenedor se regenera
      container.insertAdjacentHTML("beforeend", BTN_HTML(url));
    } else {
      btn.setAttribute("href", url);
      if (!btn.parentElement) container.appendChild(btn);
    }
  }

  // 1) Inserción inicial
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", insertOrUpdate);
  } else {
    insertOrUpdate();
  }

  // 2) Reintentos cortos por si el tema pinta tarde
  let tries = 0;
  const t = setInterval(() => {
    insertOrUpdate();
    if (++tries >= 10) clearInterval(t);
  }, 300);

  // 3) Reaccionar a cambios de variante o regeneraciones del DOM
  document.addEventListener("change", (ev) => {
    if (ev.target.closest('form[action="/shop/cart/update"]')) insertOrUpdate();
  });

  const mo = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "childList" || m.type === "attributes") {
        insertOrUpdate();
        break;
      }
    }
  });
  mo.observe(document.body, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["value", "class"],
  });
})();