odoo.define('serial_printer_custom_wizard.customizer', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.SPWCustomizer = publicWidget.Widget.extend({
    selector: '.spw-container',
    start() {
      const file = this.el.querySelector('#spw_file');
      const logo = this.el.querySelector('#spw_logo');
      const base = this.el.querySelector('#spw_base_img');

      if (file && logo) {
        file.addEventListener('change', (e) => {
          const f = e.target.files && e.target.files[0];
          if (!f) return;
          const reader = new FileReader();
          reader.onload = (ev) => {
            logo.src = ev.target.result;
            logo.classList.remove('d-none');
          };
          reader.readAsDataURL(f);
        });
      }

      // Sliders
      const scale = this.el.querySelector('#spw_scale');
      const rot = this.el.querySelector('#spw_rotate');
      const posX = this.el.querySelector('#spw_pos_x');
      const posY = this.el.querySelector('#spw_pos_y');

      const apply = () => {
        if (!logo) return;
        const s = (scale ? Number(scale.value) : 100) / 100;
        const r = rot ? Number(rot.value) : 0;
        const x = posX ? Number(posX.value) : 50;
        const y = posY ? Number(posY.value) : 50;
        logo.style.left = x + '%';
        logo.style.top = y + '%';
        logo.style.transform = `translate(-50%, -50%) rotate(${r}deg) scale(${s})`;
      };

      [scale, rot, posX, posY].forEach(inp => inp && inp.addEventListener('input', apply));
      apply();

      return this._super(...arguments);
    }
  });
});