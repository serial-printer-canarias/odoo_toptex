/** Simple preview: posiciona/rota/escala el logo sobre la foto */
odoo.define('serial_printer_custom_wizard.customizer_preview', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    const Preview = publicWidget.Widget.extend({
        selector: '.spw-wrap',

        start() {
            this.base = this.el.querySelector('#spw_base_img');
            this.logo = this.el.querySelector('#spw_logo_img');
            this.file = this.el.querySelector('#spw_file');
            this.size = this.el.querySelector('#spw_size');
            this.rot  = this.el.querySelector('#spw_rot');
            this.x    = this.el.querySelector('#spw_x');
            this.y    = this.el.querySelector('#spw_y');

            // Colores
            this.palette = this.el.querySelector('#spw_palette');
            this.colorName = this.el.querySelector('#spw_color_name');
            this.colorHex  = this.el.querySelector('#spw_color_hex');

            // Posición rápida
            this.el.addEventListener('change', (ev) => {
                if (ev.target.name === 'spw_posq') this._applyQuick(ev.target.value);
            });

            // Eventos
            this.file.addEventListener('change', () => this._loadFile());
            [this.size,this.rot,this.x,this.y].forEach(i => i.addEventListener('input', () => this._updateLogo()));

            this.palette.addEventListener('click', (ev) => {
                const chip = ev.target.closest('.spw-chip'); if (!chip) return;
                this.palette.querySelectorAll('.spw-chip').forEach(c => c.classList.remove('is-active'));
                chip.classList.add('is-active');
                this.colorName.value = chip.dataset.name || '';
                this.colorHex.value = getComputedStyle(chip).getPropertyValue('--c').trim();
            });

            // Estado inicial
            const firstChip = this.palette.querySelector('.spw-chip'); if (firstChip) firstChip.classList.add('is-active');
            this._applyQuick('pecho_izq');
            return this._super(...arguments);
        },

        _loadFile() {
            const f = this.file.files && this.file.files[0];
            if (!f) return;
            const reader = new FileReader();
            reader.onload = () => {
                this.logo.src = reader.result;
                this.logo.classList.remove('d-none');
                this._updateLogo();
            };
            reader.readAsDataURL(f);
        },

        _applyQuick(where) {
            // Valores base
            let pos = {x: 35, y: 58}; // pecho izq
            if (where === 'pecho_dcha') pos = {x: 65, y: 58};
            if (where === 'espalda')    pos = {x: 50, y: 40};
            if (where === 'libre')      pos = {x: 50, y: 50};
            this.x.value = pos.x; this.y.value = pos.y;
            this._updateLogo();
        },

        _updateLogo() {
            const s = parseFloat(this.size.value || '0.6');
            const r = parseFloat(this.rot.value || '0');
            const x = parseFloat(this.x.value || '50');
            const y = parseFloat(this.y.value || '50');
            this.logo.style.transform = `translate(-50%,-50%) translate(${x}%, ${y}%) scale(${s}) rotate(${r}deg)`;
        },
    });

    publicWidget.registry.spwCustomizerPreview = Preview;
    return Preview;
});