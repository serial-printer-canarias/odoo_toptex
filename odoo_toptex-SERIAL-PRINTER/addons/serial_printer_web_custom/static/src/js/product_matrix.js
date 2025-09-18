/** Odoo 18 — Matriz Color x Talla (robusto) */
odoo.define('serial_printer_web_custom.product_matrix', [], function (require) {
  'use strict';

  (function () {
    // ---- Sonda visual para confirmar que el JS se cargó
    try {
      if (!document.getElementById('sp-probe')) {
        const p = document.createElement('div');
        p.id = 'sp-probe';
        p.style.cssText =
          'position:fixed;right:10px;bottom:10px;z-index:99999;background:#16a34a;color:#fff;padding:.25rem .5rem;border-radius:.4rem;font:12px/1.2 system-ui';
        p.textContent = 'SP matrix JS';
        document.body.appendChild(p);
        setTimeout(() => p.remove(), 1200);
      }
      console.log('[SP][matrix] JS cargado');
    } catch (_) {}

    // ---- Helpers
    const onReady = (fn) => {
      if (document.readyState !== 'loading') fn();
      else document.addEventListener('DOMContentLoaded', fn);
    };
    const qsa = (root, sel) => Array.from(root.querySelectorAll(sel));

    function getRoot() {
      return (
        document.querySelector('#product_details') ||
        document.querySelector('.o_wsale_product_page') ||
        document.querySelector('.oe_website_sale') ||
        document.querySelector('main') ||
        document.body
      );
    }

    // Orden natural de tallas
    function sizeKey(txt) {
      const t = (txt || '').trim().toUpperCase();
      const map = { 'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '3XL': 7, '4XL': 8, '5XL': 9 };
      if (t in map) return map[t];
      // 8 UK / 40 EU / 30 US -> tomar número
      const m = t.match(/\d+/);
      if (m) return 100 + parseInt(m[0], 10);
      return 200 + t.charCodeAt(0);
    }

    const isColorName = (n) => /(color|colour|colou?r|colorway)/i.test(n || '');
    const isSizeName  = (n) => /(size|talla|taille|uk|eu|us|it|fr)/i.test(n || '');
    const looksLikeSize = (v) =>
      /^(XXS|XS|S|M|L|XL|XXL|[345]XL|\d+(\s?(UK|EU|US|IT|FR))?)$/i.test((v || '').trim());

    // ---- Lee grupos de atributos Color/Talla de la página
    function getAttributeGroups(scope) {
      // 1) localizar contenedores típicos de atributos
      let containers = qsa(
        scope,
        [
          '[data-attribute_name]',
          '[data-attribute-name]',
          '.js_attribute',
          '.o_wsale_product_configurator_row',
          '.o_product_variant_attribute',
        ].join(',')
      );

      // 2) fallback: si no hay contenedores, agrupar por "name" de radios
      if (!containers.length) {
        const radios = qsa(scope, 'input[type="radio"]');
        const byName = new Map();
        for (const r of radios) {
          if (!byName.has(r.name)) byName.set(r.name, []);
          byName.get(r.name).push(r);
        }
        containers = Array.from(byName.values())
          .filter((arr) => arr.length >= 2)
          .map((arr) => arr[0].closest('div') || scope);
      }

      // 3) construir grupos { name, options:[{id,text,input}], el }
      const groups = [];
      for (const el of containers) {
        const name =
          el.getAttribute?.('data-attribute_name') ||
          el.getAttribute?.('data-attribute-name') ||
          (el.querySelector('.o_variant_label, .attribute_name, legend') || {}).textContent ||
          '';

        const radios = qsa(el, 'input[type="radio"]');
        const options = radios
          .map((inp) => {
            // id del valor
            const id = parseInt(
              inp.value ||
                inp.getAttribute('data-value_id') ||
                inp.getAttribute('data-value-id') ||
                inp.getAttribute('data-attribute_value_id') ||
                inp.getAttribute('data-attribute-value-id') ||
                '0',
              10
            );
            // texto visible del valor
            const lbl =
              (inp.id && el.querySelector(`label[for="${inp.id}"]`)) ||
              inp.closest('label') ||
              inp.parentElement?.querySelector?.('.badge, .name, .variant-name');
            const text = (
              (lbl && lbl.textContent) ||
              inp.getAttribute('data-value_name') ||
              inp.getAttribute('data-value-name') ||
              ''
            ).trim();

            return id && text ? { id, text, input: inp } : null;
          })
          .filter(Boolean);

        if (options.length) groups.push({ name: (name || '').trim(), options, el });
      }

      console.log(
        '[SP][matrix] grupos detectados:',
        groups.map((g) => ({ name: g.name, options: g.options.map((o) => o.text) }))
      );
      return groups;
    }

    // ---- Render de la tabla
    function renderGrid(color, size) {
      const wrap = document.createElement('div');
      wrap.id = 'sp-matrix';

      const table = document.createElement('table');
      table.className = 'sp-matrix__table';

      // cabecera
      const thead = document.createElement('thead');
      const trh = document.createElement('tr');
      const th0 = document.createElement('th');
      th0.className = 'sp-sticky-left';
      trh.appendChild(th0);

      size.options.sort((a, b) => sizeKey(a.text) - sizeKey(b.text));
      for (const s of size.options) {
        const th = document.createElement('th');
        th.textContent = s.text;
        trh.appendChild(th);
      }
      thead.appendChild(trh);
      table.appendChild(thead);

      // cuerpo
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

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-primary mt-2';
      btn.textContent = 'Añadir selección';
      btn.addEventListener('click', () => {
        const cells = qsa(table, 'td.sp-cell');
        for (const cell of cells) {
          const qty = parseInt(cell.querySelector('.sp-qty').value || '0', 10);
          if (!qty) continue;

          const c = color.options.find((o) => String(o.id) === cell.dataset.colorId);
          const s = size.options.find((o) => String(o.id) === cell.dataset.sizeId);
          c?.input?.click();
          s?.input?.click();

          const qtyInput = document.querySelector('.o_wsale_product_page input[name="add_qty"]');
          if (qtyInput) qtyInput.value = String(qty);

          const addBtn = document.querySelector(
            '.o_wsale_product_page .o_add_to_cart, .o_wsale_product_page [data-add-to-cart]'
          );
          addBtn?.click();
        }
      });

      wrap.appendChild(table);
      wrap.appendChild(btn);
      return wrap;
    }

    // ---- Punto de entrada
    function ensureMatrix() {
      const root = getRoot();
      if (!root) return false;
      if (root.querySelector('#sp-matrix')) return true;

      const scope =
        root.querySelector('.js_product .js_attributes') ||
        root.querySelector('.js_attributes') ||
        root.querySelector('.o_wsale_product_configurator') ||
        root;

      const groups = getAttributeGroups(scope);
      if (!groups.length) return false;

      // 1º intentar por nombre
      let color = groups.find((g) => isColorName(g.name));
      let size  = groups.find((g) => isSizeName(g.name));

      // 2º heurística por contenido
      if (!color || !size) {
        const score = (g) => g.options.reduce((a, o) => a + (looksLikeSize(o.text) ? 1 : 0), 0);
        const sorted = [...groups].sort((a, b) => score(b) - score(a));
        if (!size && sorted.length) size = sorted[0];
        if (!color) color = groups.find((g) => g !== size) || groups[0];
        console.warn('[SP][matrix] usando heurística — Color:', color?.name, 'Size:', size?.name);
      }

      if (!color || !size) return false;

      const anchor =
        root.querySelector('.js_attributes') ||
        root.querySelector('.o_wsale_product_configurator') ||
        root.querySelector('.product_price') ||
        root;

      const matrix = renderGrid(color, size);
      anchor.parentNode.insertBefore(matrix, anchor.nextSibling);
      root.classList.add('sp-matrix-active');

      console.log('[SP][matrix] matriz creada ✔', { color: color.name, size: size.name });
      // expón diagnóstico por si hace falta
      window._sp_diag = { groups, color, size };
      return true;
    }

    let tries = 0;
    const tick = () => {
      const ok = ensureMatrix();
      if (ok || tries++ > 50) clearInterval(timer);
    };
    onReady(tick);
    const timer = setInterval(tick, 300);

    // Si la ficha se re-renderiza, volver a intentar
    const mo = new MutationObserver(() => ensureMatrix());
    mo.observe(document.body, { childList: true, subtree: true });
  })();

  return {};
});