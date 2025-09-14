// addons/serial_printer_custom_wizard/static/src/js/spw_cart.js
(function () {
  "use strict";

  function $(sel) { return document.querySelector(sel); }

  function getNumber(el, defVal) {
    const v = parseFloat((el && el.value) || defVal);
    return isFinite(v) ? v : defVal;
  }

  /** Devuelve {canvas, dataURL} con el render base+logo en resolución nativa */
  async function composeCanvas() {
    const baseImg = $("#spw_product_img");
    const logoImgEl = $("#spw_logo_preview");
    if (!baseImg) throw new Error("No se encuentra #spw_product_img");

    // Espera a que cargue la base si es necesario
    if (!baseImg.complete || !baseImg.naturalWidth) {
      await new Promise(res => {
        baseImg.addEventListener("load", res, { once: true });
        baseImg.addEventListener("error", res, { once: true });
      });
    }

    const natW = baseImg.naturalWidth || baseImg.width;
    const natH = baseImg.naturalHeight || baseImg.height;
    const canvas = document.createElement("canvas");
    canvas.width = natW;
    canvas.height = natH;
    const ctx = canvas.getContext("2d");

    // Dibuja la base
    ctx.drawImage(baseImg, 0, 0, natW, natH);

    // Si no hay logo cargado, termina
    if (!logoImgEl || !logoImgEl.src) {
      return { canvas, dataURL: canvas.toDataURL("image/png") };
    }

    // Medidas en pantalla y escala a píxeles nativos
    const baseRect = baseImg.getBoundingClientRect();
    const logoRect = logoImgEl.getBoundingClientRect();
    const scale = natW / baseRect.width;

    const x = (logoRect.left - baseRect.left) * scale;
    const y = (logoRect.top - baseRect.top) * scale;
    const w = logoRect.width * scale;
    const h = logoRect.height * scale;

    // Rotación (grados → radianes)
    const rotEl = $("#spw_rotation");
    const angle = getNumber(rotEl, 0) * Math.PI / 180;

    // Carga el logo en objeto Image para dibujarlo
    const temp = new Image();
    // data:URL o misma web => sin CORS
    temp.src = logoImgEl.src;
    await new Promise((res) => {
      if (temp.complete) return res();
      temp.onload = () => res();
      temp.onerror = () => res();
    });

    // Centro del logo
    const cx = x + w / 2;
    const cy = y + h / 2;

    ctx.save();
    ctx.translate(cx, cy);
    if (angle) ctx.rotate(angle);
    ctx.drawImage(temp, -w / 2, -h / 2, w, h);
    ctx.restore();

    const dataURL = canvas.toDataURL("image/png");
    return { canvas, dataURL };
  }

  /** Descarga PNG */
  async function spwDownload() {
    try {
      const { dataURL } = await composeCanvas();
      const a = document.createElement("a");
      a.href = dataURL;
      a.download = "personalizacion.png";
      // Soporte iOS/Safari
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (e) {
      console.error(e);
      alert("No se pudo generar el PNG.");
    }
  }

  /** Añade al carrito con cantidad y adjunta PNG + nota */
  async function spwAddToCart() {
    try {
      const variantId = parseInt(($("#spw_variant_id") && $("#spw_variant_id").value) || "0", 10);
      const templateId = parseInt(($("#spw_template_id") && $("#spw_template_id").value) || "0", 10);
      const qty = Math.max(1, parseInt(($("#spw_qty") && $("#spw_qty").value) || "1", 10));

      if (!variantId && !templateId) {
        alert("Falta el producto/variante.");
        return;
      }

      const tech = (document.querySelector('input[name="spw_tech"]:checked') || {}).value || "";
      const svgColor = (document.querySelector('input[name="spw_svg_color"]:checked') || {}).value || "";
      const notes = ($("#spw_notes") && $("#spw_notes").value) || "";

      const size = getNumber($("#spw_size"), 100);
      const posX = getNumber($("#spw_pos_x"), 0);
      const posY = getNumber($("#spw_pos_y"), 10);
      const rotation = getNumber($("#spw_rotation"), 0);

      const { dataURL } = await composeCanvas();

      const payload = {
        variant_id: variantId || false,
        template_id: templateId || false,
        qty: qty,
        tech: tech,
        svg_color: svgColor,
        notes: notes,
        size: size,
        pos_x: posX,
        pos_y: posY,
        rotation: rotation,
        image_dataurl: dataURL,
      };

      const resp = await fetch("/spw/add_to_cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        credentials: "same-origin",
      });
      const json = await resp.json();
      if (!json || !json.ok) {
        console.error(json);
        alert("No se pudo añadir al carrito.");
        return;
      }
      // Ir al carrito
      window.location.href = "/shop/cart";
    } catch (e) {
      console.error(e);
      alert("Ocurrió un problema al añadir al carrito.");
    }
  }

  // Exponer funciones globales que ya llama la plantilla
  window.spwDownload = spwDownload;
  window.spwAddToCart = spwAddToCart;
})();