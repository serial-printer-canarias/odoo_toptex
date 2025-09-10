/** SPW – Customizer logic (Odoo 18, frontend) */
document.addEventListener("DOMContentLoaded", () => {
  const qs  = (sel, el=document) => el.querySelector(sel);
  const qsa = (sel, el=document) => [...el.querySelectorAll(sel)];

  const stage   = qs("#spw_stage");
  const baseImg = qs("#spw_base");
  const logoImg = qs("#spw_logo");
  const handle  = qs("#spw_handle");

  const inFile  = qs("#spw_file");
  const fileName= qs("#spw_file_name");
  const rScale  = qs("#spw_scale");
  const rRotate = qs("#spw_rotate");
  const rPosX   = qs("#spw_pos_x");
  const rPosY   = qs("#spw_pos_y");

  const paletteBox = qs("#spw_palette");
  const colorHex   = qs("#spw_color_hex");
  const colorName  = qs("#spw_color_name");
  const colorLabel = qs("#spw_color_label");

  const addBtn  = qs("#spw_add_to_cart_custom");
  const container = qs("#spw_container");
  const productId = parseInt(container?.dataset.productId || "0", 10) || 0;

  /* —— 1) Paleta NS300 (aprox.) ———
     Sustituye/ajusta los hex si tienes la carta oficial.
  */
  const NS300 = [
    {name:"White",   hex:"#FFFFFF"},
    {name:"Black",   hex:"#000000"},
    {name:"Navy",    hex:"#13294B"},
    {name:"Royal",   hex:"#0057B8"},
    {name:"Red",     hex:"#D0021B"},
    {name:"Burgundy",hex:"#75151E"},
    {name:"Orange",  hex:"#FF6A00"},
    {name:"Yellow",  hex:"#FFD100"},
    {name:"Bottle",  hex:"#0B5741"},
    {name:"Kelly",   hex:"#00A86B"},
    {name:"Purple",  hex:"#5B2C83"},
    {name:"Brown",   hex:"#5C4033"},
    {name:"Grey",    hex:"#808080"},
    {name:"Light Grey", hex:"#BDBDBD"},
  ];

  function buildPalette() {
    paletteBox.innerHTML = "";
    NS300.forEach((c, idx) => {
      const b = document.createElement("button");
      b.className = "spw-swatch";
      b.title = c.name;
      b.style.setProperty("--swatch", c.hex);
      b.setAttribute("type","button");
      b.setAttribute("data-hex", c.hex);
      b.setAttribute("data-name", c.name);
      if (idx === 1) b.classList.add("active"); // Black por defecto
      b.addEventListener("click", () => selectColor(c.hex, c.name, b));
      paletteBox.appendChild(b);
    });
    // valor inicial
    selectColor(NS300[1].hex, NS300[1].name, paletteBox.children[1]);
  }
  function selectColor(hex, name, btn) {
    qsa(".spw-swatch", paletteBox).forEach(x => x.classList.remove("active"));
    btn?.classList.add("active");
    colorHex.value  = hex;
    colorName.value = name;
    colorLabel.textContent = `${name} (${hex})`;
    // No re-coloreamos el PNG (lo guardamos para el pedido).
  }

  /* —— 2) Subida del logo ——— */
  inFile?.addEventListener("change", (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    fileName.textContent = f.name;
    const r = new FileReader();
    r.onload = () => {
      logoImg.src = r.result;
      logoImg.classList.add("visible");
      // Centrar y valores neutros
      rScale.value = 100; rRotate.value = 0; rPosX.value = 50; rPosY.value = 50;
      applyTransform();
    };
    r.readAsDataURL(f);
  });

  /* —— 3) Presets de posición ——— */
  const PRESETS = {
    chest_left:  { x: 32, y: 42, s: 60, rot: 0 },
    chest_right: { x: 68, y: 42, s: 60, rot: 0 },
    back:        { x: 50, y: 28, s: 90, rot: 0 },
  };
  qsa("input[name='spw_preset']").forEach(r => {
    r.addEventListener("change", () => {
      if (r.value === "none") return;
      const p = PRESETS[r.value];
      if (!p) return;
      rPosX.value = p.x; rPosY.value = p.y;
      rScale.value = p.s; rRotate.value = p.rot;
      applyTransform();
    });
  });

  /* —— 4) Sliders —— */
  [rScale, rRotate, rPosX, rPosY].forEach(inp => {
    inp?.addEventListener("input", applyTransform);
  });

  function applyTransform() {
    // Usamos % relativos al tamaño visible del stage
    const xPct = Number(rPosX.value);
    const yPct = Number(rPosY.value);
    const scale = Number(rScale.value) / 100;
    const rot = Number(rRotate.value);

    logoImg.style.setProperty("--x", `${xPct}%`);
    logoImg.style.setProperty("--y", `${yPct}%`);
    logoImg.style.setProperty("--scale", scale);
    logoImg.style.setProperty("--rot", `${rot}deg`);
    // Mover handle al centro del logo
    handle.style.left = `calc(${xPct}% - 12px)`;
    handle.style.top  = `calc(${yPct}% - 12px)`;
  }

  /* —— 5) Drag (mouse/touch) —— */
  let dragging = false;
  function startDrag(ev) {
    dragging = true;
    ev.preventDefault();
  }
  function moveDrag(ev) {
    if (!dragging) return;
    const rect = stage.getBoundingClientRect();
    const px = (("touches" in ev ? ev.touches[0].clientX : ev.clientX) - rect.left) / rect.width;
    const py = (("touches" in ev ? ev.touches[0].clientY : ev.clientY) - rect.top ) / rect.height;
    rPosX.value = Math.min(100, Math.max(0, Math.round(px*100)));
    rPosY.value = Math.min(100, Math.max(0, Math.round(py*100)));
    applyTransform();
  }
  function endDrag(){ dragging = false; }

  [stage, handle].forEach(el => {
    el.addEventListener("mousedown", startDrag);
    window.addEventListener("mousemove", moveDrag);
    window.addEventListener("mouseup", endDrag);

    el.addEventListener("touchstart", startDrag, {passive:false});
    window.addEventListener("touchmove", moveDrag, {passive:false});
    window.addEventListener("touchend", endDrag);
  });

  /* —— 6) Añadir al carrito (guardamos parámetros en query para el paso siguiente)
        Aquí mantenemos el flujo existente en tu botón.
        Si más adelante quieres grabarlo en attachment/JSON, lo hacemos.
  */
  addBtn?.addEventListener("click", async (e) => {
    e.preventDefault();

    const params = new URLSearchParams({
      product_id: String(productId || 0),
      type: (qs("input[name='spw_type']:checked")?.value || "none"),
      color_hex: colorHex.value,
      color_name: colorName.value,
      scale: rScale.value,
      rotate: rRotate.value,
      x: rPosX.value,
      y: rPosY.value,
    });

    // Si hay imagen cargada, la subimos como dataURL en sessionStorage (temporal)
    // y la recogeremos en el step de carrito/checkout con otro script.
    if (logoImg.src?.startsWith("data:")) {
      try {
        sessionStorage.setItem("spw_logo_dataurl", logoImg.src);
      } catch (_) {}
    }

    // Redirige al add-to-cart nativo con los parámetros de personalización
    // (podrás leerlos en el carrito para render/guardar).
    window.location.href = `/shop/cart/update?product_id=${productId}&add_qty=1&${params.toString()}`;
  });

  // init
  buildPalette();
  applyTransform();
});