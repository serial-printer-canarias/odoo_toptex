/** SPW – Color palette (no tocar cart; sólo en customizer) */
odoo.define('serial_printer_custom_wizard.spw_color_palette', [], function () {
  'use strict';

  function onReady(cb){ document.readyState==='loading'
    ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }

  // paleta: blanco → negros con pasteles y medios
  const PALETTE = [
    {n:'Blanco',h:'#FFFFFF'},{n:'Crema',h:'#FFF2CC'},{n:'Perla',h:'#F5F5F5'},
    {n:'Arena',h:'#F6E3C5'},{n:'Melocotón',h:'#FFB6A3'},{n:'Rosa pastel',h:'#F7A8D0'},
    {n:'Lavanda',h:'#E6E0FA'},{n:'Lila',h:'#D7C4F3'},{n:'Malva',h:'#BFA7F0'},
    {n:'Azul cielo',h:'#93C5FD'},{n:'Azul medio',h:'#60A5FA'},{n:'Azul marino',h:'#1E3A8A'},
    {n:'Cian',h:'#22D3EE'},{n:'Turquesa',h:'#7DD3FC'},{n:'Menta',h:'#A7F3D0'},
    {n:'Verde pastel',h:'#C7F2CF'},{n:'Verde medio',h:'#34D399'},{n:'Verde oscuro',h:'#166534'},
    {n:'Lima',h:'#A3E635'},{n:'Mostaza',h:'#EAB308'},{n:'Naranja',h:'#FB923C'},
    {n:'Coral',h:'#FB7185'},{n:'Rojo',h:'#EF4444'},{n:'Granate',h:'#991B1B'},
    {n:'Topo',h:'#A8A29E'},{n:'Marrón',h:'#8B5E34'},
    {n:'Gris claro',h:'#E5E7EB'},{n:'Gris medio',h:'#9CA3AF'},{n:'Gris oscuro',h:'#4B5563'},
    {n:'Antracita',h:'#2E2E2E'},{n:'Negro',h:'#000000'},
  ];

  // dónde escribir el color elegido (no cambiamos tu flujo)
  const COLOR_INPUTS = [
    'input[name="spw_svg_color"]',
    '#spw_svg_color',
    'input[name="svg_color"]',
  ];

  function getColorInput(){
    for (const sel of COLOR_INPUTS){
      const el = document.querySelector(sel);
      if (el) return el;
    }
    return null;
  }

  function setColor(hex){
    const input = getColorInput();
    if (input){
      input.value = hex;
      input.dispatchEvent(new Event('input', {bubbles:true}));
      input.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }

  // elimina la UI antigua si existe (no rompe si no está)
  function removeLegacy(){
    const suspects = [
      '.spw-quick-colors', '.spw-color-old', '.spw-dot-row',
      '.spw-color-pills-legacy', '.spw-legacy-swatches'
    ];
    suspects.forEach(s => document.querySelectorAll(s).forEach(n => n.remove()));
  }

  function mountPalette(mount){
    removeLegacy();

    // evita doble render
    if (mount.querySelector('.spw-color-grid')) return;

    const wrap = document.createElement('div');
    wrap.className = 'spw-color-grid';

    PALETTE.forEach(({n,h})=>{
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'spw-chip';
      btn.setAttribute('data-hex', h);

      btn.innerHTML = `
        <span class="swatch" style="background:${h}"></span>
        <span class="labels">
          <span class="name">${n}</span>
          <span class="hex">${h}</span>
        </span>
      `;

      btn.addEventListener('click', ()=>{
        // marca selección visual
        wrap.querySelectorAll('.spw-chip.is-active').forEach(b=>b.classList.remove('is-active'));
        btn.classList.add('is-active');
        setColor(h);
      });

      wrap.appendChild(btn);
    });

    mount.appendChild(wrap);
  }

  function boot(){
    // 1) nunca en el carrito
    if (document.querySelector('#o_cart')) return;

    // 2) sólo si hay contenedor del customizer
    const mount = document.querySelector('#spw-color-palette, #spw_color_palette');
    if (!mount) return;

    mount.classList.add('spw-color-palette');
    mountPalette(mount);
  }

  onReady(boot);
});