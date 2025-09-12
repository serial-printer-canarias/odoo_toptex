/** @odoo-module **/

// SOLO: previsualizar el logo que sube el cliente sobre la imagen de la variante.
// No toca menús ni controles que ya tengas.

(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const fileInput  = document.querySelector("#spw_file");
    const previewImg = document.querySelector("#spw_logo_preview");
    const baseImg    = document.querySelector("#spw_product_img");

    // Si tu página no tiene alguno de estos, salimos sin romper nada.
    if (!fileInput || !previewImg || !baseImg) return;

    // Estado por defecto (no cambia tu UI actual)
    const state = {
      widthPct: 30,  // % del ancho del producto
      rot: 0,        // grados
      x: 50,         // % desde la izquierda
      y: 60,         // % desde arriba (aprox. zona del dobladillo)
    };

    function applyTransform() {
      previewImg.style.position  = "absolute";
      previewImg.style.left      = state.x + "%";
      previewImg.style.top       = state.y + "%";
      previewImg.style.width     = state.widthPct + "%";
      previewImg.style.height    = "auto";
      previewImg.style.transform = `translate(-50%, -50%) rotate(${state.rot}deg)`;
      previewImg.style.pointerEvents = "none";
      previewImg.style.zIndex    = "5";
      previewImg.style.opacity   = "1";
      previewImg.classList.remove("d-none");
    }

    function showPreview(dataUrl) {
      previewImg.onload = () => applyTransform();
      previewImg.src = dataUrl;
    }

    // ── Carga del archivo local (PNG/JPG/SVG) ──────────────────────────────────
    fileInput.addEventListener("change", (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      if (f.size > 10 * 1024 * 1024) {
        alert("El archivo supera 10MB.");
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => showPreview(e.target.result);
      reader.readAsDataURL(f); // compatible para PNG/JPG/SVG
    });

    // ── SI EXISTEN, enganchamos tus sliders/botones actuales (no los creamos) ─
    const sSize = document.getElementById("spw_size");
    const sRot  = document.getElementById("spw_rotation");
    const sX    = document.getElementById("spw_pos_x");
    const sY    = document.getElementById("spw_pos_y");
    const btnReset = document.getElementById("spw_reset");

    if (sSize) {
      state.widthPct = +sSize.value || state.widthPct;
      sSize.addEventListener("input", () => { state.widthPct = +sSize.value || 30; applyTransform(); });
    }
    if (sRot) {
      state.rot = +sRot.value || 0;
      sRot.addEventListener("input", () => { state.rot = +sRot.value || 0; applyTransform(); });
    }
    if (sX) {
      state.x = +sX.value || 50;
      sX.addEventListener("input", () => { state.x = +sX.value || 50; applyTransform(); });
    }
    if (sY) {
      state.y = +sY.value || 60;
      sY.addEventListener("input", () => { state.y = +sY.value || 60; applyTransform(); });
    }
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        fileInput.value = "";
        previewImg.classList.add("d-none");
        // Vuelve al estado por defecto sin tocar tu UI
        state.widthPct = 30; state.rot = 0; state.x = 50; state.y = 60;
      });
    }
  });
})();