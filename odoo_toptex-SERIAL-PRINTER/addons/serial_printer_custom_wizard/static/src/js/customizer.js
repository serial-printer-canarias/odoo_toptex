/** Serial Printer – Customizer (preview + sliders + color svg)
 * Requiere que en la página existan:
 *  - #spw_canvas (contenedor del producto, position:relative)
 *  - #spw_product_img (imagen del producto/variante)
 *  - #spw_logo_file (input type="file")
 *  - #spw_scale, #spw_rotation, #spw_pos_x, #spw_pos_y (range inputs)
 *  - Botones de color opcionales con atributo data-spw-color="#RRGGBB"
 */
odoo.define('serial_printer_custom_wizard.customizer', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    publicWidget.registry.SPWCustomizer = publicWidget.Widget.extend({
        selector: '.spw-customizer',

        start() {
            // DOM
            this.$canvas    = this.$('#spw_canvas');
            this.$prodImg   = this.$('#spw_product_img');
            this.$file      = this.$('#spw_logo_file');

            this.$scale     = this.$('#spw_scale');
            this.$rotation  = this.$('#spw_rotation');
            this.$posX      = this.$('#spw_pos_x');
            this.$posY      = this.$('#spw_pos_y');

            this.$colorBtns = this.$('[data-spw-color]');

            // Estado
            this.$logo      = null;   // contenedor del logo (DIV con <img> o <svg> dentro)
            this.logoType   = null;   // 'img' | 'svg'

            // Asegurar position:relative en el canvas
            if (this.$canvas.length && this.$canvas.css('position') === 'static') {
                this.$canvas.css('position', 'relative');
            }

            // Bindings
            this._bindEvents();
            return this._super.apply(this, arguments);
        },

        _bindEvents() {
            this.$file.on('change', (ev) => this._onSelectFile(ev));

            const apply = () => this._applyTransform();
            this.$scale.on('input change', apply);
            this.$rotation.on('input change', apply);
            this.$posX.on('input change', apply);
            this.$posY.on('input change', apply);

            // Drag & drop del logo
            this.$canvas.on('mousedown touchstart', '#spw_logo_preview', (ev) => this._startDrag(ev));

            // Color (para SVG; en bitmap se intenta un tinte simple)
            this.$colorBtns.on('click', (ev) => {
                const color = String($(ev.currentTarget).data('spw-color') || '').trim();
                if (color) this._setColor(color);
            });
        },

        _ensureLogoContainer() {
            if (this.$logo && this.$logo.length) return;

            this.$logo = $('<div/>', {
                id: 'spw_logo_preview',
                css: {
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    width: '150px',
                    height: '150px',
                    transform: 'translate(-50%, -50%)',
                    'transform-origin': 'center center',
                    'pointer-events': 'auto',
                    'touch-action': 'none',
                },
            });
            this.$canvas.append(this.$logo);
        },

        async _onSelectFile(ev) {
            const file = ev.currentTarget.files && ev.currentTarget.files[0];
            if (!file) return;

            this._ensureLogoContainer();

            if (file.type === 'image/svg+xml') {
                // Inline SVG para poder recolorear
                const text = await file.text();
                const cleaned = text
                    .replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
                    .replace(/<foreignObject[\s\S]*?>[\s\S]*?<\/foreignObject>/gi, '');
                this.logoType = 'svg';
                this.$logo.empty().append($(cleaned).attr({ width: '100%', height: '100%' }));
            } else {
                // PNG/JPG
                this.logoType = 'img';
                const url = URL.createObjectURL(file);
                const $img = $('<img/>', {
                    src: url,
                    css: { width: '100%', height: '100%', 'object-fit': 'contain' },
                });
                this.$logo.empty().append($img);
            }

            // Colocar en el centro y aplicar sliders actuales
            this._applyTransform();
        },

        _applyTransform() {
            if (!this.$logo) return;

            const scale = parseFloat(this.$scale.val() || '1');
            const rot   = parseFloat(this.$rotation.val() || '0');
            const px    = parseFloat(this.$posX.val() || '0');   // rango esperado: -100..100
            const py    = parseFloat(this.$posY.val() || '0');

            const w = this.$canvas.outerWidth();
            const h = this.$canvas.outerHeight();
            const x = (w / 2) + (px / 100) * (w / 2);
            const y = (h / 2) + (py / 100) * (h / 2);

            this.$logo.css({ left: `${x}px`, top: `${y}px` });
            this.$logo.css('transform', `translate(-50%, -50%) rotate(${rot}deg) scale(${scale})`);
        },

        _setColor(hex) {
            if (!this.$logo) return;

            if (this.logoType === 'svg') {
                // Cambiar fill/stroke en todos los nodos del SVG
                this.$logo.find('*').each(function () {
                    const $n = $(this);
                    if ($n.attr('fill') && $n.attr('fill') !== 'none') $n.attr('fill', hex);
                    if ($n.attr('stroke') && $n.attr('stroke') !== 'none') $n.attr('stroke', hex);
                });
            } else {
                // Tinte simple para bitmaps (no perfecto pero útil para preview)
                this.$logo.css({
                    filter: 'brightness(0) saturate(100%)',
                    'background-color': hex,
                    'mix-blend-mode': 'multiply',
                });
            }
        },

        // ---- Drag support ---------------------------------------------------
        _startDrag(ev) {
            ev.preventDefault();
            const start = this._point(ev);
            const startLeft = parseFloat(this.$logo.css('left'));
            const startTop  = parseFloat(this.$logo.css('top'));

            const move = (e) => {
                const p = this._point(e);
                const dx = p.x - start.x;
                const dy = p.y - start.y;
                this.$logo.css({ left: `${startLeft + dx}px`, top: `${startTop + dy}px` });
                this._syncSlidersWithLogo();
            };
            const up = () => {
                $(document).off('mousemove touchmove', move);
                $(document).off('mouseup touchend', up);
            };

            $(document).on('mousemove touchmove', move);
            $(document).on('mouseup touchend', up);
        },

        _point(ev) {
            const oe = ev.originalEvent || ev;
            if (oe.touches && oe.touches[0]) {
                return { x: oe.touches[0].clientX, y: oe.touches[0].clientY };
            }
            return { x: oe.clientX || 0, y: oe.clientY || 0 };
        },

        _syncSlidersWithLogo() {
            const w = this.$canvas.outerWidth();
            const h = this.$canvas.outerHeight();
            const x = parseFloat(this.$logo.css('left')) - (w / 2);
            const y = parseFloat(this.$logo.css('top'))  - (h / 2);
            const px = (x / (w / 2)) * 100;
            const py = (y / (h / 2)) * 100;
            if (this.$posX.length) this.$posX.val(px).trigger('change');
            if (this.$posY.length) this.$posY.val(py).trigger('change');
        },
    });

    return publicWidget.registry.SPWCustomizer;
});