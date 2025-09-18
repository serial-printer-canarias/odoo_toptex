/** Odoo 18 — Matriz Color x Talla (sin dependencias AMD) */
odoo.define('serial_printer_web_custom.product_matrix', [], function (require) {
  'use strict';

  (function () {
    // --- Sonda visual: confirma carga del asset
    try {
      if (!document.getElementById('sp-probe')) {
        const p = document.createElement('div');
        p.id = 'sp-probe';
        p.className = 'sp-probe';
        p.textContent = 'SP matrix asset cargado';
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 1400);
      }
      console.log('[SP][matrix] JS cargado');
    } catch (e) {
      console.warn('[SP][matrix] no se pudo pintar la sonda:', e);
    }

    // --- Helpers
    const onReady = (fn) => {
      if (document.readyState !== 'loading') fn();
      else document.addEventListener('DOMContentLoaded', fn);
    };

    function getRoot() {
      // Distintas plantillas: usa el que exista
      return (
        document.querySelector('#product_details') ||
        document.querySelector('.o_wsale_product_page') ||
        document.querySelector('.oe_website_sale') ||
        document.querySelector('main')
      );
    }

    // Orden “natural” de tallas: XXS < XS < S < M < L < XL < XXL < 3XL < 4XL < 5XL, luego numéricas
    function sizeKey(txt) {
      const t = (txt || '').trim().toUpperCase();
      const map = { 'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '3XL': 7, '4XL': 8, '5XL': 9 };
      if (t in map) return map[t];
      const m = t.match(/\d+/);
      if (m) return 100 + parseInt(m[0], 10);
      return 200 + t.charCodeAt(0);
    }

    const isColorName = (n) => /(color|colour|colou?r|colorway)/i.test(n || '');
    const isSizeName  = (n) => /(size|talla|taille|uk|eu|us)/i.test(n || '');

    /**
     * Agrupa radios por atributo (por el name), toma etiqueta del grupo o del label.
     * Devuelve [{ name, options:[{id,text,input}], el }, ...]
     */
    function getAttributeGroups(scope) {
      const allRadios = Array.from(scope.querySelectorAll('input[type="radio"][name^="attribute"]'));
      if (!allRadios.length) return [];

      const byName = new Map();
      for (const r of allRadios) {
        if (!byName.has(r.name)) byName.set(r.name, []);
        byName.get(r.name).push(r);
      }

      const groups = [];
      for (const [name, radios] of byName.entries()) {
        // Contenedor típico de un atributo
        const groupEl =
          radios[0].closest('.js_attribute') ||
          radios[0].closest('.o_wsale_product_configurator_row') ||
          radios[0].closest('[data-attribute-name]') ||
          radios[0].closest('div');

        const labelEl =
          (groupEl && (groupEl.querySelector('.o_variant_label') || groupEl.querySelector('.attribute_name'))) || null;

        const groupName = (
          (groupEl && groupEl.getAttribute('data-attribute-name')) ||
          (labelEl && labelEl.textContent) ||
          name
        ).trim();

        const options = radios
          .map((inp) => {
            const id = parseInt(
              inp.value || inp.dataset.valueId || inp.dataset.variantId || inp.dataset.attributeValueId || '0',
              10
            );
            const lblByFor = (groupEl && groupEl.querySelector(`label[for="${inp.id}"]`)) || null;
            const txt =
              (lblByFor && lblByFor.textContent) ||
              (inp.closest('label') && inp.closest('label').textContent) ||
              inp.getAttribute('data-value_name') ||
              '';
            const text = (txt || '').trim();
            return id && text ? { id, text, input: inp } : null;
          })
          .filter(Boolean);

        if (options.length) groups.push({ name: groupName, options, el: groupEl });
      }

      // Log de diagnóstico
      console.log('[SP][matrix] grupos detectados:',
        groups.map(g => ({ name: g.name, options: g.options.map(o => o.text) }))
      );
      return groups;
    }

    function renderGrid(color, size) {
      const wrap = document.createElement('div');
      wrap.id = 'sp-matrix';

      const table = document.createElement('table');
      table.className = 'sp-matrix__table';

      // Cabecera
      const thead = document.createElement('thead');
      const trh = document.createElement('tr');
      const th0 = document.createElement('th');
      th0.className = 'sp-sticky-left';
      th0.textContent = '';
      trh.appendChild(th0);

      size.options.sort((a, b) => sizeKey(a.text) - sizeKey(b.text));
      for (const s of size.options) {
        const th = document.createElement('th');
        th.textContent = s.text;
        trh.appendChild(th);
      }
      thead.appendChild(trh);
      table.appendChild(thead);

      // Cuerpo
      const tbody = document.createElement('tbody');
      for (const c of color.options) {
        const tr = document.createElement('tr');

        const tdLeft = document.createElement('td');
        tdLeft.className = 'sp-sticky-left';
        tdLeft.innerHTML = `<div class="sp-color"><div class="sp-color__img"></div><div>${c.text}</div></div>`;
        tr.appendChild(tdLeft);

        for (const s of size.options) {
          const td = document.createElement('td');
          td.className = 'sp-cell';
          td.dataset.colorId = String(c.id);
          td.dataset.sizeId = String(s.id);
          td.innerHTML = `
            <input class="sp-qty" type="number" min="0" step="1" value="0">
            <div class="sp-meta"></div>
          `;
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);

      // Botón de acción
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-primary mt-2';
      btn.textContent = 'Añadir selección';
      btn.addEventListener('click', () => {
        const cells = Array.from(table.querySelectorAll('td.sp-cell'));
        for (const cell of cells) {
          const qty = parseInt(cell.querySelector('.sp-qty').value || '0', 10);
          if (!qty) continue;

          const c = color.options.find(o => String(o.id) === cell.dataset.colorId);
          const s = size.options.find(o => String(o.id) === cell.dataset.sizeId);
          if (c?.input) c.input.click();
          if (s?.input) s.input.click();

          const qtyInput = document.querySelector('.o_wsale_product_page input[name="add_qty"]');
          if (qtyInput) qtyInput.value = String(qty);

          const addBtn = document.querySelector(
            '.o_wsale_product_page .o_add_to_cart, .o_wsale_product_page [data-add-to-cart]'
          );
          if (addBtn) addBtn.click();
        }
      });

      wrap.appendChild(table);
      wrap.appendChild(btn);
      return wrap;
    }

    /** Devuelve true si creó la tabla; false si aún no. */
    function ensureMatrix() {
      const root = getRoot();
      if (!root) { console.warn('[SP][matrix] root no encontrado'); return false; }
      if (root.querySelector('#sp-matrix')) return true;

      // ámbito preferente de atributos
      const scope =
        root.querySelector('.js_product .js_attributes') ||
        root.querySelector('.js_attributes') ||
        root;

      const groups = getAttributeGroups(scope);
      if (!groups.length) { console.warn('[SP][matrix] sin grupos de atributo'); return false; }

      let color = groups.find(g => isColorName(g.name));
      let size  = groups.find(g => isSizeName(g.name));

      // Si no detecta por nombre, usa heurística: 2 grupos => 1º color, 2º talla
      if (!color || !size) {
        if (groups.length >= 2) {
          [color, size] = [groups[0], groups[1]];
          console.warn('[SP][matrix] usando heurística de grupos (no match por nombre):',
            color?.name, size?.name);
        }
      }
      if (!color || !size) { console.warn('[SP][matrix] falta Color o Talla'); return false; }

      // inserta justo debajo del bloque de atributos
      const anchor = root.querySelector('.js_attributes, .o_wsale_product_configurator, .product_price') || root;
      const matrix = renderGrid(color, size);
      anchor.parentNode.insertBefore(matrix, anchor.nextSibling);
      root.classList.add('sp-matrix-active');

      console.log('[SP][matrix] matriz creada ✔ — Color:', color.name, 'Talla:', size.name);
      return true;
    }

    // Reintenta hasta que la DOM de la ficha esté lista (y si se rehace por cambio de variante)
    let tries = 0;
    const tick = () => {
      const done = ensureMatrix();
      if (done || tries++ > 40) clearInterval(timer);
    };
    onReady(tick);
    const timer = setInterval(tick, 300);

    // Si el DOM cambia (owl/website events), vuelve a intentar
    const mo = new MutationObserver(() => ensureMatrix());
    mo.observe(document.body, { childList: true, subtree: true });
  })();

  return {};
});