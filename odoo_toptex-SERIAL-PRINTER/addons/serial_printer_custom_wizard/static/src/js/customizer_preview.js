odoo.define('serial_printer_custom_wizard.customizer_preview', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    /**
     * Vista previa del logo encima de la imagen del producto.
     * - Soporta PNG/JPG/SVG
     * - No depende de jQuery
     * - No rompe otras páginas (se auto-activa solo en .spw-customizer)
     */
    publicWidget.registry.SpwLogoPreview = publicWidget.Widget.extend({
        selector: '.spw-customizer',

        start() {
            // Canvas (contenedor de la imagen del producto)
            this.canvas = this.el.querySelector('#spw_canvas');

            // Crea el <img> de preview si no existe
            this.logoImg = this.el.querySelector('#spw_logo_preview');
            if (!this.logoImg) {
                this.logoImg = document.createElement('img');
                this.logoImg.id = 'spw_logo_preview';
                this.logoImg.alt = 'Logo preview';
                this.logoImg.className = 'spw-logo-preview d-none';
                this.canvas && this.canvas.appendChild(this.logoImg);
            }

            // Localiza los controles (ids alternativos por si varían)
            const q = s => this.el.querySelector(s);
            this.fileInput = this.el.querySelector(
                '#spw_logo_file, #spw_logo_input, input[type="file"][name="spw_logo"], input[type="file"][name="logo"]'
            );
            this.size   = q('#spw_size, #spw_logo_size');
            this.rotate = q('#spw_rotate, #spw_logo_rotate');
            this.posX   = q('#spw_pos_x, #spw_logo_pos_x');
            this.posY   = q('#spw_pos_y, #spw_logo_pos_y');

            this._bind();
            return this._super(...arguments);
        },

        _bind() {
            // Subida de archivo
            if (this.fileInput) {
                this.fileInput.addEventListener('change', ev => this._onFileChange(ev));
            }
            // Sliders
            ['input', 'change'].forEach(evt => {
                if (this.size)   this.size.addEventListener(evt, () => this._applyTransform());
                if (this.rotate) this.rotate.addEventListener(evt, () => this._applyTransform());
                if (this.posX)   this.posX.addEventListener(evt, () => this._applyTransform());
                if (this.posY)   this.posY.addEventListener(evt, () => this._applyTransform());
            });
        },

        _onFileChange(ev) {
            const file = ev.target.files && ev.target.files[0];
            if (!file) return;

            // Valida tipo rápidamente
            const ok = /image\/(png|jpe?g|svg\+xml)/i.test(file.type) || /\.(png|jpe?g|svg)$/i.test(file.name);
            if (!ok) {
                console.warn('[SPW] Formato no soportado:', file.type || file.name);
                return;
            }

            // Carga con ObjectURL (rápido y compatible)
            const url = URL.createObjectURL(file);
            this.logoImg.onload = () => {
                URL.revokeObjectURL(url);
                this.logoImg.classList.remove('d-none');
                this._applyTransform();
            };
            this.logoImg.onerror = () => {
                console.warn('[SPW] No se pudo previsualizar el archivo.');
            };
            this.logoImg.src = url;
        },

        _applyTransform() {
            // Valores por defecto seguros
            const v = (el, def) => (el ? Number(el.value) : def);
            const scale = Math.max(0.05, v(this.size, 100) / 100); // 5% – 100%
            const rot   = v(this.rotate, 0);
            const x     = v(this.posX, 50);  // en %
            const y     = v(this.posY, 60);  // en %

            Object.assign(this.logoImg.style, {
                left: x + '%',
                top:  y + '%',
                transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${scale})`,
            });
        },
    });

    return publicWidget.registry.SpwLogoPreview;
});