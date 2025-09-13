/** serial_printer_custom_wizard/static/src/js/spw.js **/

(function () {
  "use strict";

  // ==== FICHA DE PRODUCTO: Navegar a la página de personalización con la variante seleccionada ====
  function initProductPage() {
    const btn = document.getElementById("spw_personalize_btn");
    if (!btn) return;

    btn.addEventListener("click", function (ev) {
      ev.preventDefault();
      // Buscar el form que contiene el input name=product_id (variante actual)
      const form = btn.closest("form") || document.querySelector("form");
      if (!form) return;

      const variantInput = form.querySelector("input[name='product_id']");
      const variantId = variantInput && variantInput.value ? parseInt(variantInput.value, 10) : null;
      if (!variantId) {
        console.warn("[SPW] No se encontró product_id (variante).");
        return;
      }
      window.location.href = `/spw/customize/${variantId}`;
    });
  }

  // ==== PÁGINA DE PERSONALIZACIÓN: Previsualizar logo sobre imagen de variante ====
  function initCustomizerPage() {
    const canvas = document.getElementById("spw_canvas");
    const baseImg = document.getElementById("spw_product_img");
    const logo = document.getElementById("spw_logo_preview");
    const fileInput = document.getElementById("spw_logo_input");
    const sizeRange = document.getElementById("spw_size");
    const posXRange = document.getElementById("spw_pos_x");
    const posYRange = document.getElementById("spw_pos_y");
    const rotRange = document.getElementById("spw_rotate");
    const resetBtn = document.getElementById("spw_reset");

    if (!canvas || !baseImg || !logo) return;

    // Estado del overlay
    const state = {
      scalePct: 100,
      posX: 0,
      posY: 0,
      rotate: 0,
      dragging: false,
      dragStart: { x: 0, y: 0 },
      startPos: { x: 0, y: 0 },
    };

    function applyTransform() {
      // Colocamos el centro en el centro del canvas (50%, 50%) y aplicamos offsets y transform
      logo.style.transform =
        `translate(calc(-50% + ${state.posX}px), calc(-50% + ${state.posY}px)) ` +
        `rotate(${state.rotate}deg) ` +
        `scale(${state.scalePct / 100})`;
    }

    // Input file -> mostrar logo
    if (fileInput) {
      fileInput.addEventListener("change", function (e) {
        const file = e.target.files && e.target.files[0] ? e.target.files[0] : null;
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (ev) {
          logo.src = ev.target.result;
          logo.classList.remove("d-none");

          // Reset básico
          state.scalePct = 100;
          state.posX = 0;
          state.posY = 0;
          state.rotate = 0;
          if (sizeRange) sizeRange.value = String(state.scalePct);
          if (posXRange) posXRange.value = String(state.posX);
          if (posYRange) posYRange.value = String(state.posY);
          if (rotRange) rotRange.value = String(state.rotate);
          applyTransform();
        };
        reader.readAsDataURL(file);
      });
    }

    // Controles
    if (sizeRange) {
      sizeRange.addEventListener("input", () => {
        state.scalePct = parseInt(sizeRange.value || "100", 10);
        applyTransform();
      });
    }
    if (posXRange) {
      posXRange.addEventListener("input", () => {
        state.posX = parseInt(posXRange.value || "0", 10);
        applyTransform();
      });
    }
    if (posYRange) {
      posYRange.addEventListener("input", () => {
        state.posY = parseInt(posYRange.value || "0", 10);
        applyTransform();
      });
    }
    if (rotRange) {
      rotRange.addEventListener("input", () => {
        state.rotate = parseInt(rotRange.value || "0", 10);
        applyTransform();
      });
    }
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        state.scalePct = 100;
        state.posX = 0;
        state.posY = 0;
        state.rotate = 0;
        if (sizeRange) sizeRange.value = "100";
        if (posXRange) posXRange.value = "0";
        if (posYRange) posYRange.value = "0";
        if (rotRange) rotRange.value = "0";
        applyTransform();
      });
    }

    // Arrastrar el logo con el ratón / touch
    function onPointerDown(ev) {
      if (logo.classList.contains("d-none")) return;
      state.dragging = true;
      state.dragStart.x = ev.clientX || (ev.touches && ev.touches[0].clientX) || 0;
      state.dragStart.y = ev.clientY || (ev.touches && ev.touches[0].clientY) || 0;
      state.startPos.x = state.posX;
      state.startPos.y = state.posY;
      ev.preventDefault();
    }
    function onPointerMove(ev) {
      if (!state.dragging) return;
      const cx = ev.clientX || (ev.touches && ev.touches[0].clientX) || 0;
      const cy = ev.clientY || (ev.touches && ev.touches[0].clientY) || 0;
      const dx = cx - state.dragStart.x;
      const dy = cy - state.dragStart.y;
      state.posX = state.startPos.x + dx;
      state.posY = state.startPos.y + dy;
      if (posXRange) posXRange.value = String(state.posX);
      if (posYRange) posYRange.value = String(state.posY);
      applyTransform();
      ev.preventDefault();
    }
    function onPointerUp() {
      state.dragging = false;
    }

    logo.addEventListener("mousedown", onPointerDown);
    logo.addEventListener("touchstart", onPointerDown, { passive: false });
    window.addEventListener("mousemove", onPointerMove, { passive: false });
    window.addEventListener("touchmove", onPointerMove, { passive: false });
    window.addEventListener("mouseup", onPointerUp);
    window.addEventListener("touchend", onPointerUp);
  }

  // Init
  document.addEventListener("DOMContentLoaded", function () {
    initProductPage();
    initCustomizerPage();
  });
})();