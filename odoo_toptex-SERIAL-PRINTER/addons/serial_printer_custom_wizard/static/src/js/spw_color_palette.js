odoo.define('serial_printer_custom_wizard.spw_color_palette', [], function () {
  'use strict';

  // Lanzador simple sin dependencias
  function onReady(cb) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', cb, { once: true });
    } else cb();
  }

  // Paleta (≈30 colores) de claro → oscuro, con pasteles y nombre + HEX
  const PALETTE = [
    { name: 'Blanco',            hex: '#FFFFFF' },
    { name: 'Marfil',            hex: '#FFFFF0' },
    { name: 'Lino',              hex: '#FAF0E6' },
    { name: 'Beige',             hex: '#F5F5DC' },
    { name: 'Melocotón pastel',  hex: '#FFDAB9' },
    { name: 'Rosa palo',         hex: '#F4C2C2' },
    { name: 'Rosa pastel',       hex: '#FFC0CB' },
    { name: 'Lavanda',           hex: '#E6E6FA' },
    { name: 'Lila',              hex: '#C8A2C8' },
    { name: 'Amarillo pastel',   hex: '#FFFACD' },
    { name: 'Albaricoque',       hex: '#FBCEB1' },
    { name: 'Coral suave',       hex: '#FFB3A7' },
    { name: 'Salmón',            hex: '#FA8072' },
    { name: 'Melón',             hex: '#FFDAB5' },
    { name: 'Menta',             hex: '#AAF0D1' },
    { name: 'Verde agua',        hex: '#71E6C6' },
    { name: 'Turquesa',          hex: '#40E0D0' },
    { name: 'Cian',              hex: '#00FFFF' },
    { name: 'Azul bebé',         hex: '#A7C7E7' },
    { name: 'Cielo',             hex: '#87CEEB' },
    { name: 'Azul',              hex: '#1D4ED8' },
    { name: 'Magenta',           hex: '#FF00FF' },
    { name: 'Rojo',              hex: '#EF4444' },
    { name: 'Naranja',           hex: '#FB923C' },
    { name: 'Amarillo',          hex: '#FACC15' },
    { name: 'Verde',             hex: '#10B981' },
    { name: 'Gris claro',        hex: '#E5E7EB' },
    { name: 'Plata',             hex: '#D1D5DB' },
    { name: 'Gris frío',         hex: '#9CA3AF' },
    { name: 'Gris cálido',       hex: '#A8A29E' },
    { name: 'Pizarra',           hex: '#64748B' },
    { name: 'Antracita',         hex: '#374151' },
    { name: 'Negro',             hex: '#000000' },
  ];

  function createPaletteFor(input) {
    if (!input || input.dataset.spwPalette === '1') return;
    input.dataset.spwPalette = '1';

    // Contenedor vertical (para móvil se ve mejor en columna)
    const wrap = document.createElement('div');
    wrap.className = 'spw-color-palette';
    wrap.style.cssText = 'display:flex;flex-direction:column;gap:8px;margin-top:10px';

    // Estilos mínimos (no tocamos CSS global)
    const makeRow = (c) => {
      const row = document.createElement('button');
      row.type = 'button';
      row.className = 'spw-swatch';
      row.title = `${c.name} ${c.hex}`;
      row.style.cssText = 'display:flex;align-items:center;gap:8px;padding:6px 8px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;cursor:pointer;text-align:left';

      const dot = document.createElement('span');
      dot.style.cssText = 'width:16px;height:16px;border-radius:9999px;border:1px solid rgba(0,0,0,.2);display:inline-block;';
      dot.style.background = c.hex;

      const label = document.createElement('span');
      label.textContent = `${c.name} (${c.hex})`;
      label.style.cssText = 'font-size:12px;line-height:1';

      row.appendChild(dot);
      row.appendChild(label);

      row.addEventListener('click', () => {
        input.value = c.hex;
        // Notificamos a cualquier listener que ya tengas
        input.dispatchEvent(new Event('input',  { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
        // Marca visual
        wrap.querySelectorAll('.spw-swatch').forEach(b => b.style.outline = 'none');
        row.style.outline = '2px solid #4f46e5';
      });

      return row;
    };

    PALETTE.forEach(c => wrap.appendChild(makeRow(c)));
    input.insertAdjacentElement('afterend', wrap);
  }

  function boot() {
    // No tocamos nada existente: si hay un input de color, añadimos la paleta al lado.
    const targets = document.querySelectorAll('input[name="spw_svg_color"], input#spw_svg_color, input[data-spw-color]');
    targets.forEach(createPaletteFor);

    // Por si el DOM del personalizador cambia dinámicamente
    const root = document.body;
    new MutationObserver(muts => {
      for (const m of muts) {
        m.addedNodes && m.addedNodes.forEach(n => {
          if (!(n instanceof HTMLElement)) return;
          n.querySelectorAll && n.querySelectorAll('input[name="spw_svg_color"], input#spw_svg_color, input[data-spw-color]')
            .forEach(createPaletteFor);
        });
      }
    }).observe(root, { childList: true, subtree: true });
  }

  onReady(boot);
  return {};
});