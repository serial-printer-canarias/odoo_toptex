/** @odoo-module **/
(function () {
  const root = document.querySelector(".spw-customizer");
  if (!root) return;

  const canvas = root.querySelector("#spw_canvas");
  const base = root.querySelector("#spw_product_img");
  if (!canvas || !base) return;

  // El canvas debe posicionar a los hijos
  canvas.style.position = "relative";

  // Overlay del logo (si no existe, lo creamos)
  let overlay = root.querySelector("#spw_logo_preview");
  if (!overlay) {
    overlay = document.createElement("img");
    overlay.id = "spw_logo_preview";
    overlay.alt = "Logo preview";
    Object.assign(overlay.style, {
      position: "absolute",
      top: "0",
      left: "0",
      zIndex: "999",                // siempre por encima
      display: "none",              // se muestra al cargar imagen
      pointerEvents: "none",
      transformOrigin: "top left",
      opacity: "1",
    });
    canvas.appendChild(overlay);
  }

  // Sliders (cogemos el que exista)
  const sliders = {
    size: root.querySelector("#spw_size, [data-spw='size'], input[data-spw-size], input[type='range'][name*='size']"),
    rot:  root.querySelector("#spw_rotate, [data-spw='rotate'], input[data-spw-rotate], input[type='range'][name*='rot']"),
    x:    root.querySelector("#spw_pos_x, [data-spw='posx'], input[data-spw-posx], input[type='range'][name*='pos_x']"),
    y:    root.querySelector("#spw_pos_y, [data-spw='posy'], input[data-spw-posy], input[type='range'][name*='pos_y']"),
  };

  function clamp(n, min, max) { return Math.min(max, Math.max(min, Number(n) || 0)); }
  function baseWidth() {
    const r = base.getBoundingClientRect();
    return r.width || base.width || 400;
  }

  function apply() {
    // si el tamaño está en 0, forzamos mínimo 10% para que nunca desaparezca
    const sRaw = sliders.size ? sliders.size.value : 100;
    const s = clamp(sRaw, 10, 300) / 100;   // 10%–300%
    const r = sliders.rot ? Number(sliders.rot.value || 0) : 0;
    const x = sliders.x ? Number(sliders.x.value || 0) : 0;
    const y = sliders.y ? Number(sliders.y.value || 0) : 0;
    overlay.style.transform = `translate(${x}px, ${y}px) rotate(${r}deg) scale(${s})`;
  }

  function showOverlayInitial() {
    // Ancho inicial visible = 35% del ancho del producto
    const w = Math.round(baseWidth() * 0.35);
    overlay.style.width = w + "px";
    overlay.style.height = "auto";
    overlay.style.display = "block";

    // Si el slider está en 0, lo llevamos a 100 (100%)
    if (sliders.size && (!sliders.size.value || Number(sliders.size.value) === 0)) {
      sliders.size.value = 100;
    }
    apply();
  }

  // Escuchamos TODOS los file inputs del panel por si cambia el id/name
  const fileInputs = root.querySelectorAll(
    '#spw_logo_input, input[type="file"][data-spw="logo"], input[name="spw_logo"], input[type="file"]'
  );
  fileInputs.forEach((inp) => {
    inp.addEventListener("change", (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      const url = URL.createObjectURL(f);
      overlay.onload = () => { showOverlayInitial(); };
      overlay.src = url;
    });
  });

  // Reaplicar al mover sliders
  Object.values(sliders).forEach((el) => { if (el) el.addEventListener("input", apply); });

  // Si cambia el tamaño del producto (responsive), mantén el logo proporcionado
  new ResizeObserver(() => {
    if (overlay.style.display !== "none") {
      overlay.style.width = Math.round(baseWidth() * 0.35) + "px";
      apply();
    }
  }).observe(base);
})();