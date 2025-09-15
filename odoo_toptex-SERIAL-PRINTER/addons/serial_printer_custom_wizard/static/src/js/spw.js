odoo.define('serial_printer_custom_wizard.spw', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    let gLogoB64 = '';      // DataURL del archivo original (con prefijo)
    let gLogoName = '';
    let gLogoMime = '';
    let gIsSvg = false;
    let gSvgOriginal = '';  // texto SVG original para recolorear

    function $(sel) { return document.querySelector(sel); }

    function currentTech() {
        const el = document.querySelector('input[name="spw_tech"]:checked');
        return el ? el.value : '';
    }
    function currentSvgColor() {
        const el = document.querySelector('input[name="spw_svg_color"]:checked');
        return el ? el.value : '';
    }

    function applyTransforms() {
        const size = parseInt($('#spw_size').value || '100', 10);
        const posX = parseInt($('#spw_pos_x').value || '0', 10);
        const posY = parseInt($('#spw_pos_y').value || '10', 10);
        const rot  = parseInt($('#spw_rotation').value || '0', 10);

        const logo = $('#spw_logo_preview');
        const scale = size / 100.0;
        logo.style.transform = `translate(-50%, -50%) translate(${posX}%, ${posY}%) rotate(${rot}deg) scale(${scale})`;
        logo.style.opacity = '1';
        logo.classList.remove('d-none');
    }

    function resetAll() {
        $('#spw_size').value = 100;
        $('#spw_pos_x').value = 0;
        $('#spw_pos_y').value = 10;
        $('#spw_rotation').value = 0;
        applyTransforms();
    }

    function recolorSvgAndShow() {
        if (!gIsSvg || !gSvgOriginal) return;
        const color = currentSvgColor() || '#000000';
        // reemplaza fill/stroke que no sean 'none'
        let svgTxt = gSvgOriginal
            .replace(/fill="(?!none)[^"]*"/gi, `fill="${color}"`)
            .replace(/stroke="(?!none)[^"]*"/gi, `stroke="${color}"`);
        const blob = new Blob([svgTxt], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        const img = $('#spw_logo_preview');
        img.onload = () => { URL.revokeObjectURL(url); applyTransforms(); };
        img.src = url;
        img.classList.remove('d-none');
        img.style.opacity = '1';
    }

    function handleFileInput(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;

        gLogoName = file.name || 'logo_original';
        gLogoMime = file.type || 'application/octet-stream';
        gIsSvg = (file.type === 'image/svg+xml');
        gSvgOriginal = '';

        if (gIsSvg) {
            // guardamos DataURL y también el texto para recolor
            const r1 = new FileReader();
            r1.onload = e => { gLogoB64 = e.target.result; };
            r1.readAsDataURL(file);

            const r2 = new FileReader();
            r2.onload = e => { gSvgOriginal = e.target.result || ''; recolorSvgAndShow(); };
            r2.readAsText(file);
        } else {
            const reader = new FileReader();
            reader.onload = function (e) {
                gLogoB64 = e.target.result; // data:
                const img = $('#spw_logo_preview');
                img.src = gLogoB64;
                img.onload = applyTransforms;
                img.classList.remove('d-none');
                img.style.opacity = '1';
            };
            reader.readAsDataURL(file);
        }
    }

    function makeCanvasPngBase64() {
        const node = $('#spw_canvas');
        return html2canvas(node, {
            useCORS: true,
            allowTaint: false,
            backgroundColor: null,
            scale: window.devicePixelRatio > 1 ? 2 : 1,
            imageTimeout: 0,
        }).then(canvas => canvas.toDataURL('image/png').replace(/^data:image\/png;base64,/, ''));
    }

    function downloadPNG() {
        const node = $('#spw_canvas');
        html2canvas(node, {
            useCORS: true,
            allowTaint: false,
            backgroundColor: null,
            scale: window.devicePixelRatio > 1 ? 2 : 1,
            imageTimeout: 0,
        }).then(canvas => {
            if (canvas.toBlob) {
                canvas.toBlob(blob => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'personalizacion.png';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 800);
                }, 'image/png');
            } else {
                const a = document.createElement('a');
                a.href = canvas.toDataURL('image/png');
                a.download = 'personalizacion.png';
                document.body.appendChild(a);
                a.click();
                a.remove();
            }
        });
    }

    async function addToCart() {
        try {
            const variantId = parseInt($('#spw_variant_id').value || '0', 10);
            const qty = Math.max(1, parseInt($('#spw_qty').value || '1', 10));
            const tech = currentTech();
            const svgColor = currentSvgColor();
            const notes = ($('#spw_notes').value || '').trim();

            if (!variantId) { alert('No se ha podido identificar la variante.'); return; }

            const png_b64 = await makeCanvasPngBase64();

            const payload = {
                variant_id: variantId,
                qty: qty,
                tech: tech,
                svg_color: svgColor,
                notes: notes,
                png_b64: png_b64,
            };
            if (gLogoB64) {
                payload.logo_b64 = gLogoB64;
                payload.logo_name = gLogoName || 'logo_original';
                payload.logo_mime = gLogoMime || 'application/octet-stream';
            }

            const resp = await ajax.jsonRpc('/spw/add_to_cart', 'call', payload);
            if (resp && resp.ok) {
                window.location = resp.cart_url || '/shop/cart';
            } else {
                alert((resp && resp.message) || 'Error añadiendo al carrito.');
            }
        } catch (err) {
            console.error('spw add_to_cart error', err);
            alert('Error añadiendo al carrito.');
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        const f = $('#spw_logo_input'); if (f) f.addEventListener('change', handleFileInput);
        ['#spw_size','#spw_pos_x','#spw_pos_y','#spw_rotation'].forEach(sel=>{
            const el = $(sel); if (el) el.addEventListener('input', applyTransforms);
        });
        document.querySelectorAll('input[name="spw_svg_color"]').forEach(el=>{
            el.addEventListener('change', recolorSvgAndShow);
        });

        const btnReset = $('#spw_reset_btn'); if (btnReset) btnReset.addEventListener('click', resetAll);
        const btnDl = $('#spw_download_btn'); if (btnDl) btnDl.addEventListener('click', downloadPNG);
        const btnCart = $('#spw_add_to_cart_btn'); if (btnCart) btnCart.addEventListener('click', addToCart);

        applyTransforms();
    });
});