odoo.define('serial_printer_custom_wizard.spw', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    // ====== Estado global mínimo ======
    let gLogoDataURL = '';   // DataURL del archivo original (con prefijo data:)
    let gLogoName    = '';
    let gLogoMime    = '';
    let gIsSvg       = false;
    let gSvgOriginal = '';   // texto SVG original para recolor

    // ====== Utilidades ======
    const $  = (sel) => document.querySelector(sel);

    const currentTech = () => {
        const el = document.querySelector('input[name="spw_tech"]:checked');
        return el ? el.value : '';
    };
    const currentSvgColor = () => {
        const el = document.querySelector('input[name="spw_svg_color"]:checked');
        return el ? el.value : '';
    };

    // ====== Transforms en la preview (lo que ya tienes en CSS) ======
    function applyTransforms() {
        const size = parseInt($('#spw_size').value || '100', 10);
        const posX = parseInt($('#spw_pos_x').value || '0',   10);
        const posY = parseInt($('#spw_pos_y').value || '10',  10);
        const rot  = parseInt($('#spw_rotation').value || '0',10);

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

    // ====== Carga/recolor de SVG ======
    function recolorSvgAndShow() {
        if (!gIsSvg || !gSvgOriginal) return;
        const color = currentSvgColor() || '#000000';

        // Sustituimos fill/stroke que no sean 'none'
        let svgTxt = gSvgOriginal
            .replace(/fill="(?!none)[^"]*"/gi, `fill="${color}"`)
            .replace(/stroke="(?!none)[^"]*"/gi, `stroke="${color}"`);

        const blob = new Blob([svgTxt], { type: 'image/svg+xml' });
        const url  = URL.createObjectURL(blob);

        const img = $('#spw_logo_preview');
        img.onload = () => { URL.revokeObjectURL(url); applyTransforms(); };
        img.src = url;
        img.classList.remove('d-none');
        img.style.opacity = '1';
    }

    // ====== Fichero de logo (PNG/JPG/SVG) ======
    function handleFileInput(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) return;

        gLogoName = file.name || 'logo_original';
        gLogoMime = file.type || 'application/octet-stream';
        gIsSvg    = (file.type === 'image/svg+xml');
        gSvgOriginal = '';

        if (gIsSvg) {
            // Guardamos DataURL y el texto SVG para recolorear
            const r1 = new FileReader();
            r1.onload = e => { gLogoDataURL = e.target.result; };
            r1.readAsDataURL(file);

            const r2 = new FileReader();
            r2.onload = e => { gSvgOriginal = e.target.result || ''; recolorSvgAndShow(); };
            r2.readAsText(file);
        } else {
            const reader = new FileReader();
            reader.onload = function (e) {
                gLogoDataURL = e.target.result;
                const img = $('#spw_logo_preview');
                img.src = gLogoDataURL;
                img.onload = applyTransforms;
                img.classList.remove('d-none');
                img.style.opacity = '1';
            };
            reader.readAsDataURL(file);
        }
    }

    // ====== Composición a PNG SIN librerías ======
    /**
     * Renderiza el canvas final igual que lo ves en pantalla:
     * - Toma tamaño NATURAL del producto para buena calidad
     * - Proyecta la posición/tamaño del logo a píxeles naturales
     * - Aplica rotación y escala
     * Devuelve un objeto { canvas, toDataURLBase64() }
     */
    function composeCanvasFromDOM() {
        const baseEl = $('#spw_product_img');
        const logoEl = $('#spw_logo_preview');

        // Si no hay imagen base, abortamos
        const natW = baseEl.naturalWidth  || baseEl.width  || 0;
        const natH = baseEl.naturalHeight || baseEl.height || 0;
        if (!natW || !natH) return null;

        // Dimensiones mostradas en pantalla (para mapear)
        const baseRect = baseEl.getBoundingClientRect();
        const scaleToNatural = natW / (baseRect.width || 1);

        // Creamos canvas basado en tamaño NATURAL
        const canvas = document.createElement('canvas');
        canvas.width  = natW;
        canvas.height = natH;
        const ctx = canvas.getContext('2d');

        // Fondo blanco (opcional) para evitar transparencia
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, natW, natH);

        // Dibujamos producto
        ctx.drawImage(baseEl, 0, 0, natW, natH);

        // Si hay logo visible, lo dibujamos en su posición real
        if (logoEl && logoEl.src && logoEl.style.opacity !== '0' && !logoEl.classList.contains('d-none')) {
            const r = logoEl.getBoundingClientRect();

            // Centro del logo relativo al producto (en pantalla)
            const cx_disp = (r.left + r.right)/2 - baseRect.left;
            const cy_disp = (r.top  + r.bottom)/2 - baseRect.top;

            // Ancho/alto mostrados del logo
            const w_disp = r.width;
            const h_disp = r.height;

            // Convertimos a píxeles naturales del producto
            const cx = cx_disp * scaleToNatural;
            const cy = cy_disp * scaleToNatural;
            const w  = Math.max(1, w_disp * scaleToNatural);
            const h  = Math.max(1, h_disp * scaleToNatural);

            // Ángulo actual (extraemos del slider)
            const rotDeg = parseInt($('#spw_rotation').value || '0', 10);
            const rotRad = rotDeg * Math.PI / 180;

            // Dibujamos con rotación alrededor del centro
            ctx.save();
            ctx.translate(cx, cy);
            ctx.rotate(rotRad);
            try {
                ctx.drawImage(logoEl, -w/2, -h/2, w, h);
            } catch (e) {
                console.warn('No se pudo dibujar el logo en canvas:', e);
            }
            ctx.restore();
        }

        return {
            canvas,
            toDataURLBase64: () => canvas.toDataURL('image/png').replace(/^data:image\/png;base64,/, ''),
        };
    }

    // Descarga forzada compatible iOS
    function downloadPNG() {
        const comp = composeCanvasFromDOM();
        if (!comp) { alert('No se pudo generar la previsualización.'); return; }

        const canvas = comp.canvas;

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
            // Fallback (muy raro hoy en día)
            const a = document.createElement('a');
            a.href = canvas.toDataURL('image/png');
            a.download = 'personalizacion.png';
            document.body.appendChild(a);
            a.click();
            a.remove();
        }
    }

    // ====== Envío al carrito ======
    async function addToCart() {
        try {
            const variantId = parseInt($('#spw_variant_id').value || '0', 10);
            const qty       = Math.max(1, parseInt($('#spw_qty').value || '1', 10));
            const tech      = currentTech();
            const svgColor  = currentSvgColor();
            const notes     = ($('#spw_notes').value || '').trim();

            if (!variantId) { alert('No se ha podido identificar la variante.'); return; }

            const comp = composeCanvasFromDOM();
            if (!comp) { alert('No se pudo generar la previsualización.'); return; }
            const png_b64 = comp.toDataURLBase64();

            const payload = {
                variant_id: variantId,
                qty: qty,
                tech: tech,
                svg_color: svgColor,
                notes: notes,
                png_b64: png_b64,
            };

            // Adjuntar también el archivo original subido (si lo hay)
            if (gLogoDataURL) {
                payload.logo_b64  = gLogoDataURL.indexOf(',') !== -1 ? gLogoDataURL.split(',', 1)[1] : gLogoDataURL;
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

    // ====== Listeners ======
    document.addEventListener('DOMContentLoaded', function () {
        const f = $('#spw_logo_input'); if (f) f.addEventListener('change', handleFileInput);
        ['#spw_size','#spw_pos_x','#spw_pos_y','#spw_rotation'].forEach(sel=>{
            const el = $(sel); if (el) el.addEventListener('input', applyTransforms);
        });
        document.querySelectorAll('input[name="spw_svg_color"]').forEach(el=>{
            el.addEventListener('change', recolorSvgAndShow);
        });

        const btnReset = $('#spw_reset_btn');      if (btnReset) btnReset.addEventListener('click', resetAll);
        const btnDl    = $('#spw_download_btn');   if (btnDl)    btnDl.addEventListener('click', downloadPNG);
        const btnCart  = $('#spw_add_to_cart_btn');if (btnCart)  btnCart.addEventListener('click', addToCart);

        applyTransforms();
    });
});