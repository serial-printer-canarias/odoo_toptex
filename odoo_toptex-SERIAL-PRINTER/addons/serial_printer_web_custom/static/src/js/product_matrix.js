/** Odoo 18 — Matriz Color x Talla (sin dependencias AMD) */
odoo.define('serial_printer_web_custom.product_matrix', [], function (require) {
    'use strict';

    // Utilidad: ejecutar cuando el DOM esté listo
    function onReady(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    // Detecta bloques de atributos (Color, Talla, etc.)
    function getAttributeBlocks(scope) {
        // Odoo 18 tiene diferentes clases/plantillas; cubrimos varias
        const rows = Array.from(scope.querySelectorAll(
            '.o_wsale_product_configurator_row, .js_attribute, .o_variant_attribute'
        ));

        const blocks = [];
        for (const row of rows) {
            const labelEl = row.querySelector('.o_variant_label, .attribute_name, .o_wsale_product_configurator_label');
            const name = (
                row.getAttribute('data-attribute-name') ||
                (labelEl && labelEl.textContent) ||
                ''
            ).trim().toLowerCase();
            if (!name) continue;

            const radios = Array.from(row.querySelectorAll('input[type="radio"]'));
            if (!radios.length) continue;

            const options = radios.map((inp) => {
                // Odoo cambia los data-* según vista; usamos varias opciones
                const id = parseInt(
                    inp.value || inp.dataset.valueId || inp.dataset.variantId || inp.dataset.attributeValueId || '0',
                    10
                );
                const lbl = row.querySelector(`label[for="${inp.id}"]`);
                const txt = (
                    (lbl && lbl.textContent) ||
                    inp.getAttribute('data-value_name') ||
                    ''
                ).trim();
                return id && txt ? { id, text: txt, input: inp } : null;
            }).filter(Boolean);

            if (options.length) {
                blocks.push({ name, options, el: row });
            }
        }
        return blocks;
    }

    // Heurística para identificar color/talla
    const isColor = (n) => /(color|colour|colou?r|colorway)/i.test(n);
    const isSize  = (n) => /(size|talla|taille|uk|eu|us)/i.test(n);

    // Ordena tallas de forma natural (10 < 12 < 14, XS < S < M…)
    function sizeKey(txt) {
        const t = txt.trim().toUpperCase();
        // Letras comunes primero
        const table = { 'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '3XL': 7, '4XL': 8, '5XL': 9 };
        if (t in table) return table[t];
        // Captura números (UK/EU)
        const m = t.match(/\d+/);
        if (m) return 100 + parseInt(m[0], 10);
        // Fallback alfabético
        return 200 + t.charCodeAt(0);
    }

    function renderGrid({ color, size }) {
        // contenedor final
        const container = document.createElement('div');
        container.id = 'sp-matrix';

        // tabla
        const table = document.createElement('table');
        table.className = 'sp-matrix__table';

        // thead
        const thead = document.createElement('thead');
        const trh = document.createElement('tr');
        const th0 = document.createElement('th');
        th0.className = 'sp-sticky-left';
        th0.textContent = ''; // cabecera hueca (columna colores)
        trh.appendChild(th0);

        size.options.sort((a, b) => sizeKey(a.text) - sizeKey(b.text));
        for (const s of size.options) {
            const th = document.createElement('th');
            th.textContent = s.text;
            trh.appendChild(th);
        }
        thead.appendChild(trh);
        table.appendChild(thead);

        // tbody
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
                td.innerHTML = `
                    <input class="sp-qty" type="number" min="0" step="1" value="0">
                    <div class="sp-meta"></div>
                `;
                td.dataset.colorId = String(c.id);
                td.dataset.sizeId  = String(s.id);
                tbody.appendChild(tr);
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }
        table.appendChild(tbody);

        // botón añadir
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-primary mt-2';
        btn.textContent = 'Añadir selección';
        btn.addEventListener('click', async () => {
            // Recorremos celdas y usamos el radio original de Odoo para setear variante
            const cells = Array.from(table.querySelectorAll('td.sp-cell'));
            const tasks = [];
            cells.forEach((cell) => {
                const qty = parseInt(cell.querySelector('.sp-qty').value || '0', 10);
                if (qty > 0) {
                    // Marca color y talla en los radios originales
                    const colorRadio = color.options.find(o => String(o.id) === cell.dataset.colorId)?.input;
                    const sizeRadio  = size.options.find(o => String(o.id) === cell.dataset.sizeId)?.input;
                    if (colorRadio) colorRadio.click();
                    if (sizeRadio)  sizeRadio.click();
                    // dispara el Add to cart nativo (si existiera hook custom, cámbialo aquí)
                    const addBtn = document.querySelector('.o_wsale_product_page .o_add_to_cart, .o_wsale_product_page [data-add-to-cart]');
                    if (addBtn) {
                        // setea qty del control principal
                        const mainQty = document.querySelector('.o_wsale_product_page input[name="add_qty"]');
                        if (mainQty) mainQty.value = String(qty);
                        addBtn.click();
                    }
                }
            });
        });

        container.appendChild(table);
        container.appendChild(btn);
        return container;
    }

    function ensureMatrix() {
        const root = document.querySelector('.o_wsale_product_page');
        if (!root) return;

        // Ya creada
        if (root.querySelector('#sp-matrix')) return;

        const attrScope = root.querySelector('.js_product .js_attributes') || root;
        const blocks = getAttributeBlocks(attrScope);
        if (!blocks.length) return;

        const color = blocks.find(b => isColor(b.name));
        const size  = blocks.find(b => isSize(b.name));
        if (!color || !size) return;

        // Renderiza
        const matrix = renderGrid({ color, size });

        const afterEl = root.querySelector('.product_price, .o_wsale_product_configurator, .js_attributes') || root;
        afterEl.parentNode.insertBefore(matrix, afterEl.nextSibling);

        // Oculta radios originales sólo si hay matriz
        root.classList.add('sp-matrix-active');

        console.log('[SP] product_matrix listo — Color:', color.name, 'Talla:', size.name);
    }

    onReady(ensureMatrix);

    // Reacciona a cambios dinámicos (algunas vistas cambian al seleccionar atributo)
    const obs = new MutationObserver(() => ensureMatrix());
    obs.observe(document.body, { childList: true, subtree: true });

});