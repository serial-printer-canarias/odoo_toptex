/** SPW – Paleta de colores (píldora + nombre + código) */
odoo.define('serial_printer_custom_wizard.spw_color_palette', [], function () {
  'use strict';

  // ---------- helpers ----------
  function onReady(cb){ document.readyState === 'loading' ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }
  const selInput = 'input[name="spw_svg_color"], #spw_svg_color, input[name="color_svg"], input[name="spw_color"]';

  // 30 colores: blanco → negros con pasteles
  const COLORS = [
    {name:'Blanco',          hex:'#FFFFFF'},
    {name:'Marfil',          hex:'#F7F2E7'},
    {name:'Beige pastel',    hex:'#F4E3C1'},
    {name:'Arena',           hex:'#E8D3B0'},
    {name:'Melocotón suave', hex:'#FFD8C2'},
    {name:'Rosa pastel',     hex:'#F7C6CC'},
    {name:'Coral claro',     hex:'#FFB5A7'},
    {name:'Salmón',          hex:'#FFA07A'},
    {name:'Lavanda',         hex:'#E6E0FA'},
    {name:'Lila',            hex:'#CDB4DB'},
    {name:'Malva',           hex:'#B9A3E3'},
    {name:'Violeta suave',   hex:'#A78BFA'},
    {name:'Azul bebé',       hex:'#BDE0FE'},
    {name:'Azul cielo',      hex:'#93C5FD'},
    {name:'Azul medio',      hex:'#60A5FA'},
    {name:'Turquesa',        hex:'#7DD3FC'},
    {name:'Cian',            hex:'#22D3EE'},
    {name:'Menta',           hex:'#A7F3D0'},
    {name:'Verde pastel',    hex:'#C7EFCF'},
    {name:'Verde medio',     hex:'#34D399'},
    {name:'Lima',            hex:'#BBF7D0'},
    {name:'Amarillo pastel', hex:'#FFF2B2'},
    {name:'Mostaza suave',   hex:'#FACC15'},
    {name:'Naranja pastel',  hex:'#FED7AA'},
    {name:'Rojo suave',      hex:'#FCA5A5'},
    {name:'Granate',         hex:'#DC2626'},
    {name:'Gris claro',      hex:'#E5E7EB'},
    {name:'Gris medio',      hex:'#9CA3AF'},
    {name:'Gris oscuro',     hex:'#4B5563'},
    {name:'Negro',           hex:'#000000'},
  ];

  function ensureStyles() {
    if (document.getElementById('spw-color-palette-css')) return;
    const css = `
    .spw-color-palette{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-top:10px}
    @media (max-width:640px){.spw-color-palette{grid-template-columns:repeat(2,minmax(0,1fr));}}
    .spw-color-item{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #e5e7eb;border-radius:12px;background:#fff;cursor:pointer;user-select:none;box-shadow:0 1px 1px rgba(0,0,0,.03)}
    .spw-color-item:focus{outline:2px solid #6366f1;outline-offset:2px}
    .spw-color-item.selected{border-color:#c7d2fe;box-shadow:0 0 0 2px #e0e7ff inset}
    .spw-dot{width:22px;height:22px;border-radius:9999px;border:1px solid rgba(0,0,0,.12);flex:0 0 22px}
    .spw-labels{display:flex;flex-direction:column;line-height:1.1}
    .spw-name{font-size:12.5px;color:#111827}
    .spw-code{font-size:11.5px;color:#6b7280}
    `;
    const tag = document.createElement('style');
    tag.id = 'spw-color-palette-css';
    tag.appendChild(document.createTextNode(css));
    document.head.appendChild(tag);
  }

  function selectColor(hex, input, container, itemEl) {
    if (input) {
      input.value = hex;
      input.dispatchEvent(new Event('input', {bubbles:true}));
      input.dispatchEvent(new Event('change', {bubbles:true}));
    }
    container.querySelectorAll('.spw-color-item.selected').forEach(el=>el.classList.remove('selected'));
    itemEl?.classList.add('selected');
  }

  function renderPaletteFor(input) {
    if (!input || input.dataset.spwPaletteMounted) return;
    input.dataset.spwPaletteMounted = '1';

    ensureStyles();

    // contenedor
    const wrap = document.createElement('div');
    wrap.className = 'spw-color-palette';

    // items
    COLORS.forEach(c => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'spw-color-item';
      btn.setAttribute('aria-label', `${c.name} ${c.hex}`);
      btn.innerHTML = `
        <span class="spw-dot" style="background:${c.hex}"></span>
        <span class="spw-labels">
          <span class="spw-name">${c.name}</span>
          <span class="spw-code">${c.hex}</span>
        </span>
      `;
      btn.addEventListener('click', () => selectColor(c.hex, input, wrap, btn));
      wrap.appendChild(btn);
    });

    // insertar bajo el input (si hay label/field, queda pegado)
    input.insertAdjacentElement('afterend', wrap);

    // preselección si el input ya tenía valor
    const current = (input.value || '').trim().toUpperCase();
    if (current) {
      const item = [...wrap.querySelectorAll('.spw-color-item')]
        .find(el => el.querySelector('.spw-code').textContent.toUpperCase() === current);
      if (item) item.classList.add('selected');
    }
  }

  function boot() {
    const input = document.querySelector(selInput) ||
      [...document.querySelectorAll('label')]
        .find(l => /color\s*svg/i.test(l.textContent || ''))?.htmlFor &&
      document.getElementById([...document.querySelectorAll('label')]
        .find(l => /color\s*svg/i.test(l.textContent || ''))?.htmlFor);

    if (input) renderPaletteFor(input);

    // por si el DOM cambia (SPA)
    const root = document.body;
    new MutationObserver(ms => {
      for (const m of ms) {
        if (m.addedNodes) {
          const i = (m.target && m.target.matches && m.target.matches(selInput)) ? m.target :
                    (m.target && m.target.querySelector && m.target.querySelector(selInput));
          if (i) renderPaletteFor(i);
        }
      }
    }).observe(root, {subtree:true, childList:true});
  }

  onReady(boot);
});