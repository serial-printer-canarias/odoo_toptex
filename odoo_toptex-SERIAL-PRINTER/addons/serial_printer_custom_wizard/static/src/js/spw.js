/** serial_printer_custom_wizard/static/src/js/spw.js **/
odoo.define('serial_printer_custom_wizard.spw', function (require) {
    "use strict";

    const publicRoot = require('web.public.root');

    function onReady() {
        const canvas = document.querySelector('.spw-canvas-wrapper');
        if (!canvas) return;

        const baseImg = document.getElementById('spw_base_img');
        const logoImg = document.getElementById('spw_logo');

        const fileInput = document.getElementById('spw_file');
        const scale = document.getElementById('spw_scale');
        const rotate = document.getElementById('spw_rotate');
        const posX = document.getElementById('spw_pos_x');
        const posY = document.getElementById('spw_pos_y');

        const swatches = document.querySelectorAll('.spw-swatch');
        const quickBtns = document.querySelectorAll('.spw-quick');

        let state = {
            x: 50, y: 50, s: 1, r: 0, color: null,
            dragging: false, dragOffsetX: 0, dragOffsetY: 0,
        };

        function applyTransform() {
            logoImg.style.left = state.x + '%';
            logoImg.style.top  = state.y + '%';
            logoImg.style.transform =
                `translate(-50%, -50%) rotate(${state.r}deg) scale(${state.s})`;
        }

        // Cargar logo
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const f = e.target.files && e.target.files[0];
                if (!f) return;
                const reader = new FileReader();
                reader.onload = () => {
                    logoImg.src = reader.result;
                    logoImg.classList.remove('d-none');
                    // reset
                    state = { x:50, y:50, s:1, r:0, color: state.color, dragging:false, dragOffsetX:0, dragOffsetY:0 };
                    scale.value = "1";
                    rotate.value = "0";
                    posX.value = "50";
                    posY.value = "50";
                    applyTransform();
                };
                reader.readAsDataURL(f);
            });
        }

        // Sliders
        scale && scale.addEventListener('input', () => { state.s = parseFloat(scale.value); applyTransform(); });
        rotate && rotate.addEventListener('input', () => { state.r = parseInt(rotate.value || 0); applyTransform(); });
        posX && posX.addEventListener('input', () => { state.x = parseInt(posX.value || 0); applyTransform(); });
        posY && posY.addEventListener('input', () => { state.y = parseInt(posY.value || 0); applyTransform(); });

        // Arrastrar logo
        function canvasPointFromEvent(ev) {
            const rect = canvas.getBoundingClientRect();
            const cx = ((ev.clientX - rect.left) / rect.width) * 100;
            const cy = ((ev.clientY - rect.top) / rect.height) * 100;
            return {cx: Math.min(100, Math.max(0, cx)), cy: Math.min(100, Math.max(0, cy))};
        }
        logoImg.addEventListener('pointerdown', (ev) => {
            ev.preventDefault();
            logoImg.setPointerCapture(ev.pointerId);
            state.dragging = true;
            const {cx, cy} = canvasPointFromEvent(ev);
            state.dragOffsetX = cx - state.x;
            state.dragOffsetY = cy - state.y;
        });
        logoImg.addEventListener('pointermove', (ev) => {
            if (!state.dragging) return;
            const {cx, cy} = canvasPointFromEvent(ev);
            state.x = cx - state.dragOffsetX;
            state.y = cy - state.dragOffsetY;
            posX.value = String(Math.round(state.x));
            posY.value = String(Math.round(state.y));
            applyTransform();
        });
        logoImg.addEventListener('pointerup', () => { state.dragging = false; });

        // Paleta de colores (solo marca selección visual y guarda valor)
        swatches.forEach(sw => {
            sw.addEventListener('click', () => {
                swatches.forEach(s => s.classList.remove('is-active'));
                sw.classList.add('is-active');
                state.color = sw.dataset.color;
            });
        });

        // Posiciones rápidas
        quickBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const p = btn.dataset.pos;
                if (p === 'left-chest')  { state.x = 35; state.y = 42; }
                if (p === 'right-chest') { state.x = 65; state.y = 42; }
                if (p === 'back')        { state.x = 50; state.y = 30; }
                if (p === 'free')        { state.x = 50; state.y = 50; }
                posX.value = String(state.x); posY.value = String(state.y);
                applyTransform();
            });
        });

        // Añadir al carrito: aquí solo prevenimos que recargue
        const addBtn = document.getElementById('spw_add_to_cart');
        addBtn && addBtn.addEventListener('click', (e) => {
            // TODO: enviar estos datos al backend o como nota de línea
            // Por ahora solo evitamos submit real para que no bloquee la demo
            e.preventDefault();
            addBtn.classList.add('disabled');
            setTimeout(() => addBtn.classList.remove('disabled'), 800);
        });

        // Si hay variante sin imagen, ya estamos usando la del template (XML).
        // Nada que hacer aquí en JS.
    }

    publicRoot.ready(onReady);
});