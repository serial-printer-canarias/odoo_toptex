/** Odoo 18 – SERIAL PRINTER
 *  Baseline estable: pinta la matriz Color x Talla debajo de los atributos.
 *  No usa dependencias ([]) para evitar errores del loader.
 *  No toca carrito/precio/stock todavía.
 */
odoo.define('serial_printer_web_custom.product_matrix', [], function () {
  'use strict';

  // -------- utilidades ----------
  function onReady(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function alreadyRendered(scope) {
    return !!$('#sp-matrix', scope);
  }

  // Lee filas de atributos (Color/Talla) de forma tolerante al tema
  function readAttributeBlocks(scope) {
    const rows = $$(
      '.js_attributes .o_variant_row, .o_wsale_product_configurator .o_variant_row',
      scope
    );
    const blocks = [];

    rows.forEach((row) => {
      const name = (
        $('.o_variant_label, .o_attribute_label, label', row)?.textContent || ''
      ).trim().toLowerCase();

      const radios = $$('input[type="radio"]', row);
      if (!radios.length) return;

      const options = radios
        .map((inp) => {
          const li = inp.closest('li') || inp.parentElement || row;
          const text =
            ($('label', li)?.textContent ||
              li.textContent ||
              inp.getAttribute('data-value_name') ||
              '').trim();

          // id del valor (varía por tema)
          const id = parseInt(
            inp.dataset.valueId || inp.getAttribute('data-value-id') || inp.value || '0',
            10
          );
          if (!id) return null;

          // intentar miniatura (si existe)
          let img = '';
          const imgEl = $('img', li);
          if (imgEl && imgEl.src) img = imgEl.src;
          return { id, text, img, input: inp };
        })
        .filter(Boolean);

      if (name && options.length) blocks.push({ name, options, row });
    });

    return blocks;
  }

  function pickColorAndSize(blocks) {
    const isColor = (n) => /(color|colour|couleur)/i.test(n);
    const isSize  = (n) => /(talla|size|taille|tamanho|maß)/i.test(n);

    let color = blocks.find((b) => isColor(b.name)) || blocks[0] || null;
    let size  = blocks.find((b) => isSize(b.name))  || blocks[1] || null;

    return { color, size };
  }

  // -------- render matriz ----------
  function renderMatrix(color, size) {
    const wrap  = document.createElement('div');
    wrap.id     = 'sp-matrix';
    wrap.className = 'sp-matrix-active';

    const table = document.createElement('table');
    table.className = 'sp-matrix__table';

    // thead
    const thead = document.createElement('thead');
    const trH = document.createElement('tr');
    const th0 = document.createElement('th');
    th0.className = 'sp-sticky-left';
    th0.textContent = 'Color';
    trH.appendChild(th0);
    size.options.forEach((opt) => {
      const th = document.createElement('th');
      th.textContent = opt.text || '';
      trH.appendChild(th);
    });
    thead.appendChild(trH);
    table.appendChild(thead);

    // tbody
    const tbody = document.createElement('tbody');
    color.options.forEach((c) => {
      const tr = document.createElement('tr');

      // celda fija izquierda (miniatura + nombre)
      const tdLeft = document.createElement('td');
      tdLeft.className = 'sp-sticky-left';
      const info = document.createElement('div');
      info.className = 'sp-color';

      const img = document.createElement('img');
      img.className = 'sp-color__img';
      img.alt = c.text || '';
      img.src = c.img || ($('.product_detail_img img')?.src || '');
      info.appendChild(img);

      const name = document.createElement('span');
      name.textContent = c.text || '';
      info.appendChild(name);

      tdLeft.appendChild(info);
      tr.appendChild(tdLeft);

      // celdas cantidad (baseline: inputs vacíos)
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

  function insertMatrix(container, scope) {
    // la colocamos justo después del bloque de atributos si existe,
    // si no, debajo del configurador, y si no, al final de la ficha
    const anchors = [
      '.js_product .js_attributes',
      '.o_wsale_product_configurator',
      '.o_wsale_product_information',
    ];
    for (const sel of anchors) {
      const el = $(sel, scope);
      if (el) {
        el.insertAdjacentElement('afterend', container);
        return;
      }
    }
    // fallback
    const body = $('.o_wsale_product_page') || scope;
    body.appendChild(container);
  }

  function buildOnce() {
    const page = $('.o_wsale_product_page');
    if (!page || alreadyRendered(page)) return;

    const blocks = readAttributeBlocks(page);
    if (!blocks.length) return;

    const { color, size } = pickColorAndSize(blocks);
    if (!color || !size) return;

    const matrix = renderMatrix(color, size);
    insertMatrix(matrix, page);

    // Si quieres ocultar la UI original, activa esta clase (el SCSS ya tiene la regla comentada)
    // document.body.classList.add('sp-matrix-active');
  }

  // montar al cargar
  onReady(buildOnce);

  // y reintentar si la página cambia dinámicamente
  onReady(() => {
    const page = $('.o_wsale_product_page');
    if (!page) return;
    const mo = new MutationObserver(() => {
      if (!alreadyRendered(page)) buildOnce();
    });
    mo.observe(page, { childList: true, subtree: true });
  });

  return {};
});