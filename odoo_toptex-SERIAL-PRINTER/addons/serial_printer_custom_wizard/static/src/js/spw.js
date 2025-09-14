// addons/serial_printer_custom_wizard/static/src/js/spw.js
odoo.define('serial_printer_custom_wizard.spw', function (require) {
    'use strict';

    const publicRoot = require('web.core'); // asegura carga de assets
    // No usamos ajax.jsonRpc para simplificar; enviamos fetch() a /spw/add_to_cart

    function byId(id){ return document.getElementById(id); }

    function ready(fn){ 
        if (document.readyState !== 'loading') { fn(); }
        else { document.addEventListener('DOMContentLoaded', fn); }
    }

    ready(function () {
        const elBase     = byId('spw_product_img');     // imagen producto
        const elLogo     = byId('spw_logo_preview');    // overlay
        const inputLogo  = byId('spw_logo_input');
        const rSize      = byId('spw_size');
        const rPosX      = byId('spw_pos_x');
        const rPosY      = byId('spw_pos_y');
        const rRot       = byId('spw_rotation');
        const btnReset   = document.querySelector('[onclick*="spwReset"]');
        const notesEl    = byId('spw_notes') || document.querySelector('textarea#spw_notes');
        const techEls    = document.querySelectorAll('input[name="spw_tech"]');
        const colorEls   = document.querySelectorAll('.spw-color-swatch input[type="radio"]');
        const btnAdd     = byId('spw_add_to_cart');
        const btnDownload= byId('spw_download_png');

        const templateId = (byId('spw_template_id') && byId('spw_template_id').value) || '';
        const variantId  = (byId('spw_variant_id')  && byId('spw_variant_id').value)  || '';

        let logoIsSVG = false;
        let svgOriginalText = '';   // para recolorear
        let svgCurrentColor = '';   // hex del botón seleccionado
        let logoNatural = { w: 0, h: 0 }; // tamaño natural del raster/preview

        // --- Utilidades de preview
        function applyTransform(){
            const scale = (parseInt(rSize.value || 100, 10) / 100);
            const tx = parseInt(rPosX.value || 0, 10);
            const ty = parseInt(rPosY.value || 0, 10);
            const rot = parseInt(rRot.value || 0, 10);

            elLogo.style.transform =
                `translate(-50%, -50%) translate(${tx}%, ${ty}%) rotate(${rot}deg) scale(${scale})`;
        }

        function setLogoSrcFromBlobURL(url){
            elLogo.src = url;
            elLogo.classList.remove('d-none');
            elLogo.style.opacity = '1';
            // obtener w/h naturales cuando cargue
            elLogo.onload = () => {
                logoNatural.w = elLogo.naturalWidth;
                logoNatural.h = elLogo.naturalHeight;
            };
        }

        // Recolorear SVG inline (sustituyendo fills/strokes a un color)
        function recolorSVGText(svgText, hex){
            // reemplaza fill/stroke actuales por el color elegido
            const clean = svgText
                .replace(/fill="[^"]*"/gi, '')     // limpia fills
                .replace(/stroke="[^"]*"/gi, '');  // limpia strokes
            // Envolvemos con un <g> que aplica fill/stroke por CSS interno
            return clean.replace(
                /<svg([^>]*)>/i,
                `<svg$1><style> * { fill: ${hex} !important; stroke: ${hex} !important; } </style>`
            );
        }

        function updateSVGColor(hex){
            if (!logoIsSVG || !svgOriginalText) return;
            svgCurrentColor = hex;
            const colored = recolorSVGText(svgOriginalText, hex);
            const blob = new Blob([colored], {type: 'image/svg+xml'});
            const url = URL.createObjectURL(blob);
            setLogoSrcFromBlobURL(url);
        }

        // --- Carga del logo
        if (inputLogo) {
            inputLogo.addEventListener('change', function () {
                const f = this.files && this.files[0];
                if (!f) return;

                logoIsSVG = f.type === 'image/svg+xml';

                if (logoIsSVG) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        svgOriginalText = String(e.target.result || '');
                        // si hay un color seleccionado, lo aplicamos; si no, tal cual
                        if (svgCurrentColor) {
                            updateSVGColor(svgCurrentColor);
                        } else {
                            const blob = new Blob([svgOriginalText], {type: 'image/svg+xml'});
                            const url = URL.createObjectURL(blob);
                            setLogoSrcFromBlobURL(url);
                        }
                    };
                    reader.readAsText(f);
                } else {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const url = e.target.result;
                        setLogoSrcFromBlobURL(url);
                    };
                    reader.readAsDataURL(f);
                }
            });
        }

        // --- Sliders
        [rSize, rPosX, rPosY, rRot].forEach(el => {
            if (el) el.addEventListener('input', applyTransform);
        });

        // --- Colores (solo afectan a SVG)
        colorEls.forEach(radio => {
            radio.addEventListener('change', function(){
                if (!this.checked) return;
                const hex = this.value;
                updateSVGColor(hex);
            });
        });

        // --- Reset
        window.spwReset = function(){
            if (rSize) rSize.value = 100;
            if (rPosX) rPosX.value = 0;
            if (rPosY) rPosY.value = 10;
            if (rRot)  rRot.value  = 0;
            applyTransform();
        };
        if (btnReset) btnReset.addEventListener('click', window.spwReset);
        applyTransform();

        // --- Composición a PNG para descargar / enviar al carrito
        async function composeToPNGDataURL(){
            // asegurarnos de que la imagen base está cargada
            if (!elBase || !elBase.complete) {
                await new Promise((res)=> elBase.onload = res);
            }
            const baseW = elBase.naturalWidth || elBase.width;
            const baseH = elBase.naturalHeight || elBase.height;

            const canvas = document.createElement('canvas');
            canvas.width = baseW;
            canvas.height = baseH;
            const ctx = canvas.getContext('2d');

            // dibuja base
            ctx.drawImage(elBase, 0, 0, baseW, baseH);

            if (elLogo && elLogo.src) {
                // valores desde la UI
                const scale = (parseInt(rSize.value || 100, 10) / 100);
                const txPct = parseInt(rPosX.value || 0, 10);
                const tyPct = parseInt(rPosY.value || 0, 10);
                const rotDeg= parseInt(rRot.value || 0, 10);

                // centro del overlay en px (la preview usa 50% 60% + slider)
                const cx = baseW * (0.5 + txPct / 100);
                const cy = baseH * (0.6 + tyPct / 100);

                // tamaño destino (escala sobre tamaño natural del recurso)
                const w = (logoNatural.w || elLogo.naturalWidth || 200) * scale;
                const h = (logoNatural.h || elLogo.naturalHeight || 200) * scale;

                ctx.save();
                ctx.translate(cx, cy);
                ctx.rotate(rotDeg * Math.PI / 180);
                ctx.drawImage(elLogo, -w/2, -h/2, w, h);
                ctx.restore();
            }

            return canvas.toDataURL('image/png');
        }

        // Descargar PNG (ya lo tenías; lo mantenemos)
        if (btnDownload) {
            btnDownload.addEventListener('click', async function(){
                const dataURL = await composeToPNGDataURL();
                const a = document.createElement('a');
                a.href = dataURL;
                a.download = 'personalizacion.png';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
            });
        }

        // Añadir al carrito con esta personalización
        if (btnAdd) {
            btnAdd.addEventListener('click', async function(){
                try {
                    const pngData = await composeToPNGDataURL();

                    let technique = '';
                    techEls.forEach(r => { if (r.checked) technique = r.value; });

                    let svgColor = '';
                    const selectedColor = document.querySelector('.spw-color-swatch input[type="radio"]:checked');
                    if (selectedColor) svgColor = selectedColor.value;

                    const payload = {
                        template_id: templateId || '',
                        variant_id:  variantId  || '',
                        quantity: 1,
                        technique: technique,
                        svg_color: svgColor,
                        notes: (notesEl && notesEl.value) || '',
                        png_data: pngData,
                    };

                    const resp = await fetch('/spw/add_to_cart', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(payload),
                        credentials: 'same-origin'
                    });
                    const json = await resp.json();
                    if (json && json.ok) {
                        window.location = json.cart_url || '/shop/cart';
                    } else {
                        alert('No se pudo añadir al carrito.\n' + (json && json.error ? json.error : ''));
                    }
                } catch (e) {
                    console.error(e);
                    alert('Error al preparar la personalización.');
                }
            });
        }
    });
});