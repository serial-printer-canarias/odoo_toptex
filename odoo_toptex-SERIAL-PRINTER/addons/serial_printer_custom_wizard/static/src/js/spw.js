/** addons/serial_printer_custom_wizard/static/src/js/spw.js **/
odoo.define('serial_printer_custom_wizard.spw', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    let gLogoB64 = '';     // DataURL del archivo original subido (con prefijo)
    let gLogoName = '';
    let gLogoMime = '';

    function $(sel) { return document.querySelector(sel); }

    function currentTech() {
        const el = document.querySelector('input[name="spw_tech"]:checked');
        return el ? el.value : '';
    }
    function currentSvgColor() {
        const el = document.querySelector('input[name="spw_svg_color"]:checked');
        return el ? el.value : '';
    }

    // Aplica transformaciones al logo
    function applyTransforms() {
        const size = parseInt($('#spw_size').value, 10);
        const posX = parseInt($('#spw_pos_x').value, 10);
        const posY = parseInt($('#spw_pos_y').value, 10);
        const rot  = parseInt($('#spw_rotation').value, 10);

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

    // Cargar archivo y previsualizar (guarda DataURL para adjuntarlo)
    function handleFileInput(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;
        gLogoName = file.name || 'logo_original';
        gLogoMime = file.type || 'application/octet-stream';

        const reader = new FileReader();
        reader.onload = function (e) {
            const dataUrl = e.target.result; // con prefijo data:
            gLogoB64 = dataUrl;
            const img = $('#spw_logo_preview');
            img.src = dataUrl;
            img.onload = applyTransforms;
            img.classList.remove('d-none');
            img.style.opacity = '1';
        };
        reader.readAsDataURL(file);
    }

    // Screenshot del canvas -> base64 (sólo datos, sin prefijo)
    function makeCanvasPngBase64() {
        const node = $('#spw_canvas');
        return html2canvas(node, {
            useCORS: true,
            allowTaint: false,
            backgroundColor: null,
            scale: window.devicePixelRatio > 1 ? 2 : 1,
            imageTimeout: 0,
        }).then(canvas => {
            const dataUrl = canvas.toDataURL('image/png');
            return dataUrl.replace(/^data:image\/png;base64,/, '');
        });
    }

    // Descargar PNG robusto (iOS incluido)
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
                canvas.toBlob(function (blob) {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'personalizacion.png';
                    document.body.appendChild(a);
                    a.click();
                    setTimeout(function () {
                        URL.revokeObjectURL(url);
                        a.remove();
                    }, 1000);
                }, 'image/png');
            } else {
                // fallback
                const a = document.createElement('a');
                a.href = canvas.toDataURL('image/png');
                a.download = 'personalizacion.png';
                document.body.appendChild(a);
                a.click();
                a.remove();
            }
        });
    }

    // Enviar al carrito
    async function addToCart() {
        try {
            const variantId = parseInt($('#spw_variant_id').value || '0', 10);
            const qty = Math.max(1, parseInt($('#spw_qty').value || '1', 10));
            const tech = currentTech();
            const svgColor = currentSvgColor();
            const notes = ($('#spw_notes').value || '').trim();

            if (!variantId) {
                alert('No se ha podido identificar la variante.');
                return;
            }

            const png_b64 = await makeCanvasPngBase64();

            const payload = {
                variant_id: variantId,
                qty: qty,
                tech: tech,
                svg_color: svgColor,
                notes: notes,
                png_b64: png_b64,               // sólo datos base64
            };

            // Adjuntar archivo original si hay
            if (gLogoB64) {
                payload.logo_b64 = gLogoB64;   // puede ir con prefijo; el servidor lo admite
                payload.logo_name = gLogoName || 'logo_original';
                payload.logo_mime = gLogoMime || 'application/octet-stream';
            }

            const resp = await ajax.jsonRpc('/spw/add_to_cart', 'call', payload);
            if (resp && resp.ok) {
                window.location = resp.cart_url || '/shop/cart';
            } else {
                alert(resp && resp.message ? resp.message : 'Error añadiendo al carrito.');
            }
        } catch (err) {
            console.error('spw add_to_cart error', err);
            alert('Error añadiendo al carrito.');
        }
    }

    // Bindings al cargar
    document.addEventListener('DOMContentLoaded', function () {
        const f = $('#spw_logo_input');
        if (f) f.addEventListener('change', handleFileInput);

        ['#spw_size', '#spw_pos_x', '#spw_pos_y', '#spw_rotation'].forEach(sel => {
            const el = $(sel);
            if (el) el.addEventListener('input', applyTransforms);
        });

        const btnReset = $('#spw_reset_btn');
        if (btnReset) btnReset.addEventListener('click', resetAll);

        const btnDl = $('#spw_download_btn');
        if (btnDl) btnDl.addEventListener('click', downloadPNG);

        const btnCart = $('#spw_add_to_cart_btn');
        if (btnCart) btnCart.addEventListener('click', addToCart);

        // primera aplicación de transformaciones
        applyTransforms();
    });
});