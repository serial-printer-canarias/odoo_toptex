(function () {
  function byId(id) { return document.getElementById(id); }

  function init() {
    const canvas = byId("spw_canvas");
    const logo = byId("spw_logo_img");
    const inputFile = byId("spw_logo");
    const scale = byId("spw_scale");
    const rot = byId("spw_rotate");
    const posX = byId("spw_pos_x");
    const posY = byId("spw_pos_y");

    if (!canvas || !logo || !inputFile) return;

    // Cargar imagen subida
    inputFile.addEventListener("change", (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        logo.src = ev.target.result;
        logo.classList.remove("d-none");
        apply();
      };
      reader.readAsDataURL(f);
    });

    // Arrastrar con el dedo/ratón
    let dragging = false;
    let start = { x: 0, y: 0 };
    let origin = { x: 50, y: 50 };

    function pointerDown(ev) {
      if (ev.target !== logo) return;
      dragging = true;
      const rect = canvas.getBoundingClientRect();
      start = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
      origin = { x: +posX.value, y: +posY.value };
      ev.preventDefault();
    }
    function pointerMove(ev) {
      if (!dragging) return;
      const rect = canvas.getBoundingClientRect();
      const dx = ((ev.clientX - rect.left) - start.x) / rect.width * 100;
      const dy = ((ev.clientY - rect.top) - start.y) / rect.height * 100;
      posX.value = Math.max(0, Math.min(100, origin.x + dx));
      posY.value = Math.max(0, Math.min(100, origin.y + dy));
      apply();
    }
    function pointerUp() { dragging = false; }

    canvas.addEventListener("pointerdown", pointerDown);
    window.addEventListener("pointermove", pointerMove);
    window.addEventListener("pointerup", pointerUp);

    // Sliders
    [scale, rot, posX, posY].forEach(el => el && el.addEventListener("input", apply));

    // Colores (sólo ejemplo visual - si luego calculas precio, captura data-color)
    document.querySelectorAll(".spw-color").forEach(b => {
      b.addEventListener("click", () => {
        document.querySelectorAll(".spw-color").forEach(x => x.classList.remove("ring"));
        b.classList.add("ring");
        // aquí podrías guardar b.dataset.color
      });
    });

    // Posiciones rápidas
    document.querySelectorAll(".spw-pos").forEach(b => {
      b.addEventListener("click", () => {
        const rect = canvas.getBoundingClientRect();
        if (b.dataset.pos === "left") { posX.value = 30; posY.value = 40; }
        if (b.dataset.pos === "right") { posX.value = 70; posY.value = 40; }
        if (b.dataset.pos === "back") { posX.value = 50; posY.value = 60; }
        if (b.dataset.pos === "free") { /* no-op */ }
        apply();
      });
    });

    function apply() {
      const s = (+scale.value || 100) / 100;
      const r = +rot.value || 0;
      const x = +posX.value || 50;
      const y = +posY.value || 50;

      logo.style.left = x + "%";
      logo.style.top = y + "%";
      logo.style.transform = `translate(-50%, -50%) rotate(${r}deg) scale(${s})`;
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();