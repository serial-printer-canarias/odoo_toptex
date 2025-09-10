/**
 * Serial Printer – Customizer Preview (Frontend)
 * - Muestra el logo subido encima de la imagen del producto
 * - Controles: tamaño (%), rotación (º), posición X/Y (%)
 * - Guarda un JSON oculto con toda la personalización antes de enviar el formulario
 *
 * Requiere en la plantilla estos IDs (ya los tienes):
 *  - spw_preview             (div contenedor relativo)
 *  - spw_product_img         (img base del producto)
 *  - spw_logo                (img overlay del logo)
 *  - spw_logo_input          (input[type=file])
 *  - spw_size, spw_rotate    (input[type=range])
 *  - spw_pos_x, spw_pos_y    (input[type=range])
 *  - spw_tech, spw_position  (selects)
 *  - spw_color               (input/select para color)
 *  - spw_add_to_cart         (botón submit)
 *  - spw_payload             (input[type=hidden] name=spw_customization_json) – si no existe se crea
 *  - spw_form (opcional)     (form de personalización). Si no existe, se usa el primer <form> de la página.
 */
(function () {
  const $ = (id) => document.getElementById(id);
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  const asNum = (v, def) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : def;
  };

  function getProductId() {
    // 1) si el contenedor tiene data-product-id
    const cont = $("spw_preview");
    if (cont && cont.dataset && cont.dataset.productId) {
      return cont.dataset.productId;
    }
    // 2) input oculto de Odoo
    const hid = document.querySelector('input[name="product_id"]');
    if (hid && hid.value) return hid.value;
    return null;
  }

  function ensureHiddenPayload() {
    let input = $("spw_payload");
    if (!input) {
      const form = $("spw_form") || document.querySelector("form") || document.body;
      input = document.createElement("input");
      input.type = "hidden";
      input.id = "spw_payload";
      input.name = "spw_customization_json";
      form.appendChild(input);
    }
    return input;
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
    } else {
      fn();
    }
  }

  ready(() => {
    const preview   = $("spw_preview");
    if (!preview) return; // No estamos en la página de personalización

    const productImg = $("spw_product_img");
    const logoImg    = $("spw_logo");

    const inpFile = $("spw_logo_input");
    const inpSize = $("spw_size");
    const inpRot  = $("spw_rotate");
    const inpX    = $("spw_pos_x");
    const inpY    = $("spw_pos_y");

    const selTech = $("spw_tech");
    const selPos  = $("spw_position");
    const inpCol  = $("spw_color");

    const btnAdd  = $("spw_add_to_cart");
    const hidden  = ensureHiddenPayload();

    // Valores por defecto (por si los controles vienen vacíos)
    if (inpSize && !inpSize.value) inpSize.value = "22";
    if (inpRot  && !inpRot.value)  inpRot.value  = "0";
    if (inpX    && !inpX.value)    inpX.value    = "50";
    if (inpY    && !inpY.value)    inpY.value    = "50";

    // ---------- Pintado ----------
    function applyTransform() {
      if (!logoImg) return;
      const size = asNum(inpSize && inpSize.value, 22); // en %
      const rot  = asNum(inpRot && inpRot.value, 0);    // en grados
      const x    = clamp(asNum(inpX && inpX.value, 50), 0, 100);
      const y    = clamp(asNum(inpY && inpY.value, 50), 0, 100);

      logoImg.style.width = size + "%";
      logoImg.style.left  = x + "%";
      logoImg.style.top   = y + "%";
      logoImg.style.transform = `translate(-50%, -50%) rotate(${rot}deg)`;
    }

    // ---------- Carga del logo ----------
    function loadLogoFromFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        if (logoImg) {
          logoImg.src = ev.target.result;
          logoImg.classList.remove("hidden");
          applyTransform();
        }
      };
      reader.readAsDataURL(file);
    }

    inpFile && inpFile.addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      loadLogoFromFile(f);
    });

    // ---------- Drag sobre la imagen para posicionar ----------
    let dragging = false;
    function updateXYFromPointer(ev) {
      if (!productImg || !inpX || !inpY) return;
      const rect = productImg.getBoundingClientRect();
      const px = clamp(((ev.clientX - rect.left) / rect.width) * 100, 0, 100);
      const py = clamp(((ev.clientY - rect.top) / rect.height) * 100, 0, 100);
      inpX.value = String(px.toFixed(2));
      inpY.value = String(py.toFixed(2));
      applyTransform();
    }

    preview.addEventListener("pointerdown", (ev) => {
      dragging = true;
      updateXYFromPointer(ev);
      preview.setPointerCapture && preview.setPointerCapture(ev.pointerId);
    });
    preview.addEventListener("pointermove", (ev) => {
      if (!dragging) return;
      updateXYFromPointer(ev);
    });
    preview.addEventListener("pointerup", (ev) => {
      dragging = false;
      preview.releasePointerCapture && preview.releasePointerCapture(ev.pointerId);
    });
    window.addEventListener("resize", applyTransform);

    // ---------- Controles ----------
    [inpSize, inpRot, inpX, inpY].forEach((el) => {
      el && el.addEventListener("input", applyTransform);
      el && el.addEventListener("change", applyTransform);
    });

    // ---------- Guardado del JSON antes de enviar ----------
    function buildPayload() {
      const payload = {
        v: 1,
        product_id: getProductId(),
        tech: selTech ? selTech.value : "",
        color: inpCol ? inpCol.value : "",
        position: selPos ? selPos.value : "",
        size_pct: asNum(inpSize && inpSize.value, 22),
        rotate_deg: asNum(inpRot && inpRot.value, 0),
        pos_x_pct: asNum(inpX && inpX.value, 50),
        pos_y_pct: asNum(inpY && inpY.value, 50),
        // Nota: guardar el dataURL del logo en el JSON.
        // Si te preocupa el tamaño, en backend puedes procesarlo y limpiarlo.
        logo_data_url: (logoImg && logoImg.src && !logoImg.classList.contains("hidden")) ? logoImg.src : "",
      };
      return payload;
    }

    function beforeSubmit() {
      const payload = buildPayload();
      hidden.value = JSON.stringify(payload);
    }

    // Si el botón es submit, guardamos justo antes del envío
    if (btnAdd) {
      btnAdd.addEventListener("click", () => {
        beforeSubmit();
      });
    }
    // Por si el usuario envía el form con Enter
    const form = $("spw_form") || btnAdd && btnAdd.closest("form") || document.querySelector("form");
    if (form) {
      form.addEventListener("submit", () => {
        beforeSubmit();
      });
    }

    // Primera aplicación de estilos (por si hay valores precargados)
    applyTransform();
  });
})();