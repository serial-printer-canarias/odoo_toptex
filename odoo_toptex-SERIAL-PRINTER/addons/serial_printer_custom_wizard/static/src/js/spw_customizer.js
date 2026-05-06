/** @odoo-module **/

// Lógica de previsualización; solo actúa si existe #spw_canvas
document.addEventListener("DOMContentLoaded", () => {
    const stage = document.querySelector("#spw_canvas");
    if (!stage) return; // así no carga nada en el resto del sitio

    const logo = stage.querySelector("#spw_logo_preview");
    const fileInput = document.querySelector("#spw_logo_input");
    const size = document.querySelector("#spw_size");
    const rot = document.querySelector("#spw_rotate");
    const posX = document.querySelector("#spw_posx");
    const posY = document.querySelector("#spw_posy");

    const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

    function update() {
        if (!logo || !logo.dataset.loaded) return;
        const s = (Number(size?.value || 70)) / 100;   // 0.1–1.5
        const a = Number(rot?.value || 0);             // -180–180
        const x = clamp(Number(posX?.value || 50), 0, 100);
        const y = clamp(Number(posY?.value || 60), 0, 100);
        logo.style.left = `${x}%`;
        logo.style.top = `${y}%`;
        logo.style.transform = `translate(-50%, -50%) rotate(${a}deg) scale(${s})`;
    }

    fileInput?.addEventListener("change", (e) => {
        const f = e.target.files && e.target.files[0];
        if (!f) return;

        const url = URL.createObjectURL(f);
        logo.src = url;
        logo.classList.remove("d-none");
        logo.dataset.loaded = "1";
        logo.onload = () => URL.revokeObjectURL(url);
        update();
    });

    [size, rot, posX, posY].forEach((el) => el?.addEventListener("input", update));

    // Arrastrar el logo
    let dragging = false;
    logo?.addEventListener("mousedown", (ev) => { dragging = true; ev.preventDefault(); });
    window.addEventListener("mouseup", () => { dragging = false; });
    stage.addEventListener("mousemove", (ev) => {
        if (!dragging) return;
        const rect = stage.getBoundingClientRect();
        const px = ((ev.clientX - rect.left) / rect.width) * 100;
        const py = ((ev.clientY - rect.top) / rect.height) * 100;
        if (posX) posX.value = clamp(px, 0, 100);
        if (posY) posY.value = clamp(py, 0, 100);
        update();
    });
});