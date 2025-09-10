/** @odoo-module **/

// Previsualización sencilla del logo sobre la imagen del producto.
(function () {
    const $ = (sel) => document.querySelector(sel);

    function updateTransforms() {
        const logo = $("#spw_logo_preview");
        if (!logo || logo.classList.contains("d-none")) return;

        const scale = ($("#spw_scale")?.value || 100) / 100;
        const rot = parseInt($("#spw_rotate")?.value || "0", 10);
        const px = parseInt($("#spw_posx")?.value || "50", 10);
        const py = parseInt($("#spw_posy")?.value || "50", 10);

        logo.style.transform = `translate(-50%, -50%) translate(${px}%, ${py}%) rotate(${rot}deg) scale(${scale})`;
        logo.style.transformOrigin = "center center";
    }

    function wireControls() {
        ["#spw_scale", "#spw_rotate", "#spw_posx", "#spw_posy"].forEach((id) => {
            const el = $(id);
            if (el) el.addEventListener("input", updateTransforms);
        });
    }

    document.addEventListener("DOMContentLoaded", () => {
        const file = $("#spw_logo");
        const logo = $("#spw_logo_preview");
        if (!file || !logo) return;

        wireControls();

        file.addEventListener("change", (ev) => {
            const f = ev.target.files?.[0];
            if (!f) return;
            const reader = new FileReader();
            reader.onload = () => {
                logo.src = reader.result;
                logo.classList.remove("d-none");
                updateTransforms();
            };
            reader.readAsDataURL(f);
        });

        // Permite arrastrar el logo (desktop)
        let dragging = false;
        let start = { x: 0, y: 0 };
        const stage = document.querySelector(".spw-stage");
        if (stage && logo) {
            logo.addEventListener("mousedown", (e) => {
                dragging = true;
                start = { x: e.clientX, y: e.clientY };
                e.preventDefault();
            });
            document.addEventListener("mouseup", () => (dragging = false));
            document.addEventListener("mousemove", (e) => {
                if (!dragging) return;
                const rect = stage.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                $("#spw_posx").value = Math.max(0, Math.min(100, Math.round(x)));
                $("#spw_posy").value = Math.max(0, Math.min(100, Math.round(y)));
                updateTransforms();
            });
        }

        // (opcional) botón "Añadir al carrito" – aquí sólo haríamos POST a un endpoint
        // con los parámetros de personalización. Lo dejamos a futuro si tu flujo lo requiere.
        const addBtn = $("#spw_add_to_cart");
        if (addBtn) {
            addBtn.addEventListener("click", () => {
                // TODO: enviar info al backend/linea de venta
                alert("Personalización preparada (demo). Integraremos el POST al carrito en el siguiente paso.");
            });
        }
    });
})();