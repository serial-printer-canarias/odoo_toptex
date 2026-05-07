odoo.define('serial_printer_custom_wizard.personalization', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    function canvasToBase64(canvas) {
        try {
            // Safari iOS: toDataURL es lo más fiable si no hay CORS
            return canvas.toDataURL('image/png'); // incluye header data:
        } catch (e) {
            return null;
        }
    }

    function b64ToBlob(b64Data, contentType) {
        contentType = contentType || 'image/png';
        const sliceSize = 512;
        const byteCharacters = atob(b64Data);
        const byteArrays = [];
        for (let offset = 0; offset < byteCharacters.length; offset += sliceSize) {
            const slice = byteCharacters.slice(offset, offset + sliceSize);
            const byteNumbers = new Array(slice.length);
            for (let i = 0; i < slice.length; i++) {
                byteNumbers[i] = slice.charCodeAt(i);
            }
            byteArrays.push(new Uint8Array(byteNumbers));
        }
        return new Blob(byteArrays, { type: contentType });
    }

    async function addToCart() {
        const productId = parseInt(document.querySelector('[name="product_id"]').value);
        const qty = parseFloat(document.querySelector('[name="quantity"]').value || '1');

        const payload = {
            product_id: productId,
            qty: qty,
            tecnica: (document.querySelector('[name="tecnica"]')?.value || '').trim(),
            tamano: (document.querySelector('[name="tamano"]')?.value || '').trim(),
            posicion: document.querySelector('[name="posicion"]')?.value || null,
            color_hex: document.querySelector('[name="color_hex"]')?.value || null,
            svg_color: document.querySelector('[name="svg_color"]')?.value || null,
            notas: document.querySelector('[name="notas"]')?.value || null,
        };

        const canvas = document.getElementById('personalization-canvas');
        if (canvas) {
            const dataUrl = canvasToBase64(canvas); // "data:image/png;base64,....."
            if (dataUrl) {
                payload.png_b64 = dataUrl; // el backend lo sanea
                payload.png_name = 'personalizacion.png';
            }
        }

        try {
            await ajax.jsonRpc('/personalizacion/add_to_cart', 'call', payload);
            window.location = '/shop/cart';
        } catch (e) {
            window.location = '/shop/cart';
        }
    }

    async function downloadPNG() {
        const canvas = document.getElementById('personalization-canvas');
        if (!canvas) return;

        const dataUrl = canvasToBase64(canvas);
        if (!dataUrl) return;

        // dataUrl -> Blob -> descarga (mejor compatibilidad iOS)
        const b64 = dataUrl.split('base64,')[1];
        const blob = b64ToBlob(b64, 'image/png');
        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');
        a.href = url;
        a.download = 'personalizacion.png';
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1500);
    }

    function bind() {
        const addBtn = document.getElementById('btn-add-to-cart-personalization');
        if (addBtn) addBtn.addEventListener('click', function (ev) {
            ev.preventDefault();
            addToCart();
        });
        const dlBtn = document.getElementById('btn-download-png');
        if (dlBtn) {
            dlBtn.removeAttribute('disabled'); // por si el template lo dejó desactivado
            dlBtn.addEventListener('click', function (ev) {
                ev.preventDefault();
                downloadPNG();
            });
        }
    }

    document.addEventListener('DOMContentLoaded', bind);
});