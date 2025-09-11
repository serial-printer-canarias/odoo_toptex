/** Preview y controles del personalizador (mínimos y robustos) */
(function () {
  const $ = (s) => document.querySelector(s);

  const base  = $('#spw_base_img');
  const logo  = $('#spw_logo');
  const file  = $('#spw_file');
  const scale = $('#spw_scale');
  const rot   = $('#spw_rotate');
  const posX  = $('#spw_pos_x');
  const posY  = $('#spw_pos_y');

  const colorHidden = $('#spw_color');

  function applyTransform() {
    const s = (parseInt(scale.value || '40', 10)) / 100; // % a factor
    const r = parseInt(rot.value || '0', 10);
    const x = parseInt(posX.value || '50', 10);
    const y = parseInt(posY.value || '55', 10);

    logo.style.left = x + '%';
    logo.style.top  = y + '%';
    logo.style.width = (s * 100) + '%';          // ancho relativo al lienzo
    logo.style.transform = `translate(-50%, -50%) rotate(${r}deg)`;
  }

  function selectColor(hex) {
    if (!hex) return;
    colorHidden.value = hex;
    document.querySelectorAll('.spw-color').forEach(b => {
      b.classList.toggle('selected', b.dataset.color === hex);
    });
    // (no recoloreamos la imagen raster; guardamos la selección)
  }

  // Subida del logo
  if (file) {
    file.addEventListener('change', (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        logo.src = e.target.result;
        logo.classList.remove('d-none');
        // Espera a que se cargue para aplicar transformaciones
        logo.onload = () => applyTransform();
      };
      reader.readAsDataURL(f);
    });
  }

  // Sliders
  [scale, rot, posX, posY].forEach(ctrl => {
    if (ctrl) ctrl.addEventListener('input', applyTransform);
  });

  // Posiciones rápidas
  document.querySelectorAll('.spw-quick').forEach(btn => {
    btn.addEventListener('click', () => {
      const pos = btn.dataset.pos;
      if (pos === 'left_chest')   { posX.value = 32; posY.value = 58; scale.value = 32; }
      else if (pos === 'right_chest') { posX.value = 68; posY.value = 58; scale.value = 32; }
      else if (pos === 'back')    { posX.value = 50; posY.value = 35; scale.value = 50; }
      else                        { posX.value = 50; posY.value = 55; }
      applyTransform();
    });
  });

  // Paleta de colores
  document.querySelectorAll('.spw-color').forEach(btn => {
    btn.style.background = btn.dataset.color;
    btn.addEventListener('click', () => selectColor(btn.dataset.color));
  });
  // Selección inicial
  const first = document.querySelector('.spw-color');
  if (first) selectColor(first.dataset.color);

  // Arrastrar el logo con el puntero
  let dragging = false, sx = 0, sy = 0;
  function onPointerDown(e) {
    dragging = true;
    logo.setPointerCapture(e.pointerId);
    logo.classList.add('dragging');
    sx = e.clientX; sy = e.clientY;
  }
  function onPointerUp() {
    dragging = false;
    logo.classList.remove('dragging');
  }
  function onPointerMove(e) {
    if (!dragging) return;
    const rect = base.getBoundingClientRect();
    const dx = e.clientX - sx;
    const dy = e.clientY - sy;
    sx = e.clientX; sy = e.clientY;

    const nx = Math.min(100, Math.max(0, parseInt(posX.value, 10) + (dx / rect.width) * 100));
    const ny = Math.min(100, Math.max(0, parseInt(posY.value, 10) + (dy / rect.height) * 100));
    posX.value = nx; posY.value = ny;
    applyTransform();
  }

  if (logo) {
    logo.addEventListener('pointerdown', onPointerDown);
    logo.addEventListener('pointerup', onPointerUp);
    logo.addEventListener('pointercancel', onPointerUp);
    logo.addEventListener('pointermove', onPointerMove);
  }
})();