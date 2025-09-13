/** SPW - Previsualización de logo sobre la imagen del producto */
(function () {
  function qs(id) { return document.getElementById(id); }

  function initPreview() {
    const fileInput = qs('spw_logo_input');
    const canvas = qs('spw_canvas');
    const preview = qs('spw_logo_preview');

    if (!fileInput || !canvas || !preview) return;

    // Asegurar estilos base
    canvas.style.position = canvas.style.position || 'relative';
    preview.style.position = 'absolute';
    preview.style.left = '50%';
    preview.style.top = '60%';
    preview.style.transform = 'translate(-50%, -50%)';
    preview.style.pointerEvents = 'none';
    preview.style.zIndex = '5';
    preview.style.maxWidth = '80%';
    preview.style.maxHeight = '80%';
    preview.style.opacity = '1';

    function showPreviewFromFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function (e) {
        preview.src = e.target.result;   // DataURL (sirve PNG/JPG/SVG)
        preview.classList.remove('d-none');
      };
      reader.readAsDataURL(file);
    }

    fileInput.addEventListener('change', function (ev) {
      const f = ev.target.files && ev.target.files[0];
      showPreviewFromFile(f);
    });

    // Controles opcionales si existen (no obligatorios)
    const size = qs('spw_size');
    const posX = qs('spw_pos_x');
    const posY = qs('spw_pos_y');
    const rot  = qs('spw_rotation');

    function updateTransform() {
      if (!preview) return;
      const s = size ? (Number(size.value || 100) / 100) : 1;
      const x = posX ? Number(posX.value || 0) : 0;
      const y = posY ? Number(posY.value || 0) : 0;
      const r = rot  ? Number(rot.value  || 0) : 0;
      preview.style.transform =
        `translate(-50%, -50%) translate(${x}%, ${y}%) rotate(${r}deg) scale(${s})`;
    }

    [size, posX, posY, rot].forEach(ctrl => {
      if (ctrl) ctrl.addEventListener('input', updateTransform);
    });

    // Reset si existe window.spwReset
    window.spwReset = function () {
      preview.classList.add('d-none');
      preview.removeAttribute('src');
      if (size) size.value = 100;
      if (posX) posX.value = 0;
      if (posY) posY.value = 10;
      if (rot)  rot.value  = 0;
      updateTransform();
    };

    updateTransform();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPreview);
  } else {
    initPreview();
  }
})();