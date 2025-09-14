/** SPW – Técnica + Colores (sin romper la previsualización existente) */
(function () {
  function qs(id) { return document.getElementById(id); }
  function $all(sel) { return Array.from(document.querySelectorAll(sel)); }

  let originalSvgText = null;
  let lastFileIsSvg = false;

  function getPickedColor() {
    const active = document.querySelector('.spw-color.active');
    return active ? active.dataset.color : '#000000';
  }

  function applyColorToSvgAndShow() {
    const preview = qs('spw_logo_preview');
    if (!lastFileIsSvg || !originalSvgText || !preview) return;

    const col = getPickedColor();
    try {
      let svg = originalSvgText;

      // Reemplazos básicos de fill/stroke (conserva "none")
      svg = svg
        .replace(/fill="none"/gi, 'fill="none"')
        .replace(/fill="[^"]*"/gi, `fill="${col}"`)
        .replace(/stroke="[^"]*"/gi, `stroke="${col}"`);

      // Si no hay fill en ningún nodo, aplicamos estilo global
      if (!/fill="/i.test(svg)) {
        svg = svg.replace(/<svg([^>]*)>/i, `<svg$1><style>*{fill:${col};}</style>`);
      }

      const blob = new Blob([svg], { type: 'image/svg+xml' });
      const url = URL.createObjectURL(blob);
      preview.src = url;
      preview.classList.remove('d-none');
    } catch (e) {
      console.warn('SPW: no se pudo aplicar color al SVG', e);
    }
  }

  function init() {
    const fileInput = qs('spw_logo_input');
    const colorBtns = $all('.spw-color');
    const techRadios = $all('input[name="spw_technique"]');

    // Estado oculto para futura compra
    const hTech = qs('spw_technique_val');
    const hColor = qs('spw_color_val');

    // Técnica
    techRadios.forEach(r => {
      r.addEventListener('change', () => {
        if (r.checked && hTech) hTech.value = r.value;
      });
      if (r.checked && hTech) hTech.value = r.value; // set inicial
    });

    // Colores
    colorBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        colorBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (hColor) hColor.value = btn.dataset.color || '';
        applyColorToSvgAndShow(); // si es SVG, re-render con el color
      });
    });
    // Color inicial si ninguno activo
    if (!document.querySelector('.spw-color.active') && colorBtns[0]) {
      colorBtns[0].classList.add('active');
      if (hColor) hColor.value = colorBtns[0].dataset.color || '';
    }

    // Nos enganchamos al input de archivo SOLO para detectar SVG y guardar su texto.
    if (fileInput) {
      fileInput.addEventListener('change', ev => {
        const f = ev.target.files && ev.target.files[0];
        if (!f) { originalSvgText = null; lastFileIsSvg = false; return; }

        const isSvg = (f.type || '').includes('svg') || /\.svg$/i.test(f.name);
        if (!isSvg) {
          originalSvgText = null;
          lastFileIsSvg = false;
          return; // PNG/JPG: lo maneja tu preview actual
        }

        const reader = new FileReader();
        reader.onload = e => {
          originalSvgText = String(e.target.result || '');
          lastFileIsSvg = true;
          applyColorToSvgAndShow();
        };
        reader.readAsText(f);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();