// Vanilla JS para previsualizar el logo y moverlo/rotarlo/escalar.
(function () {
  const root = document.getElementById('spw_canvas');
  if (!root) return; // no cargar nada fuera de la página de personalización

  const file = document.getElementById('spw_logo_file');
  const overlay = document.getElementById('spw_logo_preview');

  const size = document.getElementById('spw_size');
  const rot = document.getElementById('spw_rot');
  const posx = document.getElementById('spw_posx');
  const posy = document.getElementById('spw_posy');

  function applyTransform() {
    const s = (parseFloat(size?.value) || 100) / 100;
    const r = parseFloat(rot?.value) || 0;
    const x = parseFloat(posx?.value) || 0;
    const y = parseFloat(posy?.value) || 0;
    overlay.style.transform =
      `translate(-50%,-50%) translate(${x}%, ${y}%) rotate(${r}deg) scale(${s})`;
  }

  [size, rot, posx, posy].forEach(el => el && el.addEventListener('input', applyTransform));

  if (file) {
    file.addEventListener('change', (ev) => {
      const f = ev.target.files && ev.target.files[0];
      if (!f) return;

      const reader = new FileReader();
      reader.onload = (e) => {
        overlay.src = e.target.result;   // data URL
        overlay.classList.remove('d-none');
        applyTransform();
      };
      reader.readAsDataURL(f);
    });
  }
})();