/** Move the "Personalizar" button next to the add-to-cart button */
document.addEventListener("DOMContentLoaded", () => {
  const form =
    document.querySelector("form.o_wsale_product_form") ||
    document.getElementById("product_form") ||
    document.querySelector("form[action*='/shop/cart']");

  const personalize = document.getElementById("spw_personalize_btn");
  if (!form || !personalize) return;

  const addBtn =
    form.querySelector("button[name='add_to_cart']") ||
    form.querySelector(".o_add_to_cart") ||
    form.querySelector(".js_add_cart_json") ||
    form.querySelector("button.btn-primary");

  if (addBtn) {
    addBtn.insertAdjacentElement("afterend", personalize);
    personalize.classList.remove("mt-2");
    personalize.classList.add("ms-2");
  } else {
    form.appendChild(personalize);
  }
});