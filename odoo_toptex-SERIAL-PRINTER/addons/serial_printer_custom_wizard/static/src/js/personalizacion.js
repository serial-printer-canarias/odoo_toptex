odoo.define('serial_printer_custom_wizard.personalization', function (require) {
    'use strict';

    const ajax = require('web.ajax');

    async function canvasToBase64(canvas) {
        // iOS/Safari: usar toDataURL como fallback
        try {
            if (canvas.toBlob) {
                const b64 = await new Promise(resolve => {
                    canvas.toBlob(function (blob) {
                        if (!blob) return resolve(null);
                        const reader = new FileReader();
                        reader.onloadend = () => resolve(reader.result.split(',')[1]);
                        reader.readAsDataURL(blob);
                    });
                });
                if (b64) return b64;
            }
            // Fallback
            return canvas.toDataURL('image/png').split(',')[1];
        } catch (e) {
            return null;
        }
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
            const b64 = await canvasToBase64(canvas); // puede ser null y es OK
            if (b64) {
                payload.png_b64 = b64;
                payload.png_name = 'personalizacion.png';
            }
        }

        try {
            const res = await ajax.jsonRpc('/personalizacion/add_to_cart', 'call', payload);
            // Aunque res.ok sea false, a veces la línea está creada; llevamos al carrito igualmente
            window.location = '/shop/cart';
        } catch (e) {
            // Si el JSON falla por cualquier motivo, redirigimos igual (la línea suele estar creada)
            window.location = '/shop/cart';
        }
    }

    async function downloadPNG() {
        const canvas = document.getElementById('personalization-canvas');
        if (!canvas) return;
        const b64 = await canvasToBase64(canvas);
        if (!b64) return; // si no hay canvas exportable, no hacemos nada
        const a = document.createElement('a');
        a.href = 'data:image/png;base64,' + b64;
        a.download = 'personalizacion.png';
        document.body.appendChild(a);
        a.click();
        a.remove();
    }

    function bind() {
        const addBtn = document.getElementById('btn-add-to-cart-personalization');
        if (addBtn) addBtn.addEventListener('click', function (ev) {
            ev.preventDefault();
            addToCart();
        });
        const dlBtn = document.getElementById('btn-download-png');
        if (dlBtn) dlBtn.addEventListener('click', function (ev) {
            ev.preventDefault();
            downloadPNG();
        });
    }

    document.addEventListener('DOMContentLoaded', bind);
});