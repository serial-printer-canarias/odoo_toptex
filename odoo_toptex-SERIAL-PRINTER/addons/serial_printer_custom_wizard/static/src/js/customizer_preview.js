/** SPW – Previsualización en canvas + envío al carrito */
odoo.define('serial_printer_custom_wizard.customizer_preview', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.SPWCustomizer = publicWidget.Widget.extend({
    selector: '#spw_canvas',
    start() {
      this.canvas = this.el;
      this.ctx = this.canvas.getContext('2d');
      this.baseImg = new Image();
      this.logoImg = new Image();
      this.state = { x: 0.5, y: 0.5, scale: 120, rot: 0 }; // x,y en %, escala px aprox

      this._bindUI();
      this._loadBase();
      return this._super(...arguments);
    },

    _bindUI() {
      const q = (sel) => document.querySelector(sel);
      this.inputFile  = q('#spw_file');
      this.rScale     = q('#spw_scale');
      this.rRotate    = q('#spw_rotate');
      this.rX         = q('#spw_pos_x');
      this.rY         = q('#spw_pos_y');
      this.hPreview   = q('#spw_preview_png');
      this.hParams    = q('#spw_params_json');
      this.hAreas     = q('#spw_areas');
      this.colorWrap  = q('#spw_colors');
      this.submitBtn  = q('#spw_submit');

      // File
      this.inputFile?.addEventListener('change', (e) => {
        const f = e.target.files[0];
        if (!f) return;
        const reader = new FileReader();
        reader.onload = () => {
          this.logoImg = new Image();
          this.logoImg.onload = () => this._redraw();
          this.logoImg.src = reader.result;
        };
        reader.readAsDataURL(f);
      });

      // Sliders
      [this.rScale, this.rRotate, this.rX, this.rY].forEach(inp => {
        inp?.addEventListener('input', () => {
          this.state.scale = parseInt(this.rScale.value, 10);
          this.state.rot   = parseInt(this.rRotate.value, 10) * Math.PI / 180;
          this.state.x     = parseInt(this.rX.value, 10) / 100;
          this.state.y     = parseInt(this.rY.value, 10) / 100;
          this._redraw();
        });
      });

      // Drag & drop sobre el canvas
      let dragging = false;
      this.canvas.addEventListener('mousedown', (ev) => { dragging = true; this._setXYFromEvent(ev); });
      window.addEventListener('mouseup', () => dragging = false);
      this.canvas.addEventListener('mousemove', (ev) => { if (dragging) this._setXYFromEvent(ev); });
      // Touch
      this.canvas.addEventListener('touchstart', (ev) => { dragging = true; this._setXYFromEvent(ev.touches[0]); });
      this.canvas.addEventListener('touchmove',  (ev) => { if (dragging) this._setXYFromEvent(ev.touches[0]); });

      // Posiciones rápidas (checkbox → CSV)
      document.querySelector('#spw_positions')?.addEventListener('change', () => {
        const values = [...document.querySelectorAll('#spw_positions input:checked')].map(i => i.value);
        this.hAreas.value = values.join(',');
        // Coloca rápido según la última marcada (si no es 'libre')
        const last = values[values.length - 1];
        if (last === 'pecho_izq')  { this._quick(0.32, 0.30); }
        if (last === 'pecho_dcha') { this._quick(0.68, 0.30); }
        if (last === 'espalda')    { this._quick(0.50, 0.22); }
      });

      // Swatches de color (datos vienen en data-colors)
      try {
        const colors = JSON.parse(this.colorWrap?.dataset.colors || '[]');
        this._renderSwatches(colors);
      } catch (_) {}

      // Envío: genera PNG y params
      this.submitBtn?.addEventListener('click', () => {
        this.hPreview.value = this.canvas.toDataURL('image/png');
        this.hParams.value = JSON.stringify({
          x: this.state.x, y: this.state.y,
          scale: this.state.scale, rot_deg: (this.state.rot * 180 / Math.PI)
        });
      });
    },

    _renderSwatches(colors) {
      const setSelected = (code, hex) => {
        document.querySelectorAll('.spw-swatch').forEach(n => n.classList.remove('selected'));
        const el = this.colorWrap.querySelector(`[data-code="${code}"]`);
        if (el) el.classList.add('selected');
        const codeInput = document.querySelector('#spw_color_code');
        const hexInput  = document.querySelector('#spw_color_hex');
        if (codeInput) codeInput.value = code;
        if (hexInput)  hexInput.value  = hex;
      };
      colors.forEach(c => {
        const b = document.createElement('button');
        b.type = 'button';
        b.className = 'spw-swatch';
        b.style.background = c.hex;
        b.dataset.code = c.code;
        b.title = `${c.name} (${c.code})`;
        b.addEventListener('click', () => setSelected(c.code, c.hex));
        this.colorWrap.appendChild(b);
      });
      // Selección por defecto:
      if (colors[0]) setSelected(colors[0].code, colors[0].hex);
    },

    _quick(px, py) {
      this.state.x = px; this.state.y = py;
      this.rX.value = Math.round(px * 100);
      this.rY.value = Math.round(py * 100);
      this._redraw();
    },

    _setXYFromEvent(ev) {
      const rect = this.canvas.getBoundingClientRect();
      const x = (ev.clientX - rect.left) / rect.width;
      const y = (ev.clientY - rect.top) / rect.height;
      this.state.x = Math.min(1, Math.max(0, x));
      this.state.y = Math.min(1, Math.max(0, y));
      this.rX.value = Math.round(this.state.x * 100);
      this.rY.value = Math.round(this.state.y * 100);
      this._redraw();
    },

    _loadBase() {
      // Tamaño canvas responsivo (relación del sitio)
      const w = this.canvas.clientWidth || 900;
      this.canvas.width  = w;
      this.canvas.height = Math.round(w * 0.85);
      this.baseImg.onload = () => this._redraw();
      this.baseImg.src = window.SPW_BASE_URL || document.querySelector('#spw_base_url')?.value || '';
    },

    _redraw() {
      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      // Base
      if (this.baseImg.complete && this.baseImg.naturalWidth) {
        ctx.drawImage(this.baseImg, 0, 0, this.canvas.width, this.canvas.height);
      }

      // Logo
      if (this.logoImg.complete && this.logoImg.naturalWidth) {
        const cx = this.canvas.width * this.state.x;
        const cy = this.canvas.height * this.state.y;
        const s  = this.state.scale;

        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(this.state.rot);
        ctx.drawImage(this.logoImg, -s/2, -s/2, s, s);
        ctx.restore();
      } else {
        // Píxel guía
        const cx = this.canvas.width * this.state.x;
        const cy = this.canvas.height * this.state.y;
        ctx.beginPath();
        ctx.arc(cx, cy, 12, 0, Math.PI*2);
        ctx.fillStyle = '#ffffff';
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 2;
        ctx.fill(); ctx.stroke();
      }
    },
  });
});