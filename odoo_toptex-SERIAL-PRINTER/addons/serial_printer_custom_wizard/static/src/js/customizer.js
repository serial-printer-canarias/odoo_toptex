(function () {
  function qs(id) { return document.getElementById(id); }

  const imgLogo   = qs("spw_logo_preview");
  const inputFile = qs("spw_logo_file");
  const rSize     = qs("spw_size");
  const rRot      = qs("spw_rotate");
  const rX        = qs("spw_pos_x");
  const rY        = qs("spw_pos_y");

  function render() {
    if (!imgLogo || imgLogo.classList.contains("d-none")) return;
    const s  = parseFloat(rSize.value || "0.7");
    const r  = parseFloat(rRot.value || "0");
    const px = parseFloat(rX.value || "50");
    const py = parseFloat(rY.value || "60");

    imgLogo.style.left = px + "%";
    imgLogo.style.top  = py + "%";
    imgLogo.style.transform = `translate(-50%, -50%) scale(${s}) rotate(${r}deg)`;
  }

  // Cargar imagen (PNG/JPG/SVG) via FileReader como DataURL
  if (inputFile) {
    inputFile.addEventListener("change", function (e) {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = function () {
        imgLogo.src = reader.result;
        imgLogo.classList.remove("d-none");
        render();
      };
      reader.readAsDataURL(f);
    });
  }

  [rSize, rRot, rX, rY].forEach(function (el) {
    if (el) el.addEventListener("input", render);
  });

  // Volver
  const back = qs("spw_back");
  if (back) {
    back.addEventListener("click", function (e) {
      e.preventDefault();
      if (history.length > 1) history.back();
      else window.location.href = "/shop";
    });
  }

  // Añadir al carrito (sin guardar aún la imagen; se añade la variante)
  const add = qs("spw_add_to_cart");
  if (add) {
    add.addEventListener("click", function (e) {
      e.preventDefault();
      const variantId = add.dataset.variantId || add.dataset.fallbackVariantId;
      if (!variantId) return;
      // Redirección simple al endpoint estándar
      window.location.href = `/shop/cart/update?product_id=${variantId}&add_qty=1`;
    });
  }
})();