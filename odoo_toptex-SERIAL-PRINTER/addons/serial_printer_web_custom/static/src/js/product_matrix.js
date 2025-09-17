/** **********************************************************************
 * SERIAL PRINTER - Product Matrix (solo grid, sin dependencias Odoo JS)
 * - Sin require('web.public.widget') ni require('web.ajax')
 * - Construye el grid Color × Talla cuando detecta ambos atributos
 * - Reintenta con MutationObserver si el tema inyecta tarde los atributos
 *********************************************************************** */
odoo.define('serial_printer_web_custom.product_matrix', function () {
  'use strict';

  // Utilidad: ejecutar cuando el DOM está listo
  function onReady(fn) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fn);
    else fn();
  }

  // Buscar bloques de atributos (soporta distintos temas/plantillas)
  function getAttributeBlocks(scope) {
    const $scope = scope || document;
    const blocks = [];

    // (A) Contenedores con data-attribute_name (el más común)
    $scope.querySelectorAll('.js_product .js_attributes [data-attribute_name]').forEach(el => {
      const name = (el.getAttribute('data-attribute_name') || '').trim();
      const options = Array.from(el.querySelectorAll('input[type="radio"]')).map(inp => {
        const id = parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value, 10);
        const lbl = inp.closest('label');
        const text = (lbl ? lbl.textContent : (inp.getAttribute('title') || '')).trim();
        return id ? { id, name: text, input: inp } : null;
      }).filter(Boolean);
      if (name && options.length) blocks.push({ name, options, el });
    });
    if (blocks.length) return blocks;

    // (B) Fallback: label.o_variant_label + radios
    const root = $scope.querySelector('.js_product .js_attributes, .js_product .o_wsale_product_configurator');
    if (root) {
      const groups = {};
      root.querySelectorAll('label.o_variant_label').forEach(lbl => {
        const name = (lbl.textContent || lbl.getAttribute('title') || '').trim();
        const holder = lbl.parentElement;
        const options = Array.from(holder.querySelectorAll('input[type="radio"]')).map(inp => {
          const id = parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value, 10);
          const l = inp.closest('label');
          const text = (l ? l.textContent : (inp.getAttribute('title') || '')).trim();
          return id ? { id, name: text, input: inp } : null;
        }).filter(Boolean);
        if (name && options.length) groups[name] = { name, options, el: holder };
      });
      Object.values(groups).forEach(g => blocks.push(g));
    }
    return blocks;
  }

  // Detectar cuál es Color y cuál Talla; si no puede, usa los dos primeros
  function pickColorAndSize(blocks) {
    const isColor = n => /^(color|colour|couleur)$/i.test((n || '').trim());
    const isSize  = n => /^(talla|size|taille|talle)$/i.test((n || '').trim());
    let color = blocks.find(b => isColor(b.name));
    let size  = blocks.find(b => isSize(b.name));
    const rest = blocks.filter(b => (b.options || []).length);
    if (!color && rest[0]) color = rest[0];
    if (!size  && rest[1]) size  = rest[1];
    return { color, size };
  }

  // Construir HTML del grid
  function renderGrid(colorBlock, sizeBlock) {
    const colors = colorBlock.options;
    const sizes  = sizeBlock.options;

    const table = document.createElement('table');
    table.className = 'sp-matrix__table table table-borderless';

    const thead = document.createElement('thead');
    const htr = document.createElement('tr');
    const corner = document.createElement('th');
    corner.className = 'sp-sticky-left';
    htr.appendChild(corner);
    sizes.forEach(s => {
      const th = document.createElement('th');
      th.innerHTML = `<div class="text-center fw-medium">${_.escape(s.name)}</div>`;
      htr.appendChild(th);
    });
    thead.appendChild(htr);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    colors.forEach(c => {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.className = 'sp-sticky-left';
      th.innerHTML = `
        <div class="sp-color">
          <div class="sp-color__img" style="background:#f5f5f5;"></div>
          <div class="fw-medium">${_.escape(c.name)}</div>
        </div>`;
      tr.appendChild(th);

      sizes.forEach(s => {
        const td = document.createElement('td');
        td.innerHTML = `
          <div class="sp-cell">
            <input class="sp-qty form-control form-control-sm"
                   type="number" min="0" step="1"
                   data-color-id="${c.id}" data-size-id="${s.id}"
                   placeholder="">
            <div class="sp-meta text-muted d-flex justify-content-between">
              <span class="sp-price"></span>
              <span class="sp-stock"></span>
            </div>
          </div>`;
        tr.appendChild(td);
      });

      tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    return table;
  }

  // Montaje del grid (una sola vez)
  function buildMatrixOnce() {
    if (document.getElementById('sp-matrix')) return true;
    const page = document.querySelector('.o_wsale_product_page, .oe_website_sale');
    if (!page) return false;

    const blocks = getAttributeBlocks(page);
    const { color, size } = pickColorAndSize(blocks);
    if (!(color && size)) return false;

    // punto de inserción
    const after = page.querySelector('.js_product .js_attributes:last-of-type') ||
                  page.querySelector('.product_price') ||
                  page.querySelector('.js_product');
    if (!after) return false;

    // contenedor + tabla
    document.body.classList.add('sp-matrix-active');
    const mount = document.createElement('div');
    mount.id = 'sp-matrix';
    mount.className = 'sp-matrix o-pt-3';
    mount.appendChild(renderGrid(color, size));
    after.parentNode.insertBefore(mount, after.nextSibling);

    console.info('[SP] Matrix: construida');
    return true;
  }

  // Observador para páginas que inyectan los atributos tarde
  function ensureMatrix() {
    if (buildMatrixOnce()) return;

    const obs = new MutationObserver(() => {
      if (buildMatrixOnce()) {
        obs.disconnect();
      }
    });
    obs.observe(document.body, { childList: true, subtree: true });
  }

  onReady(ensureMatrix);
});