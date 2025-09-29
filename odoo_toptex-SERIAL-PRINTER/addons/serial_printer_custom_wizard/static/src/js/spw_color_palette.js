/** SPW – Paleta de color (no toca nada más) */
odoo.define('serial_printer_custom_wizard.spw_color_palette', [], function () {
  'use strict';

  function onReady(cb){ if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', cb, {once:true}); else cb(); }

  // ≈30 colores, claro → oscuro (incluye pasteles)
  const PALETTE = [
    { name: 'Blanco',               hex: '#FFFFFF' },
    { name: 'Marfil',               hex: '#FFF8E7' },
    { name: 'Crema',                hex: '#FFF2CC' },
    { name: 'Amarillo pastel',      hex: '#FFF3B0' },
    { name: 'Melocotón',            hex: '#FFD8B1' },
    { name: 'Salmón pastel',        hex: '#FFB3AB' },
    { name: 'Coral suave',          hex: '#FFA69E' },
    { name: 'Rosa pastel',          hex: '#F8BBD0' },
    { name: 'Lila',                 hex: '#E6C6FF' },
    { name: 'Lavanda',              hex: '#CBB6F7' },
    { name: 'Malva suave',          hex: '#D1C4E9' },
    { name: 'Azul bebé',            hex: '#CDE9FF' },
    { name: 'Celeste',              hex: '#B3E5FC' },
    { name: 'Azul pastel',          hex: '#A7C5EB' },
    { name: 'Azul medio',           hex: '#90CAF9' },
    { name: 'Turquesa claro',       hex: '#A5F3FC' },
    { name: 'Aguamarina',           hex: '#98F5E1' },
    { name: 'Menta',                hex: '#BBF7D0' },
    { name: 'Verde pastel',         hex: '#A9DFBF' },
    { name: 'Verde manzana',        hex: '#8BD47A' },
    { name: 'Verde bosque suave',   hex: '#6AB07E' },
    { name: 'Lima pastel',          hex: '#DCE775' },
    { name: 'Mostaza suave',        hex: '#E6D77E' },
    { name: 'Arena',                hex: '#E6D5B8' },
    { name: 'Topo',                 hex: '#C2B8A3' },
    { name: 'Gris muy claro',       hex: '#F2F2F2' },
    { name: 'Gris claro',           hex: '#D9D9D9' },
    { name: 'Gris medio',           hex: '#A6A6A6' },
    { name: 'Antracita',            hex: '#4A4A4A' },
    { name: 'Negro',                hex: '#000000' },
  ];

  function injectStylesOnce() {
    if (document.getElementById('spw-palette-css')) return;
    const css = `
      .spw-color-palette{display:grid;grid-template-columns:repeat(auto-fill,minmax(88px,1fr));gap:10px;margin-top:8px}
      .spw-color-cell{display:flex;flex-direction:column;align-items:center;gap:6px;padding:8px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;cursor:pointer}
      .spw-color-dot{width:28px;height:28px;border-radius:9999px;border:1px solid rgba(0,0,0,.18)}
      .spw-color-label{font-size:11px;line-height:1.15;text-align:center;white-space:nowrap}
      .spw-color-cell.is-active{outline:2px solid #4f46e5;outline-offset:1px}
      .spw-color-current{margin-top:6px;font-size:12px}
    `;
    const s = document.createElement('style');
    s.id = 'spw-palette-css';
    s.textContent = css;
    document.head.appendChild(s);
  }

  function buildPalette(input){
    injectStylesOnce();

    // No duplicar si ya existe
    if (input.nextElementSibling && input.nextElementSibling.classList?.contains('spw-color-palette')) return;

    // Si el input es visible, lo dejamos; si no, lo ocultamos para limpiar UI
    if (getComputedStyle(input).display !== 'none') input.style.marginBottom = '6px';
    else input.type = input.type || 'hidden';

    const wrap = document.createElement('div');
    wrap.className = 'spw-color-palette';

    const current = document.createElement('div');
    current.className = 'spw-color-current';
    current.textContent = input.value ? `Seleccionado: ${input.value}` : 'Selecciona un color';
    input.insertAdjacentElement('afterend', current);
    current.insertAdjacentElement('afterend', wrap);

    const setActive = (btn) => {
      wrap.querySelectorAll('.spw-color-cell').forEach(el => el.classList.remove('is-active'));
      btn.classList.add('is-active');
      current.textContent = `Seleccionado: ${btn.dataset.hex} · ${btn.dataset.name}`;
    };

    PALETTE.forEach(c => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'spw-color-cell';
      btn.dataset.hex = c.hex;
      btn.dataset.name = c.name;
      btn.title = `${c.name} ${c.hex}`;

      const dot = document.createElement('span');
      dot.className = 'spw-color-dot';
      dot.style.background = c.hex;

      const label = document.createElement('div');
      label.className = 'spw-color-label';
      label.innerHTML = `${c.name}<br>${c.hex}`;

      btn.appendChild(dot);
      btn.appendChild(label);
      btn.addEventListener('click', () => {
        input.value = c.hex;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        setActive(btn);
      });

      // marcar seleccionado si coincide el valor inicial
      if ((input.value || '').toUpperCase() === c.hex.toUpperCase()) {
        setActive(btn);
      }

      wrap.appendChild(btn);
    });
  }

  onReady(function(){
    // Intentamos encontrar el campo de color
    const input =
      document.querySelector('input[name="spw_svg_color"]') ||
      document.getElementById('spw_svg_color');

    if (!input) return; // no está el campo en esta página
    buildPalette(input);
  });
});