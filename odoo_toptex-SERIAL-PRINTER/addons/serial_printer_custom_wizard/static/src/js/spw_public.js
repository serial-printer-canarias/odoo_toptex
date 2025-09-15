// addons/serial_printer_custom_wizard/static/src/js/spw_public.js
(function () {
  "use strict";

  // utilidades mínimas
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  async function fileToDataURL(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = reject;
      r.readAsDataURL(file);
    });
  }

  async function loadImage(src) {
    return new Promise((resolve, reject) => {
      const im = new Image();
      im.crossOrigin = "anonymous";
      im.onload = () => resolve(im);
      im.onerror = reject;
      im.src = src;
    });
  }

  // espera al DOM
  window.addEventListener("DOMContentLoaded", async () => {
    // si no estamos en la página del personalizador, salimos
    const stage = $("#spw_canvas");
    if (!stage) return;

    // elementos
    const productImg = $("#spw_product_img");
    const logoImg = $("#spw_logo_preview");
    const inputFile = $("#spw_logo_input");
    const size = $("#spw_size");
    const posX = $("#spw_pos_x");
    const posY = $("#spw_pos_y");
    const rot = $("#spw_rotation");
    const qty = $("#spw_qty");
    const notes = $("#spw_notes");
    const btnCart = $("#spw_add_to_cart_btn");
    const btnPNG = $("#spw_download_png");

    // radios
    let svgColor = ($("input[name='spw_svg_color']:checked") || {}).value || "";
    let tech = ($("input[name='spw_tech']:checked") || {}).value || "";

    $all("input[name='spw_svg_color']").forEach(el => {
      el.addEventListener("change", () => { svgColor = el.value; });
    });
    $all("input[name='spw_tech']").forEach(el => {
      el.addEventListener("change", () => { tech = el.value; });
    });

    // archivo subido → previsualizar
    inputFile && inputFile.addEventListener("change", async () => {
      const f = inputFile.files && inputFile.files[0];
      if (!f) return;
      const dataUrl = await fileToDataURL(f);
      logoImg.src = dataUrl;
      logoImg.classList.remove("d-none");
      logoImg.style.opacity = "1";
      applyTransform();
    });

    // sliders → mover/escala/rotar
    [size, posX, posY, rot].forEach(el => {
      el && el.addEventListener("input", applyTransform);
    });

    function applyTransform() {
      const s = (parseInt(size.value || "100", 10) / 100) || 1;
      const x = parseInt(posX.value || "0", 10) || 0;
      const y = parseInt(posY.value || "0", 10) || 0;
      const r = parseInt(rot.value || "0", 10) || 0;
      // partimos del 50%/60% que ya fija el CSS
      logoImg.style.transform =
        `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) rotate(${r}deg) scale(${s})`;
    }

    // render a canvas para descargar/enviar
    async function renderCanvas() {
      const base = await loadImage(productImg.getAttribute("src"));
      const c = document.createElement("canvas");
      c.width = base.naturalWidth || base.width;
      c.height = base.naturalHeight || base.height;
      const ctx = c.getContext("2d");

      // fondo (producto)
      ctx.drawImage(base, 0, 0, c.width, c.height);

      // overlay (logo) si existe
      if (logoImg.src && !logoImg.classList.contains("d-none") && logoImg.complete) {
        const logo = await loadImage(logoImg.src);
        // posición relativa al tamaño del stage
        const stageBox = stage.getBoundingClientRect();
        const baseBox = productImg.getBoundingClientRect();
        const relX = (logoImg.getBoundingClientRect().left - baseBox.left) / baseBox.width;
        const relY = (logoImg.getBoundingClientRect().top - baseBox.top) / baseBox.height;
        const relW = (logoImg.getBoundingClientRect().width) / baseBox.width;

        const x = relX * c.width;
        const y = relY * c.height;
        const w = relW * c.width;
        const h = w * (logo.naturalHeight / logo.naturalWidth);

        // rot/escala ya están “horneados” en la posición/tamaño arriba
        ctx.drawImage(logo, x, y, w, h);
      }
      return c;
    }

    // Descargar PNG
    btnPNG && btnPNG.addEventListener("click", async (ev) => {
      ev.preventDefault();
      try {
        const canvas = await renderCanvas();
        // Safari/iOS abre visor nativo; el resto descarga directo
        canvas.toBlob((blob) => {
          if (!blob) return;
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "personalizacion.png";
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(() => URL.revokeObjectURL(url), 1500);
        }, "image/png");
      } catch (e) {
        alert("No se pudo generar el PNG.");
        console.error(e);
      }
    });

    // Añadir al carrito con la personalización
    btnCart && btnCart.addEventListener("click", async (ev) => {
      ev.preventDefault();
      try {
        const variantId = parseInt(($("#spw_variant_id") || {}).value || "0", 10) || 0;
        const q = Math.max(1, parseInt(qty && qty.value || "1", 10) || 1);

        // el PNG de la composición
        const canvas = await renderCanvas();
        const pngB64 = canvas.toDataURL("image/png").split(",")[1] || "";

        const payload = {
          variant_id: variantId,
          qty: q,
          tech: tech || "",
          svg_color: svgColor || "",
          notes: (notes && notes.value || "").trim(),
          png_b64: pngB64,
        };

        const resp = await fetch("/spw/add_to_cart", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          credentials: "same-origin",
        });

        const json = await resp.json().catch(() => null);
        if (!resp.ok || !json || json.ok === false) {
          const msg = (json && json.message) || "Error añadiendo al carrito.";
          alert(msg);
          return;
        }
        window.location = json.cart_url || "/shop/cart";
      } catch (e) {
        console.error(e);
        alert("Error añadiendo al carrito.");
      }
    });

    // Reset (si tienes el botón con window.spwReset)
    window.spwReset = function () {
      inputFile && (inputFile.value = "");
      logoImg && (logoImg.src = "", logoImg.classList.add("d-none"));
      size && (size.value = "100");
      posX && (posX.value = "0");
      posY && (posY.value = "10");
      rot && (rot.value = "0");
      applyTransform();
    };
  });
})();