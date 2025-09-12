/** @odoo-module **/
(function () {
  const ready = (fn) => {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  };

  ready(() => {
    // Solo actúa en la página del personalizador
    const page = document.querySelector('.spw-customizer');
    if (!page) return;

    const logo = document.getElementById('spw_logo_preview');
    const fileInput = document.getElementById('spw_logo_input');
    const rangeScale = document.getElementById('spw_scale');
    const rangeRotate = document.getElementById('spw_rotate');
    const rangeX = document.getElementById('spw_pos_x');
    const rangeY = document.getElementById('spw_pos_y');

    const apply = () => {
      if (!logo || logo.classList.contains('d-none')) return;
      const scale = (parseInt(rangeScale?.value || '100', 10) / 100);
      const rot = parseInt(rangeRotate?.value || '0', 10);
      const posX = parseInt(rangeX?.value || '50', 10);
      const posY = parseInt(rangeY?.value || '50', 10);

      logo.style.left = posX + '%';
      logo.style.top = posY + '%';
      logo.style.transform = `translate(-50%, -50%) scale(${scale}) rotate(${rot}deg)`;
    };

    // Carga del archivo y muestra del preview
    fileInput?.addEventListener('change', (ev) => {
      const file = ev.target.files && ev.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        logo.src = e.target.result;
        logo.classList.remove('d-none'); // se muestra cuando hay logo
        apply();                          // aplica tamaño/pos/rotación iniciales
      };
      reader.readAsDataURL(file);
    });

    [rangeScale, rangeRotate, rangeX, rangeY]
      .forEach(el => el && el.addEventListener('input', apply));
  });
})();