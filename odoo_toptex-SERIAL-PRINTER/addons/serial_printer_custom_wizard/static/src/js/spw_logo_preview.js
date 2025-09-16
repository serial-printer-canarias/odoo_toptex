odoo.define('serial_printer_custom_wizard.spw_logo_preview', function (require) {
    'use strict';
    window.SPW = window.SPW || {};

    function getCanvas() { return document.getElementById('personalization-canvas'); }

    function drawBaseImage() {
        const imgEl = document.getElementById('spw-base-img');
        const canvas = getCanvas();
        if (!imgEl || !canvas) return;

        const paint = () => {
            const w = imgEl.naturalWidth || 900;
            const h = imgEl.naturalHeight || 900;
            const ctx = canvas.getContext('2d');
            canvas.width = w; canvas.height = h;
            ctx.clearRect(0, 0, w, h);
            ctx.drawImage(imgEl, 0, 0, w, h);
            // Si tus overlays/LOGO se pintan en customizer.js, no tocamos eso.
            if (window.SPW && typeof SPW.afterBaseDraw === 'function') SPW.afterBaseDraw(ctx, w, h);
        };
        imgEl.complete ? paint() : imgEl.addEventListener('load', paint, { once: true });
    }

    function exportPNGDataURL() {
        const canvas = getCanvas();
        if (!canvas) return null;
        try { return canvas.toDataURL('image/png'); } catch (e) { return null; }
    }

    function downloadPNG() {
        const dataUrl = exportPNGDataURL();
        if (!dataUrl) return;
        const a = document.createElement('a');
        a.href = dataUrl; a.download = 'personalizacion.png';
        if (typeof a.download === 'undefined' || /iPad|iPhone|iPod/i.test(navigator.userAgent)) {
            // iOS: abrir en nueva pestaña/visor (desde ahí “Guardar en Fotos/Archivos”)
            window.open(dataUrl, '_blank');
            return;
        }
        document.body.appendChild(a); a.click(); a.remove();
    }

    window.SPW.drawBaseImage = drawBaseImage;
    window.SPW.exportPNGDataURL = exportPNGDataURL;
    window.SPW.downloadPNG = downloadPNG;

    document.addEventListener('DOMContentLoaded', function () {
        drawBaseImage();
        const dl = document.getElementById('btn-download-png');
        if (dl) dl.addEventListener('click', function (ev) { ev.preventDefault(); downloadPNG(); });
    });
});