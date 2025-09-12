/** serial_printer_custom_wizard/static/src/js/customizer.js **/
odoo.define('serial_printer_custom_wizard.customizer', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.spwCustomizer = publicWidget.Widget.extend({
        selector: '.spw-customizer',

        start() {
            this._cache();
            this._bind();
            return this._super(...arguments);
        },

        _cache() {
            this.canvas = this.el.querySelector('#spw_canvas');
            this.logo = this.el.querySelector('#spw_logo_preview');
            this.file = this.el.querySelector('#spw_logo');
            this.scale = this.el.querySelector('#spw_scale');
            this.rotate = this.el.querySelector('#spw_rotate');
            this.posX = this.el.querySelector('#spw_pos_x');
            this.posY = this.el.querySelector('#spw_pos_y');
        },

        _bind() {
            if (this.file) {
                this.file.addEventListener('change', (ev) => {
                    const f = ev.target.files && ev.target.files[0];
                    if (!f) return;
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        this.logo.src = e.target.result;
                        this.logo.classList.remove('d-none');
                        this._apply();
                    };
                    reader.readAsDataURL(f);
                });
            }
            for (const id of ['spw_scale', 'spw_rotate', 'spw_pos_x', 'spw_pos_y']) {
                const el = this.el.querySelector('#' + id);
                if (el) el.addEventListener('input', () => this._apply());
            }

            // Permitir arrastrar el logo para posicionarlo
            if (this.logo && this.canvas) {
                let dragging = false;
                this.logo.addEventListener('mousedown', () => dragging = true);
                document.addEventListener('mouseup', () => dragging = false);
                this.canvas.addEventListener('mousemove', (e) => {
                    if (!dragging) return;
                    const rect = this.canvas.getBoundingClientRect();
                    const x = ((e.clientX - rect.left) / rect.width) * 100;
                    const y = ((e.clientY - rect.top) / rect.height) * 100;
                    this.posX.value = Math.min(100, Math.max(0, x));
                    this.posY.value = Math.min(100, Math.max(0, y));
                    this._apply();
                });
                // En móviles
                this.logo.addEventListener('touchstart', () => dragging = true, {passive: true});
                document.addEventListener('touchend', () => dragging = false, {passive: true});
                this.canvas.addEventListener('touchmove', (e) => {
                    if (!dragging) return;
                    const t = e.touches[0];
                    const rect = this.canvas.getBoundingClientRect();
                    const x = ((t.clientX - rect.left) / rect.width) * 100;
                    const y = ((t.clientY - rect.top) / rect.height) * 100;
                    this.posX.value = Math.min(100, Math.max(0, x));
                    this.posY.value = Math.min(100, Math.max(0, y));
                    this._apply();
                }, {passive: true});
            }
        },

        _apply() {
            if (!this.logo) return;
            const s = (parseFloat(this.scale?.value || '100')) / 100;
            const r = parseFloat(this.rotate?.value || '0');
            const x = parseFloat(this.posX?.value || '50');
            const y = parseFloat(this.posY?.value || '50');
            this.logo.style.left = `${x}%`;
            this.logo.style.top = `${y}%`;
            this.logo.style.transform = `translate(-50%, -50%) rotate(${r}deg) scale(${s})`;
        },
    });

    return publicWidget.registry.spwCustomizer;
});