odoo.define('serial_printer_custom_wizard.spw_cart', [], function (require) {
    'use strict';
    window.SPW = window.SPW || {};

    async function addToCart() {
        const pid = parseInt(document.querySelector('[name="product_id"]')?.value || 0);
        const qty = parseFloat(document.querySelector('[name="quantity"]')?.value || '1');

        // Guardar PNG de la vista previa (si existe)
        try {
            const dataUrl = (window.SPW && SPW.exportPNGDataURL) ? SPW.exportPNGDataURL() : null;
            if (dataUrl) sessionStorage.setItem('spw_last_png', dataUrl);
        } catch (e) {}

        // Endpoint nativo (evita el error del popup)
        const fd = new FormData();
        fd.append('product_id', pid);
        fd.append('add_qty', qty);
        fd.append('express', '1');
        try { await fetch('/shop/cart/update', { method: 'POST', body: fd, credentials: 'include' }); } catch (e) {}
        window.location = '/shop/cart';
    }

    document.addEventListener('DOMContentLoaded', function () {
        const btn = document.getElementById('spw-add-to-cart') || document.getElementById('btn-add-to-cart-personalization');
        if (btn) btn.addEventListener('click', function (ev) { ev.preventDefault(); btn.disabled = true; addToCart(); });
    });
});