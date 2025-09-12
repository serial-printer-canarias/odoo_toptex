/** Vista previa del logo (solo front, sin tocar nada del carrito) */
document.addEventListener('DOMContentLoaded', function () {
  const fileInput = document.getElementById('spw_logo_input');
  const overlay = document.getElementById('spw_logo_preview');
  const canvas = document.getElementById('spw_canvas');

  if (!fileInput || !overlay || !canvas) return;

  // Estado simple
  let posX = 50;   // en %
  let posY = 60;   // en %
  let scale = 1.0;
  let rot = 0;

  function applyTransform() {
    overlay.style.left = posX + '%';
    overlay.style.top = posY + '%';
    overlay.style.transform = `translate(-50%, -50%) rotate(${rot}deg) scale(${scale})`;
  }

  // Cargar imagen del logo
  fileInput.addEventListener('change', function (e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    // Límite blando 10MB
    if (file.size > 10 * 1024 * 1024) {
      alert('El archivo supera 10MB.');
      return;
    }

    const reader = new FileReader();
    reader.onload = function (ev) {
      overlay.src = ev.target.result;
      overlay.classList.remove('d-none');
      // Reset colocación
      posX = 50; posY = 60; scale = 1.0; rot = 0;
      applyTransform();
    };
    reader.readAsDataURL(file);
  });

  // Controles
  function byId(id) { return document.getElementById(id); }
  const up = byId('spw_move_up');
  const down = byId('spw_move_down');
  const left = byId('spw_move_left');
  const right = byId('spw_move_right');
  const sMinus = byId('spw_scale_minus');
  const sPlus = byId('spw_scale_plus');
  const rLeft = byId('spw_rotate_left');
  const rRight = byId('spw_rotate_right');
  const reset = byId('spw_reset');

  if (up) up.addEventListener('click', () => { posY = Math.max(0, posY - 2); applyTransform(); });
  if (down) down.addEventListener('click', () => { posY = Math.min(100, posY + 2); applyTransform(); });
  if (left) left.addEventListener('click', () => { posX = Math.max(0, posX - 2); applyTransform(); });
  if (right) right.addEventListener('click', () => { posX = Math.min(100, posX + 2); applyTransform(); });
  if (sMinus) sMinus.addEventListener('click', () => { scale = Math.max(0.1, +(scale - 0.05).toFixed(2)); applyTransform(); });
  if (sPlus) sPlus.addEventListener('click', () => { scale = Math.min(5, +(scale + 0.05).toFixed(2)); applyTransform(); });
  if (rLeft) rLeft.addEventListener('click', () => { rot = (rot - 5) % 360; applyTransform(); });
  if (rRight) rRight.addEventListener('click', () => { rot = (rot + 5) % 360; applyTransform(); });
  if (reset) reset.addEventListener('click', () => { posX = 50; posY = 60; scale = 1.0; rot = 0; applyTransform(); });

  // Colores (placeholder: guarda el color elegido; aplicar al SVG vendrá después)
  document.querySelectorAll('.spw-color-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const color = btn.dataset.color || '#000000';
      // Aquí solo marcamos la selección visualmente
      document.querySelectorAll('.spw-color-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      // Guardar color seleccionado para uso posterior si hace falta
      overlay.dataset.spwColor = color;
    });
  });
});