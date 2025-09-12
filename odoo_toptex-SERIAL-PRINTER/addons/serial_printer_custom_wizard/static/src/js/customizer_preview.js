/** SPW – Previsualización del logo subido (PNG/JPG/SVG)
 *  Mantiene los sliders actuales y no toca nada de variante/ficha.
 */
(function () {
  "use strict";

  function byId(id) { return document.getElementById(id); }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    var inputFile   = byId("spw_logo_input");
    var overlay     = byId("spw_logo_overlay");
    var sizeR       = byId("spw_size");
    var rotR        = byId("spw_rotation");
    var posXR       = byId("spw_pos_x");
    var posYR       = byId("spw_pos_y");
    var canvas      = byId("spw_canvas");

    if (!inputFile || !overlay || !canvas) {
      // Si no está en esta página, salimos silenciosamente.
      return;
    }

    // Estado actual de transformación
    var state = {
      scale: (sizeR ? parseInt(sizeR.value, 10) : 60) / 100,
      rot:   (rotR  ? parseInt(rotR.value, 10)  : 0),
      dx:    (posXR ? parseInt(posXR.value, 10) : 0),
      dy:    (posYR ? parseInt(posYR.value, 10) : 0),
    };

    function applyTransform() {
      // Posicionamos con left/top relativos al centro del canvas.
      overlay.style.left = "calc(50% + " + state.dx + "px)";
      overlay.style.top  = "calc(50% + " + state.dy + "px)";
      overlay.style.transform =
        "translate(-50%, -50%) scale(" + state.scale + ") rotate(" + state.rot + "deg)";
    }

    function showOverlay(dataUrl) {
      overlay.src = dataUrl;
      overlay.style.display = "block";
      applyTransform();
    }

    // Carga de archivo (PNG/JPG/SVG)
    inputFile.addEventListener("change", function (ev) {
      var file = ev.target.files && ev.target.files[0];
      if (!file) { return; }

      // Lee como DataURL y muestra
      var reader = new FileReader();
      reader.onload = function (e) {
        try {
          showOverlay(e.target.result);
        } catch (err) {
          console.error("SPW overlay error:", err);
        }
      };
      reader.readAsDataURL(file);
    });

    // Sliders
    if (sizeR) {
      sizeR.addEventListener("input", function () {
        state.scale = parseInt(sizeR.value, 10) / 100;
        applyTransform();
      });
    }
    if (rotR) {
      rotR.addEventListener("input", function () {
        state.rot = parseInt(rotR.value, 10) || 0;
        applyTransform();
      });
    }
    if (posXR) {
      posXR.addEventListener("input", function () {
        state.dx = parseInt(posXR.value, 10) || 0;
        applyTransform();
      });
    }
    if (posYR) {
      posYR.addEventListener("input", function () {
        state.dy = parseInt(posYR.value, 10) || 0;
        applyTransform();
      });
    }

    // Permite arrastrar el logo con el ratón/táctil (suave, sin romper sliders)
    (function enableDrag() {
      var dragging = false;
      var start = { x: 0, y: 0, dx: 0, dy: 0 };

      function onDown(e) {
        if (overlay.style.display === "none") { return; }
        dragging = true;
        var p = (e.touches && e.touches[0]) ? e.touches[0] : e;
        start.x = p.clientX;
        start.y = p.clientY;
        start.dx = state.dx;
        start.dy = state.dy;
        e.preventDefault();
      }
      function onMove(e) {
        if (!dragging) { return; }
        var p = (e.touches && e.touches[0]) ? e.touches[0] : e;
        var deltaX = p.clientX - start.x;
        var deltaY = p.clientY - start.y;
        state.dx = start.dx + deltaX;
        state.dy = start.dy + deltaY;
        if (posXR) posXR.value = state.dx;
        if (posYR) posYR.value = state.dy;
        applyTransform();
      }
      function onUp() { dragging = false; }

      canvas.addEventListener("mousedown", onDown);
      canvas.addEventListener("touchstart", onDown, { passive: false });
      window.addEventListener("mousemove", onMove);
      window.addEventListener("touchmove", onMove, { passive: false });
      window.addEventListener("mouseup", onUp);
      window.addEventListener("touchend", onUp);
    })();
  });
})();