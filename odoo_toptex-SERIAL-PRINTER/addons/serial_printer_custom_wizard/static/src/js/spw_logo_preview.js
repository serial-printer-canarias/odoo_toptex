// Ejecuta SOLO en la página del customizer y no toca nada más.
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(() => {
    const fileInput = document.getElementById("spw_logo_input");
    if (!fileInput) return; // si no hay input, no hacemos nada

    // Contenedor y overlay
    const canvas =
      document.getElementById("spw_canvas") ||
      document.querySelector(".spw-canvas") ||
      fileInput.closest("main")?.querySelector("#spw_canvas");
    if (!canvas) return;

    let preview = document.getElementById("spw_logo_preview");
    if (!preview) {
      preview = document.createElement("img");
      preview.id = "spw_logo_preview";
      preview.className = "spw-logo-preview d-none";
      canvas.appendChild(preview);
    }

    // Mostrar/ocultar preview
    function showPreviewFromFile(file) {
      if (!file) return;
      const url = URL.createObjectURL(file);
      preview.src = url;
      preview.onload = () => {
        // tamaño inicial: 30% del ancho del canvas
        const cw = canvas.clientWidth || 600;
        preview.style.width = Math.round(cw * 0.3) + "px";
        preview.classList.remove("d-none");
      };
    }

    fileInput.addEventListener("change", (ev) => {
      const f = ev.target.files && ev.target.files[0];
      showPreviewFromFile(f);
    });

    // Soporte por si existe un botón reset con ese id (no obligamos a tenerlo)
    const resetBtn = document.getElementById("spw_reset_btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        preview.classList.add("d-none");
        preview.removeAttribute("src");
        try { fileInput.value = ""; } catch (_) {}
      });
    }
  });
})();