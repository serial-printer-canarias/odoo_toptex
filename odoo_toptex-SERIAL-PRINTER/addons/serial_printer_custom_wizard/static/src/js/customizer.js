/** @odoo-module **/
(function () {
  // Solo ejecuta en la página del customizer
  const root = document.querySelector(".spw-customizer");
  if (!root) return;

  const canvas = root.querySelector("#spw_canvas");
  const baseImg = root.querySelector("#spw_product_img");
  if (!canvas || !baseImg) return;

  // Overlay de previsualización del logo
  let overlay = root.querySelector("#spw_logo_preview");
  if (!overlay) {
    overlay = document.createElement("img");
    overlay.id = "spw_logo_preview";
    overlay.style.position = "absolute";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.transformOrigin = "top left";
    overlay.style.pointerEvents = "none";
    overlay.style.display = "none";
    canvas.style.position = "relative";
    canvas.appendChild(overlay);
  }

  // Selectores tolerantes (coja el que exista en tu HTML)
  const fileInput = root.querySelector(
    '#spw_logo_input, input[type="file"][data-spw="logo"], input[type="file"][name="spw_logo"], input[type="file"]'
  );
  const size = root.querySelector("#spw_size, [data-spw='size'], input[data-spw-size]");
  const rot = root.querySelector("#spw_rotate, [data-spw='rotate'], input[data-spw-rotate]");
  const posX = root.querySelector("#spw_pos_x, [data-spw='posx'], input[data-spw-posx]");
  const posY = root.querySelector("#spw_pos_y, [data-spw='posy'], input[data-spw-posy]");

  function apply() {
    const s = size ? Number(size.value || 100) / 100 : 1;
    const r = rot ? Number(rot.value || 0) : 0;
    const x = posX ? Number(posX.value || 0) : 0;
    const y = posY ? Number(posY.value || 0) : 0;
    overlay.style.transform = `translate(${x}px, ${y}px) rotate(${r}deg) scale(${s})`;
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = () => {
        overlay.src = reader.result;
        overlay.style.display = "block";
        apply();
      };
      reader.readAsDataURL(f);
    });
  }

  [size, rot, posX, posY].forEach((el) => el && el.addEventListener("input", apply));
})();