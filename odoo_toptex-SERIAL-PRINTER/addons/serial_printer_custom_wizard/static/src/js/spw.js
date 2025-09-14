/** addons/serial_printer_custom_wizard/static/src/js/spw.js **/
(function () {
  "use strict";

  // Helpers DOM
  const $ = (sel) => document.querySelector(sel);

  // Elementos
  const productImg = $("#spw_product_img");
  const logoImg    = $("#spw_logo_preview");
  const fileInput  = $("#spw_logo_input");
  const sizeRange  = $("#spw_size");
  const xRange     = $("#spw_pos_x");
  const yRange     = $("#spw_pos_y");
  const rotRange   = $("#spw_rotation");
  const qtyInput   = $("#spw_qty");
  const notesInput = $("#spw_notes");

  // Estado
  const state = {
    size: Number(sizeRange ? sizeRange.value : 100), // %
    x: Number(xRange ? xRange.value : 0),            // %
    y: Number(yRange ? yRange.value : 10),           // %
    rot: Number(rotRange ? rotRange.value : 0),      // deg
    isSVG: false,
    svgColor: "#000000",
    tech: "Serigrafía",
    dataUrl: null,
  };

  function applyTransform() {
    if (!logoImg) return;
    // Posicionamos por porcentaje relativo al contenedor
    logoImg.style.left = (50 + state.x) + "%";
    logoImg.style.top  = (60 + state.y) + "%";
    logoImg.style.transform = `translate(-50%, -50%) rotate(${state.rot}deg)`;
    // El tamaño es porcentaje del ancho visible del producto
    const baseW = productImg ? productImg.clientWidth : 300;
    const px = Math.max(10, (state.size / 100) * baseW);
    logoImg.style.width = px + "px";
    logoImg.classList.remove("d-none");
  }

  function readTechniqueAndColor() {
    const tech = document.querySelector("input[name='spw_tech']:checked");
    const col  = document.querySelector("input[name='spw_svg_color']:checked");
    state.tech = tech ? tech.value : "Serigrafía";
    state.svgColor = col ? col.value : "#000000";
  }

  // Cargar imagen / svg
  function onFileChange(e) {
    const f = e.target.files && e.target.files[0];
    if (!f || !logoImg) return;
    state.isSVG = (f.type === "image/svg+xml");

    const reader = new FileReader();
    reader.onload = (ev) => {
      let url = ev.target.result;
      // Si es SVG y el usuario eligió color, intentamos recolor por string replace
      if (state.isSVG) {
        try {
          readTechniqueAndColor();
          const colored = url
            .replace(/<svg/i, `<svg fill="${state.svgColor}"`)
            .replace(/fill="[^"]*"/gi, `fill="${state.svgColor}"`);
          url = colored;
        } catch (err) { /* no-op si falla recolor */ }
      }
      logoImg.src = url;
      logoImg.onload = () => applyTransform();
      logoImg.classList.remove("d-none");
    };
    if (state.isSVG) reader.readAsText(f);
    else reader.readAsDataURL(f);
  }

  // Sliders
  if (sizeRange)  sizeRange.addEventListener("input", (e) => { state.size = Number(e.target.value); applyTransform(); });
  if (xRange)     xRange.addEventListener("input", (e) => { state.x = Number(e.target.value); applyTransform(); });
  if (yRange)     yRange.addEventListener("input", (e) => { state.y = Number(e.target.value); applyTransform(); });
  if (rotRange)   rotRange.addEventListener("input", (e) => { state.rot = Number(e.target.value); applyTransform(); });
  if (fileInput)  fileInput.addEventListener("change", onFileChange);

  // Técnica / Color listeners (no rompen nada si no existen)
  document.querySelectorAll("input[name='spw_tech']").forEach(el => {
    el.addEventListener("change", () => readTechniqueAndColor());
  });
  document.querySelectorAll("input[name='spw_svg_color']").forEach(el => {
    el.addEventListener("change", () => {
      state.svgColor = el.value;
      // Si el logo es SVG, intentar recolorear recargando el src
      if (state.isSVG && logoImg && logoImg.src) {
        let txt = logoImg.src;
        try {
          txt = txt.replace(/fill=%22[^%]*%22/gi, `fill=%22${encodeURIComponent(state.svgColor)}%22`);
          logoImg.src = txt;
        } catch (err) { /* ignorar */ }
      }
    });
  });

  // Reset
  window.spwReset = function () {
    if (sizeRange) sizeRange.value = 100;
    if (xRange)    xRange.value = 0;
    if (yRange)    yRange.value = 10;
    if (rotRange)  rotRange.value = 0;
    state.size = 100; state.x = 0; state.y = 10; state.rot = 0;
    applyTransform();
  };

  // Render a canvas y devuelve dataURL PNG
  function renderPNG() {
    return new Promise((resolve) => {
      const base = new Image();
      base.crossOrigin = "anonymous";
      base.src = productImg.src;

      const logo = new Image();
      logo.crossOrigin = "anonymous";
      logo.src = logoImg.src;

      base.onload = () => {
        const ratio = base.width / productImg.clientWidth;
        const canvas = document.createElement("canvas");
        canvas.width  = base.width;
        canvas.height = base.height;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(base, 0, 0, canvas.width, canvas.height);

        logo.onload = () => {
          // Calcular posición y tamaño en px del lienzo original
          const wDisplay = parseFloat(logoImg.style.width || "0").toString().replace("px","") * 1;
          const w = Math.max(1, wDisplay * ratio);
          const h = w * (logo.height / logo.width);

          const cx = (0.5 + state.x/100) * canvas.width;   // centro en X
          const cy = (0.60 + state.y/100) * canvas.height; // centro en Y

          ctx.save();
          ctx.translate(cx, cy);
          ctx.rotate(state.rot * Math.PI / 180);
          ctx.drawImage(logo, -w/2, -h/2, w, h);
          ctx.restore();

          resolve(canvas.toDataURL("image/png"));
        };
        // Si el logo no existe aún, devolvemos solo el producto
        logo.onerror = () => resolve(canvas.toDataURL("image/png"));
      };
    });
  }

  // Descargar PNG
  window.spwDownload = async function () {
    const url = await renderPNG();
    const a = document.createElement("a");
    a.href = url;
    a.download = "personalizacion.png";
    document.body.appendChild(a);
    a.click();
    a.remove();
  };

  // Añadir al carrito
  window.spwAddToCart = async function () {
    readTechniqueAndColor();
    const preview = await renderPNG();

    const payload = {
      template_id: Number($("#spw_template_id")?.value || 0),
      variant_id:  Number($("#spw_variant_id")?.value || 0) || null,
      qty:         Number(qtyInput ? qtyInput.value : 1) || 1,
      notes:       notesInput ? notesInput.value : "",
      tech:        state.tech,
      svg_color:   state.svgColor,
      size:        state.size,
      pos_x:       state.x,
      pos_y:       state.y,
      rot:         state.rot,
      preview_png: preview, // dataURL
    };

    const resp = await fetch("/spw/add_to_cart", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();
    if (data && data.ok) {
      window.location.href = data.cart_url || "/shop/cart";
    }
  };

  // Primera aplicación de transform si ya hay imagen
  if (logoImg && logoImg.src) { logoImg.onload = applyTransform; }
})();