/** Odoo 18 – Serial Printer – Product Matrix
 *  Paso actual: colocar la matriz justo debajo de los atributos y
 *  mostrar miniatura por color. Sin tocar carrito/precio/stock.
 */
odoo.define('serial_printer_web_custom.product_matrix', [], function () {
  'use strict';

  // Utilidad: ejecutar cuando el DOM está listo
  function onReady(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  // Lee los bloques de atributos (Color, Talla, …) de forma tolerante a plantilla
  function readAttributeBlocks(scope) {
    const rows = Array.from(
      scope.querySelectorAll('.js_attributes .o_variant_row, .o_wsale_product_configurator .o_variant_row')
    );
    const blocks = [];

    rows.forEach((row) => {
      const name =
        (row.querySelector('.o_variant_label, .o_attribute_label, label')?.textContent || '')
          .trim()
          .toLowerCase();

      const radios = Array.from(row.querySelectorAll('input[type="radio"]'));
      const options = radios
        .map((inp) => {
          const li = inp.closest('li') || inp.parentElement || row;
          // Texto visible del color/talla
          const txt =
            (li.querySelector('label')?.textContent ||
              li.textContent ||
              inp.getAttribute('data-value_name') ||
              '') // algunos temas lo llevan en data-value_name
              .trim();

          // Capturar miniatura si existe
          let img = '';
          const imgEl = li.querySelector('img');
          if (imgEl && imgEl.src) {
            img = imgEl.src;
          } else {
            // algunos temas ponen el color como background-image
            const colorEl =
              li.querySelector('.css_attribute_color, .o_attribute_color, .o_attribute_value_color') ||
              li.querySelector('[style*="background-image"]');
            if (colorEl) {
              const bg = getComputedStyle(colorEl).backgroundImage || '';
              const m = /url\(["']?(.*?)["']?\)/.exec(bg);
              if (m && m[1]) img = m[1];
            }
          }

          const valId = parseInt(inp.dataset.valueId || inp.getAttribute('data-value-id') || '0', 10);
          return valId ? { id: valId, text: txt, input: inp, img } : null;
        })
        .filter(Boolean);

      if (name && options.length) blocks.push({ name, options, row });
    });

    return blocks;
  }

  // Detección de bloques de color y talla (multilenguaje: color/talla/size/…)
  function pickColorAndSize(blocks) {
    const isColor = (n) => /(color|colour|couleur)/i.test(n);
    const isSize = (n) => /(talla|size|taille|tamanho|maß)/i.test(n);

    let color = blocks.find((b) => isColor(b.name));
    let size = blocks.find((b) => isSize(b.name));

    // Si no detecta por nombre, coge los dos primeros por orden
    if (!color && blocks[0]) color = blocks[0];
    if (!size && blocks[1]) size = blocks[1];

    return { color, size };
  }

  // Construye la tabla HTML (sin lógica de carrito aún)
  function renderMatrix(color, size) {
    const wrap = document.createElement('div');
    wrap.id = 'sp-matrix';
    wrap.className = 'sp-matrix-active';

    const table = document.createElement('table');
    table.className = 'sp-matrix__table';

    // CABECERA
    const thead = document.createElement('thead');
    const trH = document.createElement('tr');

    const thColor = document.createElement('th');
    thColor.className = 'sp-sticky-left';
    thColor.textContent = 'Color';
    trH.appendChild(thColor);

    size.options.forEach((opt) => {
      const th = document.createElement('th');
      th.textContent = opt.text || '';
      trH.appendChild(th);
    });

    thead.appendChild(trH);
    table.appendChild(thead);

    // CUERPO
    const tbody = document.createElement('tbody');

    color.options.forEach((c) => {
      const tr = document.createElement('tr');

      // Columna fija izquierda (miniatura + nombre)
      const tdLeft = document.createElement('td');
      tdLeft.className = 'sp-sticky-left';
      const rowInfo = document.createElement('div');
      rowInfo.className = 'sp-color';

      const img = document.createElement('img');
      img.className = 'sp-color__img';
      img.alt = c.text || '';
      img.src = c.img || document.querySelector('.product_detail_img img')?.src || '';
      rowInfo.appendChild(img);

      const nameEl = document.createElement('span');
      nameEl.textContent = c.text || '';
      rowInfo.appendChild(nameEl);

      tdLeft.appendChild(rowInfo);
      tr.appendChild(tdLeft);

      // Celdas de cantidades (de momento inputs vacíos)
      size.options.forEach(() => {
        const td = document.createElement('td');
        td.className = 'sp-cell';
        const input = document.createElement('input');
        input.type = 'number';
        input.min = '0';
        input.step = '1';
        input.value = '';
        input.className = 'sp-qty';
        td.appendChild(input);
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    wrap.appendChild(table);
    return wrap;
  }

  // Inserta la matriz justo DESPUÉS del bloque de atributos (más arriba),
  // con varios “anchors” de respaldo según el tema/plantilla.
  function insertMatrix(container, pageScope) {
    const anchors = [
      '.js_product .js_attributes',          // estándar
      '.o_wsale_product_configurator',       // configurador
      '.o_wsale_product_information',        // algunos temas
      '.o_wsale_product_page',               // fallback (muy genérico)
    ];
    for (const sel of anchors) {
      const el = pageScope.querySelector(sel);
      if (el) {
        el.insertAdjacentElement('afterend', container);
        return true;
      }
    }
    // último recurso: al principio del contenido
    pageScope.prepend(container);
    return true;
  }

  // Evitar renders duplicados
  function alreadyRendered(scope) {
    return !!scope.querySelector('#sp-matrix');
  }

  // Orquestador
  function ensureMatrix() {
    const page = document.querySelector('.o_wsale_product_page');
    if (!page || alreadyRendered(page)) return;

    const blocks = readAttributeBlocks(page);
    if (!blocks.length) return;

    const { color, size } = pickColorAndSize(blocks);
    if (!color || !size) return;

    const matrixEl = renderMatrix(color, size);
    insertMatrix(matrixEl, page);

    // clase en <body> para que el SCSS pueda ocultar radios si se desea
    document.body.classList.add('sp-matrix-active');
  }

  onReady(ensureMatrix);

  // Si algo de la página reemplaza la zona de atributos (por ejemplo al cambiar variante),
  // volvemos a montar la matriz automáticamente.
  const obs = new MutationObserver(() => {
    const page = document.querySelector('.o_wsale_product_page');
    if (page && !alreadyRendered(page)) ensureMatrix();
  });
  onReady(() => {
    const product = document.querySelector('.o_wsale_product_page');
    if (product) obs.observe(product, { childList: true, subtree: true });
  });

  return {};
});