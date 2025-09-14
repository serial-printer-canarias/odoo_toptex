// addons/serial_printer_custom_wizard/static/src/js/spw_cart.js
(function () {
  "use strict";

  // Utilidades
  const $ = (sel) => document.querySelector(sel);
  const num = (el, defVal) => {
    const v = parseFloat((el && el.value) || defVal);
    return Number.isFinite(v) ? v : defVal;
  };

  // Componer PNG de la previsualización (NUNCA rechaza: siempre resuelve)
  function composeCanvas() {
    return new Promise(async (resolve) => {
      try {
        const baseImg = $("#spw_product_img");
        const logoImg = $("#spw_logo_preview");
        if (!baseImg) throw new Error("No se encuentra #spw_product_img");

        if (!baseImg.complete || !baseImg.naturalWidth) {
          await new Promise((r) => {
            baseImg.addEventListener("load", r, { once: true });
            baseImg.addEventListener("error", r, { once: true });
          });
        }

        const natW = baseImg.naturalWidth  || baseImg.width  || 1200;
        const natH = baseImg.naturalHeight || baseImg.height || 1200;

        const canvas = document.createElement("canvas");
        canvas.width = natW;
        canvas.height = natH;
        const ctx = canvas.getContext("2d");

        // Dibuja base
        ctx.drawImage(baseImg, 0, 0, natW, natH);

        // Dibuja logo con posición/escala actuales
        if (logoImg && logoImg.src) {
          const baseRect = baseImg.getBoundingClientRect();
          const logoRect = logoImg.getBoundingClientRect();
          const scale = natW / (baseRect.width || 1);

          const x = (logoRect.left - baseRect.left) * scale;
          const y = (logoRect.top  - baseRect.top ) * scale;
          const w = (logoRect.width  || 0) * scale;
          const h = (logoRect.height || 0) * scale;

          const angle = num($("#spw_rotation"), 0) * Math.PI / 180;

          const tmp = new Image();
          tmp.crossOrigin = "anonymous";
          tmp.src = logoImg.src;
          await new Promise((r) => { if (tmp.complete) r(); else { tmp.onload = r; tmp.onerror = r; } });

          const cx = x + w / 2;
          const cy = y + h / 2;
          ctx.save();
          ctx.translate(cx, cy);
          if (angle) ctx.rotate(angle);
          ctx.drawImage(tmp, -w / 2, -h / 2, w, h);
          ctx.restore();
        }

        resolve({ canvas, dataURL: canvas.toDataURL("image/png") });
      } catch (e) {
        console.error(e);
        const c = document.createElement("canvas");
        c.width = 10; c.height = 10;
        resolve({ canvas: c, dataURL: c.toDataURL("image/png"), error: e });
      }
    });
  }

  // --------- BOTÓN: DESCARGAR PNG ----------
  function spwDownload() {
    composeCanvas()
      .then(({ dataURL }) => {
        try {
          const a = document.createElement("a");
          a.href = dataURL;
          a.download = "personalizacion.png";
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
        } catch (e) {
          console.error(e);
          alert("No se pudo iniciar la descarga del PNG.");
        }
      })
      .catch((e) => {
        // Nunca debería entrar aquí, pero por si acaso
        console.error(e);
      });
  }

  // --------- BOTÓN: AÑADIR AL CARRITO ----------
  function spwAddToCart() {
    // Lee valores del formulario
    const variantId  = parseInt(($("#spw_variant_id") && $("#spw_variant_id").value) || "0", 10);
    const templateId = parseInt(($("#spw_template_id") && $("#spw_template_id").value) || "0", 10);
    const qty        = Math.max(1, parseInt(($("#spw_qty") && $("#spw_qty").value) || "1", 10));

    const tech      = (document.querySelector('input[name="spw_tech"]:checked') || {}).value || "";
    const svgColor  = (document.querySelector('input[name="spw_svg_color"]:checked') || {}).value || "";
    const notes     = ($("#spw_notes") && $("#spw_notes").value) || "";

    const size     = num($("#spw_size"), 100);
    const pos_x    = num($("#spw_pos_x"), 0);
    const pos_y    = num($("#spw_pos_y"), 10);
    const rotation = num($("#spw_rotation"), 0);

    composeCanvas()
      .then(({ dataURL }) => {
        const payload = {
          variant_id: variantId || false,
          template_id: templateId || false,
          qty, tech, svg_color: svgColor, notes,
          size, pos_x, pos_y, rotation,
          image_dataurl: dataURL,
        };
        return fetch("/spw/add_to_cart", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "same-origin",
          body: JSON.stringify(payload),
        });
      })
      .then((resp) => resp.json().catch(() => ({ ok: False, error: "Respuesta no JSON" })))
      .then((json) => {
        if (!json || json.ok !== true) {
          console.error(json);
          alert("No se pudo añadir al carrito.\n" + (json && json.error ? json.error : ""));
          return;
        }
        window.location.href = "/shop/cart";
      })
      .catch((e) => {
        console.error(e);
        alert("Error añadiendo al carrito.");
      });
  }

  // Exponer global para tus onclick existentes
  window.spwDownload = spwDownload;
  window.spwAddToCart = spwAddToCart;

  // Enganchar por ID (por si no usas onclick). Evita que href="#" navegue.
  function bindButtons() {
    const d = document.getElementById("spw_download_btn");
    const a = document.getElementById("spw_add_to_cart_btn");
    if (d) d.addEventListener("click", (ev) => { ev.preventDefault(); ev.stopPropagation(); spwDownload(); });
    if (a) a.addEventListener("click", (ev) => { ev.preventDefault(); ev.stopPropagation(); spwAddToCart(); });
  }

  // Odoo carga dinámico → enganchamos en DOMContentLoaded y también con fallback
  document.addEventListener("DOMContentLoaded", bindButtons);
  window.addEventListener("load", bindButtons);
  setTimeout(bindButtons, 800); // fallback por si el DOM se repinta
})();