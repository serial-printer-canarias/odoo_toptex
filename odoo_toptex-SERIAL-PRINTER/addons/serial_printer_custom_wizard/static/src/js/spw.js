/** @odoo-module **/

function $(sel) { return document.querySelector(sel); }

function initPreview() {
    const productImg = $('#spw_product_img');
    const logoInput  = $('#spw_logo_input');
    const logoPrev   = $('#spw_logo_preview');
    const size   = $('#spw_size');
    const posX   = $('#spw_pos_x');
    const posY   = $('#spw_pos_y');
    const rotate = $('#spw_rotate');

    if (!productImg || !logoInput || !logoPrev) return;

    // Carga del logo (PNG/JPG/SVG) -> previsualizar sobre la foto
    logoInput.addEventListener('change', (e) => {
        const f = e.target.files && e.target.files[0];
        if (!f) return;

        const url = URL.createObjectURL(f);
        logoPrev.src = url;
        logoPrev.classList.remove('d-none');

        // reset pos/size básicas
        size.value = '40';
        posX.value = '0';
        posY.value = '0';
        rotate.value = '0';
        applyTransform();
    });

    function applyTransform() {
        // tamaño relativo al ancho del canvas
        const pct = parseInt(size.value || '40', 10);
        logoPrev.style.width = `${pct}%`;

        // posicionamiento relativo (translate adicional en px)
        const tx = parseInt(posX.value || '0', 10);
        const ty = parseInt(posY.value || '0', 10);
        const rot = parseInt(rotate.value || '0', 10);

        logoPrev.style.transform =
          `translate(-50%, -50%) translate(${tx}px, ${ty}px) rotate(${rot}deg)`;
        logoPrev.style.opacity = '1';
    }

    [size, posX, posY, rotate].forEach(inp => {
        if (inp) inp.addEventListener('input', applyTransform);
    });
}

document.addEventListener('DOMContentLoaded', initPreview);