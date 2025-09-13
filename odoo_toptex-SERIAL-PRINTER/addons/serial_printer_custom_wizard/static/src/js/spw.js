/** serial_printer_custom_wizard/static/src/js/spw.js **/
(function () {
  "use strict";

  // -------- util: obtener la variante actual de forma robusta ----------
  function getCurrentVariantId(scope) {
    const root = scope || document;

    // 1) estándar: hidden input name="product_id"
    const hidden = root.querySelector("input[name='product_id']");
    if (hidden && hidden.value && !isNaN(hidden.value)) {
      return parseInt(hidden.value, 10);
    }

    // 2) a veces el form lleva data-product-id
    const form = root.querySelector("form");
    if (form && form.dataset && form.dataset.productId && !isNaN(form.dataset.productId)) {
      return parseInt(form.dataset.productId, 10);
    }

    // 3) radio de atributos con data-product-id
    const checked = root.querySelector("[data-attribute_exclusions] input[type='radio'][name^='attribute_']:checked");
    if (checked && checked.dataset && checked.dataset.productId && !isNaN(checked.dataset.productId)) {
      return parseInt(checked.dataset.productId, 10);
    }

    // 4) último recurso: parámetro ?variant=123
    const m = location.search.match(/[?&]variant=(\d+)/);
    if (m) return parseInt(m[1], 10);

    return null;
  }

  // -------- PRODUCT PAGE: delegación de eventos para el botón ----------
  document.addEventListener("click", function (ev) {
    const btn = ev.target.closest("#spw_personalize_btn");
    if (!btn) return;

    ev.preventDefault();
    ev.stopPropagation();

    const scope = btn.closest("form") || document;
    const variantId = getCurrentVariantId(scope);

    if (!variantId) {
      console.warn("[SPW] No se pudo detectar la variante (product_id).");
      alert("No se ha podido detectar la variante seleccionada. Selecciona un color/talla e inténtalo de nuevo.");
      return;
    }
    window.location.assign(`/spw/customize/${variantId}`);
  });

  // -------- CUSTOMIZER: previsualización del logo (sin cambios de UX) ----------
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
      logo.style.transform =
        `translate(calc(-50% + ${state.posX}px), calc(-50% + ${state.posY}px)) ` +
        `rotate(${state.rotate}deg) ` +
        `scale(${state.scalePct / 100})`;
    }

    if (fileInput) {
      fileInput.addEventListener("change", function (e) {
        const file = e.target.files && e.target.files[0] ? e.target.files[0] : null;
        if (!file) return;

        const reader = new FileReader();
        reader.onload = function (ev) {
          logo.src = ev.target.result;
          logo.classList.remove("d-none");
          state.scalePct = 100; state.posX = 0; state.posY = 0; state.rotate = 0;
          if (sizeRange) sizeRange.value = "100";
          if (posXRange) posXRange.value = "0";
          if (posYRange) posYRange.value = "0";
          if (rotRange) rotRange.value = "0";
          applyTransform();
        };
        reader.readAsDataURL(file);
      });
    }

    if (sizeRange) sizeRange.addEventListener("input", () => { state.scalePct = parseInt(sizeRange.value || "100", 10); applyTransform(); });
    if (posXRange) posXRange.addEventListener("input", () => { state.posX = parseInt(posXRange.value || "0", 10); applyTransform(); });
    if (posYRange) posYRange.addEventListener("input", () => { state.posY = parseInt(posYRange.value || "0", 10); applyTransform(); });
    if (rotRange)  rotRange.addEventListener("input",  () => { state.rotate = parseInt(rotRange.value  || "0", 10); applyTransform(); });
    if (resetBtn)  resetBtn.addEventListener("click",  () => {
      state.scalePct = 100; state.posX = 0; state.posY = 0; state.rotate = 0;
      if (sizeRange) sizeRange.value = "100";
      if (posXRange) posXRange.value = "0";
      if (posYRange) posYRange.value = "0";
      if (rotRange)  rotRange.value  = "0";
      applyTransform();
    });

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
      state.posX = state.startPos.x + (cx - state.dragStart.x);
      state.posY = state.startPos.y + (cy - state.dragStart.y);
      if (posXRange) posXRange.value = String(state.posX);
      if (posYRange) posYRange.value = String(state.posY);
      applyTransform();
      ev.preventDefault();
    }
    function onPointerUp() { state.dragging = false; }

    logo.addEventListener("mousedown", onPointerDown);
    logo.addEventListener("touchstart", onPointerDown, { passive: false });
    window.addEventListener("mousemove", onPointerMove, { passive: false });
    window.addEventListener("touchmove", onPointerMove, { passive: false });
    window.addEventListener("mouseup", onPointerUp);
    window.addEventListener("touchend", onPointerUp);
  }

  document.addEventListener("DOMContentLoaded", initCustomizerPage);
})();