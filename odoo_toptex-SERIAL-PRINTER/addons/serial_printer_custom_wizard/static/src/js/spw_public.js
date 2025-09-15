// addons/serial_printer_custom_wizard/static/src/js/spw_public.js
(function () {
  "use strict";
  console.log("[SPW] spw_public.js cargado");
  // ... (tu mismo contenido a partir de aquí, sin cambios)
})();

// addons/serial_printer_custom_wizard/static/src/js/spw_public.js
(function () {
  "use strict";

  // Helpers DOM
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  // Carga de imagen asegurando onload/promesa
  async function loadImage(src) {
    return new Promise((resolve, reject) => {
      const im = new Image();
      im.crossOrigin = "anonymous";
      im.onload = () => resolve(im);
      im.onerror = reject;
      im.src = src;
    });
  }

  // Lee fichero a dataURL
  function readAsDataURL(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(r.result);
      r.onerror = reject;
      r.readAsDataURL(file);
    });
  }

  // Convierte dataURL -> base64 (sin prefijo)
  function dataURLtoBase64(dataURL) {
    const comma = dataURL.indexOf(',');
    return comma !== -1 ? dataURL.slice(comma + 1) : dataURL;
  }

  // Estado global muy pequeño
  const S = {
    productImg: null,
    logoDataURL: "",     // dataURL del logo cargado por el usuario
    isSVG: false,        // si el logo es SVG
  };

  // Inicializa controles
  async function init() {
    const productImgEl = $("#spw_product_img");
    const logoEl = $("#spw_logo_preview");
    const logoInput = $("#spw_logo_input");

    // Guardamos referencia
    S.productImg = productImgEl;

    // Handle subida de logo
    logoInput.addEventListener("change", async (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      const name = (f.name || "").toLowerCase();
      S.isSVG = name.endsWith(".svg");
      const dataURL = await readAsDataURL(f);
      S.logoDataURL = dataURL;
      logoEl.src = dataURL;
      logoEl.classList.remove("d-none");
      logoEl.style.opacity = "1";
      // reset tamaño/pos por si venimos de otro
      applyTransform();
    });

    // Sliders
    ["spw_size", "spw_pos_x", "spw_pos_y", "spw_rotation"].forEach(id => {
      const el = $("#" + id);
      if (el) el.addEventListener("input", applyTransform);
    });

    // Reset
    window.spwReset = function () {
      $("#spw_size").value = 100;
      $("#spw_pos_x").value = 0;
      $("#spw_pos_y").value = 10;
      $("#spw_rotation").value = 0;
      applyTransform();
    };

    // Botón descargar PNG
    $("#spw_download_png").addEventListener("click", async () => {
      try {
        const pngDataURL = await renderPNGDataURL();
        const a = document.createElement("a");
        a.href = pngDataURL;
        a.download = "personalizacion.png";
        document.body.appendChild(a);
        a.click();
        a.remove();
      } catch (e) {
        alert("No se pudo generar el PNG.");
        // console.error(e);
      }
    });

    // Botón añadir al carrito
    $("#spw_add_to_cart").addEventListener("click", async () => {
      const variantId = ($("#spw_variant_id").value || "").trim();
      const qty = parseInt(($("#spw_qty").value || "1"), 10) || 1;
      const tech = ($("input[name='spw_tech']:checked") || {}).value || "";
      const svgColor = ($("input[name='spw_svg_color']:checked") || {}).value || "";
      const notes = ($("#spw_notes").value || "").trim();

      if (!variantId) {
        alert("Falta la variante del producto.");
        return;
      }

      // Generamos PNG del montaje (aunque no haya logo, se adjunta base para el taller)
      let pngB64 = "";
      try {
        const dataURL = await renderPNGDataURL();
        pngB64 = dataURLtoBase64(dataURL);
      } catch (e) {
        // si falla, seguimos sin PNG
      }

      const payload = {
        variant_id: parseInt(variantId, 10),
        qty: qty,
        tech: tech,
        svg_color: svgColor,
        notes: notes,
        png_b64: pngB64,
      };

      try {
        const resp = await fetch("/spw/add_to_cart", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify(payload),
        });
        const data = await resp.json();
        if (data && data.ok) {
          window.location.href = data.cart_url || "/shop/cart";
        } else {
          alert(data && data.message ? data.message : "Error añadiendo al carrito.");
        }
      } catch (e) {
        alert("No se pudo añadir al carrito.");
      }
    });

    // Primera aplicación de transform
    applyTransform();
  }

  // Aplica transform en el overlay según sliders
  function applyTransform() {
    const logo = $("#spw_logo_preview");
    if (!logo) return;
    const size = parseInt($("#spw_size").value || "100", 10);
    const posX = parseInt($("#spw_pos_x").value || "0", 10);
    const posY = parseInt($("#spw_pos_y").value || "10", 10);
    const rot = parseInt($("#spw_rotation").value || "0", 10);

    // El overlay parte del 50%/60% centrado; desplazamos en %
    const tx = -50 + posX;
    const ty = -50 + posY;

    logo.style.transform = `translate(${tx}%, ${ty}%) rotate(${rot}deg)`;
    logo.style.width = size + "px";
  }

  // Render del montaje a PNG (dataURL)
  async function renderPNGDataURL() {
    const baseSrc = $("#spw_img_src").value || ($("#spw_product_img").getAttribute("src") || "");
    if (!baseSrc) throw new Error("Sin imagen base.");

    // Cargamos imágenes
    const baseIm = await loadImage(baseSrc);

    // Canvas del tamaño del base
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    canvas.width = baseIm.naturalWidth || baseIm.width;
    canvas.height = baseIm.naturalHeight || baseIm.height;

    // Dibujar base
    ctx.drawImage(baseIm, 0, 0, canvas.width, canvas.height);

    // Logo (si hay)
    if (S.logoDataURL) {
      // Para posicionar en canvas calculemos desde el overlay actual
      const overlay = $("#spw_logo_preview");
      // Tamaño destino (en px del canvas) proporcional al ancho del canvas
      const sizePx = parseInt($("#spw_size").value || "100", 10);
      // Convertimos posición (%) del translate aplicado
      const posX = parseInt($("#spw_pos_x").value || "0", 10);
      const posY = parseInt($("#spw_pos_y").value || "10", 10);

      // Partimos del 50%/60% del canvas
      let cx = canvas.width * 0.5;
      let cy = canvas.height * 0.6;

      // Ajuste por sliders (en % de la imagen, aprox. 1% = 1% ancho/alto)
      cx += (posX / 100) * canvas.width;
      cy += (posY / 100) * canvas.height;

      const rot = (parseInt($("#spw_rotation").value || "0", 10) * Math.PI) / 180;

      // Dibujar logo
      const logoIm = await loadImage(S.logoDataURL);
      const ratio = logoIm.naturalWidth ? (sizePx / logoIm.naturalWidth) : 1;
      const drawW = logoIm.naturalWidth * ratio;
      const drawH = logoIm.naturalHeight * ratio;

      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rot);
      ctx.drawImage(logoIm, -drawW / 2, -drawH / 2, drawW, drawH);
      ctx.restore();
    }

    return canvas.toDataURL("image/png");
  }

  // Arranque
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();