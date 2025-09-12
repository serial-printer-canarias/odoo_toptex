/** @odoo-module **/
(function () {
  // Ejecutar solo en la página del customizer
  const root = document.querySelector(".spw-customizer");
  if (!root) return;

  const canvas = root.querySelector("#spw_canvas");
  const baseImg = root.querySelector("#spw_product_img");
  if (!canvas || !baseImg) return;

  // Aseguramos contexto para posicionar
  canvas.style.position = "relative";

  // Crear (o reutilizar) overlay del logo
  let overlay = root.querySelector("#spw_logo_preview");
  if (!overlay) {
    overlay = document.createElement("img");
    overlay.id = "spw_logo_preview";
    overlay.alt = "Logo preview";
    overlay.style.position = "absolute";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.zIndex = "5";              // SIEMPRE por encima
    overlay.style.pointerEvents = "none";
    overlay.style.display = "none";          // se muestra al cargar imagen
    overlay.style.transformOrigin = "top left";
    canvas.appendChild(overlay);
  }

  // Inputs (tolerantes: coge el que exista)
  const fileInput = root.querySelector(
    '#spw_logo_input, input[type="file"][data-spw="logo"], input[name="spw_logo"], input[type="file"]'
  );
  const size = root.querySelector("#spw_size, [data-spw='size'], input[data-spw-size], input[type='range'][name*='size']");
  const rot  = root.querySelector("#spw_rotate, [data-spw='rotate'], input[data-spw-rotate], input[type='range'][name*='rot']");
  const posX = root.querySelector("#spw_pos_x, [data-spw='posx'], input[data-spw-posx], input[type='range'][name*='pos_x']");
  const posY = root.querySelector("#spw_pos_y, [data-spw='posy'], input[data-spw-posy], input[type='range'][name*='pos_y']");

  // Calcula ancho base visible (en px) para dar tamaño inicial al logo (25%)
  function baseWidthPx() {
    const r = baseImg.getBoundingClientRect();
    return Math.max(1, Math.round(r.width || baseImg.width || 400));
  }

  // Aplica transformaciones del panel
  function applyTransforms() {
    const s = size ? Number(size.value || 100) / 100 : 1; // 1 = 100%
    const r = rot  ? Number(rot.value  || 0)   : 0;
    const x = posX ? Number(posX.value || 0)   : 0;
    const y = posY ? Number(posY.value || 0)   : 0;
    overlay.style.transform = `translate(${x}px, ${y}px) rotate(${r}deg) scale(${s})`;
  }

  // Cuando cambie el archivo, mostramos el overlay con tamaño visible
  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;

      const url = URL.createObjectURL(f); // más rápido que FileReader
      overlay.onload = () => {
        // ancho inicial = 25% del ancho de la imagen base
        const targetW = Math.round(baseWidthPx() * 0.25);
        overlay.style.width = `${targetW}px`;
        overlay.style.height = "auto";
        overlay.style.display = "block";
        applyTransforms();
      };
      overlay.src = url;
    });
  }

  // Reaplicar al mover sliders
  [size, rot, posX, posY].forEach((el) => el && el.addEventListener("input", applyTransforms));

  // Si la imagen base cambia de tamaño (responsive), reajustamos ancho del logo
  const ro = new ResizeObserver(() => {
    if (overlay.style.display !== "none" && overlay.naturalWidth) {
      const targetW = Math.round(baseWidthPx() * 0.25);
      overlay.style.width = `${targetW}px`;
      applyTransforms();
    }
  });
  ro.observe(baseImg);
})();