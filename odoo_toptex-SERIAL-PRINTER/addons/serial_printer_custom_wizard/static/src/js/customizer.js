/** serial_printer_custom_wizard/static/src/js/customizer.js **/
odoo.define('serial_printer_custom_wizard.customizer', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const domReady = require('web.dom_ready');

    function clamp(n, min, max) { return Math.min(Math.max(n, min), max); }

    // Widget del personalizador (solo se activa si existe el contenedor)
    publicWidget.registry.SPWCustomizer = publicWidget.Widget.extend({
        selector: '.spw-customizer',
        start() {
            // Elementos del DOM (si alguno no existe, no hacemos nada y no rompemos nada)
            this.stage = this.el.querySelector('.spw-stage');
            this.baseImg = this.el.querySelector('#spw_product_img');
            this.logoImg = this.el.querySelector('#spw_logo_preview');
            this.fileInput = this.el.querySelector('#spw_logo_input');

            this.rangeSize  = this.el.querySelector('#spw_size');
            this.rangeRot   = this.el.querySelector('#spw_rotate');
            this.rangePosX  = this.el.querySelector('#spw_pos_x');
            this.rangePosY  = this.el.querySelector('#spw_pos_y');

            if (!this.stage || !this.baseImg || !this.logoImg || !this.fileInput) {
                return this._super.apply(this, arguments);
            }

            // Estado
            this.state = {
                scale: parseFloat(this.rangeSize?.value || '1'),
                rot:   parseFloat(this.rangeRot?.value  || '0'),
                x:     parseFloat(this.rangePosX?.value || '0'),
                y:     parseFloat(this.rangePosY?.value || '0'),
            };

            // Listeners
            this.fileInput.addEventListener('change', (e) => this._onSelectFile(e));
            this.rangeSize && this.rangeSize.addEventListener('input', () => this._updateTransform());
            this.rangeRot  && this.rangeRot.addEventListener('input', () => this._updateTransform());
            this.rangePosX && this.rangePosX.addEventListener('input', () => this._updateTransform());
            this.rangePosY && this.rangePosY.addEventListener('input', () => this._updateTransform());

            // Drag para mover el logo
            this._enableDrag();

            // Asegura que el logo esté oculto hasta que haya imagen
            this.logoImg.style.display = 'none';

            return this._super.apply(this, arguments);
        },

        _onSelectFile(ev) {
            const file = ev.target.files && ev.target.files[0];
            if (!file) return;

            try {
                const objectUrl = URL.createObjectURL(file);
                this.logoImg.onload = () => {
                    // Tamaño base: 30% del ancho del stage
                    this.logoImg.style.width = '30%';
                    this.logoImg.style.display = 'block';
                    URL.revokeObjectURL(objectUrl);
                    // Recentramos un poco
                    if (this.rangeSize)  this.rangeSize.value = '1';
                    if (this.rangeRot)   this.rangeRot.value = '0';
                    if (this.rangePosX)  this.rangePosX.value = '0';
                    if (this.rangePosY)  this.rangePosY.value = '0';
                    this.state = { scale:1, rot:0, x:0, y:0 };
                    this._updateTransform();
                };
                this.logoImg.src = objectUrl;
            } catch (e) {
                // Nunca romper la web
                console.error('SPW preview error:', e);
            }
        },

        _updateTransform() {
            // Leemos sliders (con fallback)
            const s = parseFloat(this.rangeSize?.value || this.state.scale);
            const r = parseFloat(this.rangeRot?.value  || this.state.rot);
            const x = parseFloat(this.rangePosX?.value || this.state.x);
            const y = parseFloat(this.rangePosY?.value || this.state.y);

            // Guards
            this.state.scale = clamp(s, 0.1, 3);
            this.state.rot   = clamp(r, -180, 180);
            this.state.x     = clamp(x, -100, 100);
            this.state.y     = clamp(y, -100, 100);

            // Aplicamos transform: translate en % relativo al contenedor
            this.logoImg.style.transform =
                `translate(${this.state.x}%, ${this.state.y}%) rotate(${this.state.rot}deg) scale(${this.state.scale})`;
            this.logoImg.style.transformOrigin = 'center center';
        },

        _enableDrag() {
            let dragging = false, startX = 0, startY = 0;

            const onDown = (e) => {
                if (this.logoImg.style.display === 'none') return;
                dragging = true;
                const p = this._pointer(e);
                startX = p.x; startY = p.y;
                e.preventDefault();
            };
            const onMove = (e) => {
                if (!dragging) return;
                const p = this._pointer(e);
                const rect = this.stage.getBoundingClientRect();
                const dx = ((p.x - startX) / rect.width) * 100;
                const dy = ((p.y - startY) / rect.height) * 100;
                startX = p.x; startY = p.y;
                if (this.rangePosX) this.rangePosX.value = (parseFloat(this.rangePosX.value || '0') + dx).toString();
                if (this.rangePosY) this.rangePosY.value = (parseFloat(this.rangePosY.value || '0') + dy).toString();
                this._updateTransform();
            };
            const onUp = () => { dragging = false; };

            this.logoImg.addEventListener('mousedown', onDown);
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);

            this.logoImg.addEventListener('touchstart', onDown, {passive:false});
            document.addEventListener('touchmove', onMove, {passive:false});
            document.addEventListener('touchend', onUp);
        },

        _pointer(e) {
            if (e.touches && e.touches[0]) return { x: e.touches[0].clientX, y: e.touches[0].clientY };
            return { x: e.clientX, y: e.clientY };
        },
    });

    domReady(() => {/* vacío: el widget se auto-registra */});
});