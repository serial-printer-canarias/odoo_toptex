/** serial_printer_custom_wizard/static/src/js/customizer_preview.js **/
odoo.define('serial_printer_custom_wizard.customizer_preview', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    function clamp(v, min, max) { return Math.min(max, Math.max(min, v)); }

    publicWidget.registry.SPWCustomizer = publicWidget.Widget.extend({
        selector: '.spw-container',
        start() {
            this.base = this.el.querySelector('#spw_base_img');
            this.logo = this.el.querySelector('#spw_logo');

            // Controles
            this.scale = this.el.querySelector('#spw_scale');
            this.rotate = this.el.querySelector('#spw_rotate');
            this.posX = this.el.querySelector('#spw_pos_x');
            this.posY = this.el.querySelector('#spw_pos_y');
            this.file = this.el.querySelector('#spw_file');
            this.colors = this.el.querySelector('#spw_colors');

            this._buildColors();
            this._bind();

            // Estado inicial
            this._updateTransform();

            return this._super(...arguments);
        },

        _bind() {
            this.scale.addEventListener('input', () => this._updateTransform());
            this.rotate.addEventListener('input', () => this._updateTransform());
            this.posX.addEventListener('input', () => this._updateTransform());
            this.posY.addEventListener('input', () => this._updateTransform());

            // Drag del logo
            const wrapper = this.el.querySelector('.spw-canvas-wrapper');
            let dragging = false;
            const onMove = (e) => {
                if (!dragging) return;
                const rect = wrapper.getBoundingClientRect();
                const x = clamp(((e.clientX - rect.left) / rect.width) * 100, 0, 100);
                const y = clamp(((e.clientY - rect.top) / rect.height) * 100, 0, 100);
                this.posX.value = Math.round(x);
                this.posY.value = Math.round(y);
                this._updateTransform();
            };
            this.logo.addEventListener('pointerdown', (e) => { dragging = true; this.logo.setPointerCapture(e.pointerId); });
            window.addEventListener('pointermove', onMove);
            window.addEventListener('pointerup', () => dragging = false);

            // Quick positions
            this.el.querySelectorAll('.spw-quick').forEach(btn => {
                btn.addEventListener('click', () => {
                    const pos = btn.dataset.pos;
                    if (pos === 'left_chest') { this.posX.value = 30; this.posY.value = 35; }
                    else if (pos === 'right_chest') { this.posX.value = 70; this.posY.value = 35; }
                    else if (pos === 'back') { this.posX.value = 50; this.posY.value = 60; }
                    else { this.posX.value = 50; this.posY.value = 50; }
                    this._updateTransform();
                });
            });

            // Subir logo
            this.file.addEventListener('change', (ev) => {
                const f = ev.target.files && ev.target.files[0];
                if (!f) return;
                const reader = new FileReader();
                reader.onload = () => {
                    this.logo.src = reader.result;
                    this.logo.classList.remove('d-none');
                    // tamaño por defecto 25% para empezar
                    this.scale.value = 25; 
                    this._updateTransform();
                };
                reader.readAsDataURL(f);
            });
        },

        _updateTransform() {
            const s = parseInt(this.scale.value || 100, 10);
            const r = parseInt(this.rotate.value || 0, 10);
            const x = parseInt(this.posX.value || 50, 10);
            const y = parseInt(this.posY.value || 50, 10);
            this.logo.style.width = s + '%';
            this.logo.style.left = x + '%';
            this.logo.style.top = y + '%';
            this.logo.style.transform = `translate(-50%, -50%) rotate(${r}deg)`;
        },

        _buildColors() {
            // Paleta compacta estilo NS300 (sin mencionarlo)
            const HEX = [
                '#000000','#2F2F2F','#595959','#808080','#B3B3B3','#FFFFFF',
                '#7F0000','#C00000','#FF5A5A','#FF7F00','#FFC000',
                '#006837','#009E49','#00B050','#2E74B5','#0070C0','#00B0F0',
                '#7030A0','#A35BD1','#8B572A','#C69C6D','#3F3F0F'
            ];
            this.colors.innerHTML = '';
            HEX.forEach(h => {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'spw-color';
                b.style.background = h;
                b.setAttribute('data-hex', h);
                b.addEventListener('click', () => {
                    this.colors.querySelectorAll('.spw-color.active').forEach(x => x.classList.remove('active'));
                    b.classList.add('active');
                    // guardamos el color elegido (puedes enviarlo al carrito después)
                    this.el.dataset.spwColor = h;
                });
                this.colors.appendChild(b);
            });
        },
    });

    return publicWidget.registry.SPWCustomizer;
});