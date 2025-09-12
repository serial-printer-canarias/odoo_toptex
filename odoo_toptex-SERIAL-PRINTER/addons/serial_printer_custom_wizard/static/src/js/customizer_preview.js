(function () {
  'use strict';

  const s = {
    canvas: null,
    productImg: null,
    logo: null,
    input: null,
    size: null,
    rotate: null,
    posX: null,
    posY: null,
  };

  function setTransform() {
    if (!s.logo) return;
    const scale = (s.size ? Number(s.size.value) : 100) / 100;
    const rot = s.rotate ? Number(s.rotate.value) : 0;
    const x = s.posX ? Number(s.posX.value) : 0;
    const y = s.posY ? Number(s.posY.value) : 0;

    s.logo.style.transform =
      `translate(calc(-50% + ${x}% ), calc(-50% + ${y}% )) rotate(${rot}deg) scale(${scale})`;
  }

  function onFileChange(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    s.logo.src = url;
    s.logo.classList.remove('d-none');
    setTransform();
  }

  function quickPosition(e) {
    e.preventDefault();
    const pos = e.currentTarget.getAttribute('data-pos');
    switch (pos) {
      case 'left_chest': s.posX.value = -20; s.posY.value = -5; s.size.value = 90; break;
      case 'right_chest': s.posX.value = 20; s.posY.value = -5; s.size.value = 90; break;
      case 'back': s.posX.value = 0; s.posY.value = 10; s.size.value = 140; break;
      default: s.posX.value = 0; s.posY.value = 0; s.size.value = 100;
    }
    setTransform();
  }

  function init() {
    s.canvas = document.querySelector('.spw-canvas-wrapper');
    s.productImg = document.getElementById('spw_product_img');
    s.logo = document.getElementById('spw_logo_preview');
    s.input = document.getElementById('spw_logo_input');
    s.size = document.getElementById('spw_size');
    s.rotate = document.getElementById('spw_rotate');
    s.posX = document.getElementById('spw_pos_x');
    s.posY = document.getElementById('spw_pos_y');

    if (!s.canvas || !s.logo) return;

    s.input && s.input.addEventListener('change', onFileChange);
    [s.size, s.rotate, s.posX, s.posY].forEach(el => el && el.addEventListener('input', setTransform));
    document.querySelectorAll('.spw-quick').forEach(b => b.addEventListener('click', quickPosition));

    // arrastre básico
    let dragging = false;
    s.logo.addEventListener('mousedown', () => (dragging = true));
    document.addEventListener('mouseup', () => (dragging = false));
    s.canvas.addEventListener('mousemove', (ev) => {
      if (!dragging) return;
      const rect = s.canvas.getBoundingClientRect();
      const xPct = ((ev.clientX - rect.left) / rect.width) * 100 - 50;
      const yPct = ((ev.clientY - rect.top) / rect.height) * 100 - 50;
      s.posX.value = Math.max(-50, Math.min(50, xPct));
      s.posY.value = Math.max(-50, Math.min(50, yPct));
      setTransform();
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();