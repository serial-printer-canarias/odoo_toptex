/** SPW – Paleta de colores (personalizador) */
odoo.define('serial_printer_custom_wizard.spw_color_palette', [], function () {
  'use strict';

  // ---------- helpers ----------
  function onReady(cb){ if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded', cb, {once:true});} else cb(); }
  const isCart = () => /\/shop\/cart\b/.test(location.pathname);
  const $ = sel => document.querySelector(sel);
  const $$ = sel => Array.from(document.querySelectorAll(sel));

  // Colores: blanco → negro con tonos pastel intercalados
  const PALETTE = [
    {name:'Blanco',        hex:'#FFFFFF'},
    {name:'Crema',         hex:'#FFF2CC'},
    {name:'Arena',         hex:'#F1E5C6'},
    {name:'Melocotón',     hex:'#FFB3A7'},
    {name:'Rosa pastel',   hex:'#F7D6E6'},
    {name:'Lavanda',       hex:'#E6E1FA'},
    {name:'Lila',          hex:'#D7C4F3'},
    {name:'Azul cielo',    hex:'#93C5FD'},
    {name:'Azul medio',    hex:'#60A5FA'},
    {name:'Turquesa',      hex:'#7DD3FC'},
    {name:'Cian',          hex:'#20B3EE'},
    {name:'Menta',         hex:'#A7F3D0'},
    {name:'Verde pastel',  hex:'#C7FCEC'},
    {name:'Verde medio',   hex:'#34D399'},
    {name:'Lima',          hex:'#A3E635'},
    {name:'Mostaza',       hex:'#EAB308'},
    {name:'Naranja',       hex:'#FB923C'},
    {name:'Coral',         hex:'#FB7185'},
    {name:'Rojo',          hex:'#EF4444'},
    {name:'Granate',       hex:'#991B1B'},
    {name:'Marrón',        hex:'#8B5E34'},
    {name:'Topo',          hex:'#8A8A9E'},
    {name:'Gris claro',    hex:'#E5E7EB'},
    {name:'Gris medio',    hex:'#9CA3AF'},
    {name:'Gris oscuro',   hex:'#4B5563'},
    {name:'Azul marino',   hex:'#1E3A8A'},
    {name:'Petróleo',      hex:'#0E7490'},
    {name:'Verde bosque',  hex:'#166534'},
    {name:'Vino',          hex:'#7F1D1D'},
    {name:'Negro',         hex:'#000000'},
  ];

  // CSS inline (no SCSS, no compilación)
  const CSS = `
  .spw-palette-wrap{margin-top:12px}
  .spw-palette{
    display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
    gap:10px;max-height:360px;overflow:auto;padding:8px;
    border:1px solid #eee;border-radius:12px;background:#fff;
  }
  @media(min-width:900px){ .spw-palette{grid-template-columns:repeat(3,minmax(0,1fr));} }
  .spw-swatch{
    display:flex;align-items:center;gap:10px;
    padding:8px 10px;border-radius:10px;border:1px solid #e5e7eb;
    background:#fff;cursor:pointer;transition:box-shadow .15s,transform .03s;
  }
  .spw-swatch:active{ transform:scale(.99) }
  .spw-swatch[aria-selected="true"]{
    box-shadow:0 0 0 2px #111 inset, 0 0 0 3px rgba(17,17,17,.06);
  }
  .spw-dot{width:18px;height:18px;border-radius:9999px;border:1px solid rgba(0,0,0,.18);flex:0 0 18px}
  .spw-meta{line-height:1}
  .spw-meta b{display:block;font-size:.9rem}
  .spw-meta small{display:block;font-size:.75rem;color:#555}
  /* Ocultar selección de colores antigua SOLO dentro del contenedor nuevo */
  .spw-palette-wrap .o_wsale_product_configurator_variants,
  .spw-palette-wrap .js_add_cart_variants,
  .spw-palette-wrap .product_custom_attribute{ display:none !important; }
  `;

  function injectCSS(){
    if($('#spwPaletteCSS')) return;
    const s=document.createElement('style');
    s.id='spwPaletteCSS';
    s.textContent=CSS;
    document.head.appendChild(s);
  }

  function findCustomizerForm(){
    // Buscamos un formulario del personalizador (anclas típicas que ya tienes)
    return $('#spw_customizer form') ||
           $('form[action*="/spw/"]') ||
           $('form.o_wsale_product_configurator') ||
           document.querySelector('form');
  }

  function ensureHiddenInput(form){
    // Campo donde guardamos el HEX elegido (lo usas ya en tu flujo)
    let inp=form.querySelector('input[name="spw_svg_color"]');
    if(!inp){
      inp=document.createElement('input');
      inp.type='hidden';
      inp.name='spw_svg_color';
      form.appendChild(inp);
    }
    // Campo opcional para el nombre (por si luego quieres mostrarlo en carrito)
    let nameInp=form.querySelector('input[name="spw_svg_color_name"]');
    if(!nameInp){
      nameInp=document.createElement('input');
      nameInp.type='hidden';
      nameInp.name='spw_svg_color_name';
      form.appendChild(nameInp);
    }
    return {hexInp: inp, nameInp};
  }

  function renderPalette(anchor, form){
    if($('#spwPaletteBox')) return; // ya pintado

    const wrap=document.createElement('div');
    wrap.className='spw-palette-wrap';
    wrap.id='spwPaletteBox';

    const grid=document.createElement('div');
    grid.className='spw-palette';
    wrap.appendChild(grid);

    const {hexInp, nameInp}=ensureHiddenInput(form);

    // valor actual (si recargas)
    const current=(hexInp.value||'').toUpperCase();

    PALETTE.forEach(({name,hex})=>{
      const btn=document.createElement('button');
      btn.type='button';
      btn.className='spw-swatch';
      btn.setAttribute('role','option');
      btn.setAttribute('aria-label', `${name} ${hex}`);
      btn.dataset.hex=hex;
      btn.dataset.name=name;

      if(current && current===hex.toUpperCase()){
        btn.setAttribute('aria-selected','true');
      }

      btn.innerHTML=`
        <span class="spw-dot" style="background:${hex}"></span>
        <span class="spw-meta"><b>${name}</b><small>${hex}</small></span>
      `;

      btn.addEventListener('click',()=>{
        // marcar selección
        $$('#spwPaletteBox .spw-swatch[aria-selected="true"]').forEach(b=>b.removeAttribute('aria-selected'));
        btn.setAttribute('aria-selected','true');

        // setear inputs ocultos
        hexInp.value=hex;
        nameInp.value=name;

        // dispara evento por si tu JS del personalizador escucha cambios
        hexInp.dispatchEvent(new Event('change', {bubbles:true}));
      });

      grid.appendChild(btn);
    });

    anchor.parentNode.insertBefore(wrap, anchor.nextSibling);
  }

  function boot(){
    if(isCart()) return; // nunca en carrito

    // ¿Estamos en el personalizador? Señal mínima: input de color o ancla conocida
    const form = findCustomizerForm();
    if(!form) return;

    injectCSS();

    // Punto de inserción: si tienes un ancla/fieldset para color, úsalo; si no, va al final del form.
    const anchor =
      $('#spw_color_palette_anchor') ||
      form.querySelector('[name="spw_svg_color"]')?.closest('div') ||
      form;

    renderPalette(anchor, form);
  }

  onReady(boot);
});