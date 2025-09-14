// addons/serial_printer_custom_wizard/static/src/js/spw_cart.js
(function () {
  "use strict";

  function q(sel) { return document.querySelector(sel); }
  function num(el, defVal) {
    const v = parseFloat((el && el.value) || defVal);
    return isFinite(v) ? v : defVal;
  }

  // Componer un PNG con la base + el logo en posición/escala/rotación actual
  function composeCanvas() {
    return new Promise(async (resolve) => {
      try {
        const baseImg = q("#spw_product_img");
        const logoImg = q("#spw_logo_preview");
        if (!baseImg) throw new Error("No se encuentra #spw_product_img");

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

        ctx.drawImage(baseImg, 0, 0, natW, natH);

        if (logoImg && logoImg.src) {
          const baseRect = baseImg.getBoundingClientRect();
          const logoRect = logoImg.getBoundingClientRect();
          const scale = natW / baseRect.width;

          const x = (logoRect.left - baseRect.left) * scale;
          const y = (logoRect.top  - baseRect.top ) * scale;
          const w = logoRect.width  * scale;
          const h = logoRect.height * scale;

          const angle = num(q("#spw_rotation"), 0) * Math.PI / 180;

          const temp = new Image();
          temp.src = logoImg.src;
          await new Promise(r => { if (temp.complete) r(); else { temp.onload = r; temp.onerror = r; }});

          const cx = x + w/2, cy = y + h/2;
          ctx.save();
          ctx.translate(cx, cy);
          if (angle) ctx.rotate(angle);
          ctx.drawImage(temp, -w/2, -h/2, w, h);
          ctx.restore();
        }

        resolve({ canvas, dataURL: canvas.toDataURL("image/png") });
      } catch (e) {
        // Nunca rechazar: devolvemos canvas vacío para evitar uncaught
        const c = document.createElement("canvas");
        c.width = 10; c.height = 10;
        resolve({ canvas: c, dataURL: c.toDataURL("image/png"), error: e });
      }
    });
  }

  // --- Botón: Descargar PNG ---
  function spwDownload() {
    composeCanvas().then(({ dataURL, error }) => {
      if (error) console.error(error);
      const a = document.createElement("a");
      a.href = dataURL;
      a.download = "personalizacion.png";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }).catch((e) => {
      console.error(e);
      alert("No se pudo generar el PNG.");
    });
  }

  // --- Botón: Añadir al carrito con esta personalización ---
  function spwAddToCart() {
    const variantId = parseInt((q("#spw_variant_id") && q("#spw_variant_id").value) || "0", 10);
    const templateId = parseInt((q("#spw_template_id") && q("#spw_template_id").value) || "0", 10);
    const qty       = Math.max(1, parseInt((q("#spw_qty") && q("#spw_qty").value) || "1", 10));

    const tech      = (document.querySelector('input[name="spw_tech"]:checked') || {}).value || "";
    const svgColor  = (document.querySelector('input[name="spw_svg_color"]:checked') || {}).value || "";
    const notes     = (q("#spw_notes") && q("#spw_notes").value) || "";

    const size      = num(q("#spw_size"), 100);
    const posX      = num(q("#spw_pos_x"), 0);
    const posY      = num(q("#spw_pos_y"), 10);
    const rotation  = num(q("#spw_rotation"), 0);

    composeCanvas().then(({ dataURL }) => {
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

      return fetch("/spw/add_to_cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify(payload),
      });
    }).then((resp) => {
      // Si el endpoint no existe (no importado en __init__), resp no será JSON
      return resp.json().catch(() => ({ ok: false, error: "Respuesta no JSON (¿ruta no cargada?)" }));
    }).then((json) => {
      if (!json.ok) {
        console.error(json);
        alert("No se pudo añadir al carrito.\n" + (json.error || ""));
        return;
      }
      window.location.href = "/shop/cart";
    }).catch((e) => {
      console.error(e);
      alert("Ocurrió un problema al añadir al carrito.");
    });
  }

  // Exponer en global (para los onclick existentes)
  window.spwDownload = spwDownload;
  window.spwAddToCart = spwAddToCart;

  // Y además, enganchar por ID si existen (no rompe nada)
  document.addEventListener("DOMContentLoaded", () => {
    const d = q("#spw_download_btn");
    const a = q("#spw_add_to_cart_btn");
    if (d) d.addEventListener("click", (ev) => { ev.preventDefault(); spwDownload(); });
    if (a) a.addEventListener("click", (ev) => { ev.preventDefault(); spwAddToCart(); });
  });
})();