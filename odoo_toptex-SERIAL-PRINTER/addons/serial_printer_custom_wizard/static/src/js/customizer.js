/** serial_printer_custom_wizard/static/src/js/customizer.js **/
odoo.define('serial_printer_custom_wizard.customizer', function (require) {
    'use strict';

    var domReady = require('web.dom_ready');

    domReady(function () {
        var root = document.querySelector('.spw-customizer');
        if (!root) { return; }  // No estamos en la página del personalizador

        var stage     = root.querySelector('.spw-stage');
        var baseImg   = root.querySelector('#spw_product_img');
        var logoImg   = root.querySelector('#spw_logo_preview');
        var fileInput = root.querySelector('#spw_logo_input');

        var rangeSize = root.querySelector('#spw_size');
        var rangeRot  = root.querySelector('#spw_rotate');
        var rangeX    = root.querySelector('#spw_pos_x');
        var rangeY    = root.querySelector('#spw_pos_y');

        if (!stage || !baseImg || !logoImg || !fileInput) { return; }

        function num(v, fallback) {
            var n = parseFloat(v);
            return isNaN(n) ? fallback : n;
        }

        var state = {
            scale: num(rangeSize ? rangeSize.value : 1, 1),
            rot:   num(rangeRot  ? rangeRot.value  : 0, 0),
            x:     num(rangeX    ? rangeX.value    : 0, 0),
            y:     num(rangeY    ? rangeY.value    : 0, 0),
        };

        // Previsualización del archivo
        fileInput.addEventListener('change', function (ev) {
            var file = ev.target.files && ev.target.files[0];
            if (!file) { return; }

            try {
                var url = URL.createObjectURL(file);
                logoImg.onload = function () {
                    logoImg.style.width = '30%';
                    logoImg.style.display = 'block';
                    URL.revokeObjectURL(url);
                    if (rangeSize) rangeSize.value = '1';
                    if (rangeRot)  rangeRot.value  = '0';
                    if (rangeX)    rangeX.value    = '0';
                    if (rangeY)    rangeY.value    = '0';
                    state = { scale:1, rot:0, x:0, y:0 };
                    updateTransform();
                };
                logoImg.src = url;
            } catch (e) {
                // Nunca romper el sitio
                console.error('SPW preview error:', e);
            }
        });

        // Sliders
        function bindSlider(input, onChange) {
            if (!input) { return; }
            input.addEventListener('input', onChange);
        }

        bindSlider(rangeSize, updateTransform);
        bindSlider(rangeRot,  updateTransform);
        bindSlider(rangeX,    updateTransform);
        bindSlider(rangeY,    updateTransform);

        function clamp(n, min, max) {
            return Math.min(Math.max(n, min), max);
        }

        function updateTransform() {
            var s = num(rangeSize ? rangeSize.value : state.scale, state.scale);
            var r = num(rangeRot  ? rangeRot.value  : state.rot,   state.rot);
            var x = num(rangeX    ? rangeX.value    : state.x,     state.x);
            var y = num(rangeY    ? rangeY.value    : state.y,     state.y);

            state.scale = clamp(s, 0.1, 3);
            state.rot   = clamp(r, -180, 180);
            state.x     = clamp(x, -100, 100);
            state.y     = clamp(y, -100, 100);

            logoImg.style.transform =
                'translate(' + state.x + '%, ' + state.y + '%) rotate(' + state.rot + 'deg) scale(' + state.scale + ')';
            logoImg.style.transformOrigin = 'center center';
            logoImg.style.display = logoImg.src ? 'block' : 'none';
        }

        // Arrastrar el logo
        (function enableDrag() {
            var dragging = false, startX = 0, startY = 0;

            function pointer(e) {
                if (e.touches && e.touches[0]) {
                    return { x: e.touches[0].clientX, y: e.touches[0].clientY };
                }
                return { x: e.clientX, y: e.clientY };
            }

            logoImg.addEventListener('mousedown', onDown);
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);

            logoImg.addEventListener('touchstart', onDown, { passive: false });
            document.addEventListener('touchmove', onMove, { passive: false });
            document.addEventListener('touchend', onUp);

            function onDown(e) {
                if (logoImg.style.display === 'none') { return; }
                dragging = true;
                var p = pointer(e);
                startX = p.x; startY = p.y;
                e.preventDefault();
            }
            function onMove(e) {
                if (!dragging) { return; }
                var p = pointer(e);
                var rect = stage.getBoundingClientRect();
                var dx = ((p.x - startX) / rect.width) * 100;
                var dy = ((p.y - startY) / rect.height) * 100;
                startX = p.x; startY = p.y;

                if (rangeX) { rangeX.value = (num(rangeX.value, 0) + dx).toString(); }
                if (rangeY) { rangeY.value = (num(rangeY.value, 0) + dy).toString(); }
                updateTransform();
            }
            function onUp() { dragging = false; }
        })();

        // Oculto hasta tener imagen
        logoImg.style.display = 'none';
    });
});