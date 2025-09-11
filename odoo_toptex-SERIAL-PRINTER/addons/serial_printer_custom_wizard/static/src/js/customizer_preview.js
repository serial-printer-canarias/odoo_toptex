/** Preview del logo en el customizer (canvas) */
odoo.define('serial_printer_custom_wizard.customizer_preview', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.spwCustomizerPreview = publicWidget.Widget.extend({
    selector: '#spw_canvas, #spw_page',           // cualquiera de los dos
    start() {
      const canvas  = document.getElementById('spw_canvas');
      const baseImg = document.getElementById('spw_base_img');
      const input   = document.getElementById('spw_logo');
      if (!canvas || !baseImg || !input) return;

      const ctx = canvas.getContext('2d');
      const state = { logo:null, scale:0.3, rotate:0, x:0.5, y:0.5 };

      function resizeCanvas() {
        // Ajusta canvas al tamaño natural de la imagen base
        const w = baseImg.naturalWidth || baseImg.width;
        const h = baseImg.naturalHeight || baseImg.height;
        if (!w || !h) return;
        canvas.width  = w;
        canvas.height = h;
        draw();
      }

      function draw() {
        ctx.clearRect(0,0,canvas.width,canvas.height);
        ctx.drawImage(baseImg, 0, 0, canvas.width, canvas.height);
        if (state.logo) {
          const w = canvas.width * state.scale;
          const h = state.logo.height * (w / state.logo.width);
          const x = state.x * canvas.width;
          const y = state.y * canvas.height;
          ctx.save();
          ctx.translate(x, y);
          ctx.rotate(state.rotate * Math.PI/180);
          ctx.drawImage(state.logo, -w/2, -h/2, w, h);
          ctx.restore();
        }
      }

      // Carga logo
      input.addEventListener('change', (ev) => {
        const f = ev.target.files && ev.target.files[0];
        if (!f) return;
        const r = new FileReader();
        r.onload = () => {
          const img = new Image();
          img.onload = () => { state.logo = img; draw(); };
          img.src = r.result;
        };
        r.readAsDataURL(f);
      });

      // Sliders
      const bind = (id, fn) => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', e => { fn(parseFloat(e.target.value)); draw(); });
      };
      bind('spw_scale',  v => state.scale = v);   // 0..1 (p.ej. 0.30)
      bind('spw_rotate', v => state.rotate = v);  // grados -180..180
      bind('spw_pos_x',  v => state.x = v);       // 0..1
      bind('spw_pos_y',  v => state.y = v);       // 0..1

      // pinta al cargar
      if (baseImg.complete) resizeCanvas(); else baseImg.onload = resizeCanvas;
      window.addEventListener('resize', draw);
    }
  });
});