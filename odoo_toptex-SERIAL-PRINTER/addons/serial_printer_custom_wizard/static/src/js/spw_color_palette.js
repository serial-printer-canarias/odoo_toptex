/** SPW – Paleta de colores (grid 3/2/1 columnas + nombre y código) */
(function () {
  'use strict';

  const READY = (cb) =>
    document.readyState === 'loading'
      ? document.addEventListener('DOMContentLoaded', cb, { once: true })
      : cb();

  // ===== Paleta (30 tonos de blanco → negro con pasteles) =====
  const COLORS = [
    { name: 'Blanco',          hex: '#FFFFFF' },
    { name: 'Hueso pastel',    hex: '#F7F3E8' },
    { name: 'Crema',           hex: '#FFF2CC' },
    { name: 'Amarillo suave',  hex: '#FFF5A8' },
    { name: 'Melocotón',       hex: '#FFD9B3' },
    { name: 'Rosa pastel',     hex: '#FAD0E4' },
    { name: 'Lavanda',         hex: '#E6E0F8' },
    { name: 'Lila',            hex: '#D7C4F3' },
    { name: 'Malva',           hex: '#C7B8EA' },
    { name: 'Azul cielo',      hex: '#93C5FD' },
    { name: 'Azul pastel',     hex: '#BDE0FE' },
    { name: 'Azul medio',      hex: '#60A5FA' },
    { name: 'Turquesa',        hex: '#7DD3FC' },
    { name: 'Cian',            hex: '#22D3EE' },
    { name: 'Menta',           hex: '#A7F3D0' },
    { name: 'Verde pastel',    hex: '#C7EFCF' },
    { name: 'Verde medio',     hex: '#34D399' },
    { name: 'Lima',            hex: '#A3E635' },
    { name: 'Mostaza',         hex: '#EAB308' },
    { name: 'Naranja',         hex: '#FB923C' },
    { name: 'Coral',           hex: '#FB7185' },
    { name: 'Rojo',            hex: '#EF4444' },
    { name: 'Granate',         hex: '#991B1B' },
    { name: 'Marrón',          hex: '#8B5E34' },
    { name: 'Topo',            hex: '#A8A29E' },
    { name: 'Gris claro',      hex: '#E5E7EB' },
    { name: 'Gris medio',      hex: '#9CA3AF' },
    { name: 'Gris oscuro',     hex: '#4B5563' },
    { name: 'Azul marino',     hex: '#1E3A8A' },
    { name: 'Negro',           hex: '#000000' },
  ];

  // ===== CSS embebido (3 columnas desktop, 2 tablet, 1 móvil) =====
  function injectCSS() {
    if (document.getElementById('spwColorCSS')) return;
    const style = document.createElement('style');
    style.id = 'spwColorCSS';
    style.textContent = `
      .spw-color-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0 6px}
      @media (max-width:900px){.spw-color-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
      @media (max-width:520px){.spw-color-grid{grid-template-columns:1fr}}
      .spw-color-item{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;cursor:pointer;user-select:none}
      .spw-color-item:hover{box-shadow:0 1px 3px rgba(0,0,0,.08)}
      .spw-color-dot{width:22px;height:22px;border-radius:9999px;border:1px solid rgba(0,0,0,.15);flex:none}
      .spw-color-label{line-height:1.1}
      .spw-color-name{display:block;font-size:14px;font-weight:600}
      .spw-color-hex{display:block;font-size:12px;color:#6b7280}
      .spw-color-item.is-selected{outline:2px solid #111827;outline-offset:2px}
    `;
    document.head.appendChild(style);
  }

  // ===== utilidades =====
  function getColorInput() {
    return (
      document.querySelector('input[name="spw_svg_color"]') ||
      document.getElementById('spw_svg_color') ||
      document.querySelector('input[data-spw="svg-color"]')
    );
  }

  function findAnchor() {
    // Si tienes un ancla específica, dale ese id y lo cogerá primero.
    return (
      document.getElementById('spw_color_palette') ||
      document.querySelector('[data-spw="color"]') ||
      (getColorInput() && getColorInput().parentElement) ||
      document.querySelector('.o_product_configurator_form') ||
      document.querySelector('#wrap')
    );
  }

  // ===== render =====
  function renderPalette() {
    const anchor = findAnchor();
    if (!anchor) return;

    // Limpieza: quita cualquier paleta previa o listas antiguas que hubiera
    anchor
      .querySelectorAll(
        '#spwColorPalette,.spw-color-grid,.spw-color-list,.spw-color-legacy'
      )
      .forEach((el) => el.remove());

    const grid = document.createElement('div');
    grid.id = 'spwColorPalette';
    grid.className = 'spw-color-grid';

    const current = (getColorInput()?.value || '').trim().toUpperCase();

    COLORS.forEach((c) => {
      const item = document.createElement('div');
      item.className = 'spw-color-item';
      item.dataset.hex = c.hex;

      const dot = document.createElement('span');
      dot.className = 'spw-color-dot';
      dot.style.background = c.hex;

      const label = document.createElement('span');
      label.className = 'spw-color-label';
      const n = document.createElement('span');
      n.className = 'spw-color-name';
      n.textContent = c.name;
      const h = document.createElement('span');
      h.className = 'spw-color-hex';
      h.textContent = c.hex.toUpperCase();

      label.appendChild(n);
      label.appendChild(h);
      item.appendChild(dot);
      item.appendChild(label);
      grid.appendChild(item);

      if (current && current === c.hex.toUpperCase())
        item.classList.add('is-selected');

      item.addEventListener('click', () => {
        const input = getColorInput();
        if (input) {
          input.value = c.hex.toUpperCase();
          input.dispatchEvent(new Event('input', { bubbles: true }));
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        grid
          .querySelectorAll('.spw-color-item.is-selected')
          .forEach((e) => e.classList.remove('is-selected'));
        item.classList.add('is-selected');

        // Si tienes un badge/preview de color, actualízalo
        const badge =
          document.querySelector('[data-spw="color-badge"]') ||
          document.querySelector('.spw-color-current');
        if (badge) badge.textContent = c.hex.toUpperCase();
      });
    });

    anchor.appendChild(grid);
  }

  READY(() => {
    injectCSS();
    renderPalette();

    // Si el DOM cambia (páginas con AJAX), re-intenta montar la paleta
    const obs = new MutationObserver(() => {
      if (!document.getElementById('spwColorPalette')) {
        injectCSS();
        renderPalette();
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  });
})();