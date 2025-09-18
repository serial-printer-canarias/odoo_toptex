/** Odoo 18 — Matriz Color x Talla con “sonda” de carga (sin dependencias AMD) */
odoo.define('serial_printer_web_custom.product_matrix', [], function (require) {
    'use strict';

    (function () {
        // ---- SONDA: verifica que el asset se cargó
        console.log('[SP][matrix] asset JS cargado');
        window.__SP_MATRIX_PROBE__ = 'ok';
        if (!document.getElementById('sp-probe')) {
            const p = document.createElement('div');
            p.id = 'sp-probe';
            p.className = 'sp-probe';
            p.textContent = 'SP matrix asset cargado';
            document.body.appendChild(p);
            setTimeout(() => p.remove(), 1500);
        }

        // ---- Helpers
        function onReady(fn) {
            if (document.readyState !== 'loading') fn();
            else document.addEventListener('DOMContentLoaded', fn);
        }

        function getRoot() {
            // varios posibles contenedores según plantilla
            return document.querySelector('#product_details, .o_wsale_product_page, .oe_website_sale');
        }

        function getAttributeBlocks(scope) {
            const rows = Array.from(scope.querySelectorAll(
                '.o_wsale_product_configurator_row, .js_attribute, .o_variant_attribute, .o_attribute_value_list'
            ));
            const blocks = [];
            for (const row of rows) {
                const labelEl = row.querySelector('.o_variant_label, .attribute_name, .o_wsale_product_configurator_label');
                const name = (
                    row.getAttribute('data-attribute-name') ||
                    (labelEl && labelEl.textContent) || ''
                ).trim().toLowerCase();
                if (!name) continue;

                const radios = Array.from(row.querySelectorAll('input[type="radio"]'));
                if (!radios.length) continue;

                const options = radios.map((inp) => {
                    const id = parseInt(
                        inp.value || inp.dataset.valueId || inp.dataset.variantId || inp.dataset.attributeValueId || '0',
                        10
                    );
                    const lbl = row.querySelector(`label[for="${inp.id}"]`);
                    const txt = ((lbl && lbl.textContent) || inp.getAttribute('data-value_name') || '').trim();
                    return id && txt ? { id, text: txt, input: inp } : null;
                }).filter(Boolean);

                if (options.length) blocks.push({ name, options, el: row });
            }
            return blocks;
        }

        const isColor = (n) => /(color|colour|colou?r|colorway)/i.test(n);
        const isSize  = (n) => /(size|talla|taille|uk|eu|us)/i.test(n);

        function sizeKey(txt) {
            const t = txt.trim().toUpperCase();
            const table = { 'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6, '3XL': 7, '4XL': 8, '5XL': 9 };
            if (t in table) return table[t];
            const m = t.match(/\d+/);
            if (m) return 100 + parseInt(m[0], 10);
            return 200 + t.charCodeAt(0);
        }

        function renderGrid({ color, size }) {
            const container = document.createElement('div');
            container.id = 'sp-matrix';

            const table = document.createElement('table');
            table.className = 'sp-matrix__table';

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
                const cells = Array.from(table.querySelectorAll('td.sp-cell'));
                for (const cell of cells) {
                    const qty = parseInt(cell.querySelector('.sp-qty').value || '0', 10);
                    if (!qty) continue;

                    const colorRadio = color.options.find(o => String(o.id) === cell.dataset.colorId)?.input;
                    const sizeRadio  = size.options.find(o => String(o.id) === cell.dataset.sizeId )?.input;
                    if (colorRadio) colorRadio.click();
                    if (sizeRadio)  sizeRadio.click();

                    const mainQty = document.querySelector('.o_wsale_product_page input[name="add_qty"]');
                    if (mainQty) mainQty.value = String(qty);

                    const addBtn = document.querySelector('.o_wsale_product_page .o_add_to_cart, .o_wsale_product_page [data-add-to-cart]');
                    if (addBtn) addBtn.click();
                }
            });

            container.appendChild(table);
            container.appendChild(btn);
            return container;
        }

        function ensureMatrix() {
            const root = getRoot();
            if (!root) { console.warn('[SP][matrix] root no encontrado'); return; }

            if (root.querySelector('#sp-matrix')) return;

            const attrScope = root.querySelector('.js_product .js_attributes, .js_attributes') || root;
            if (!attrScope) { console.warn('[SP][matrix] js_attributes no encontrado'); return; }

            const blocks = getAttributeBlocks(attrScope);
            if (!blocks.length) { console.warn('[SP][matrix] sin bloques de atributos'); return; }

            const color = blocks.find(b => isColor(b.name));
            const size  = blocks.find(b => isSize(b.name));
            if (!color || !size) {
                console.warn('[SP][matrix] no se detectó Color/Talla', blocks.map(b => b.name));
                return;
            }

            const matrix = renderGrid({ color, size });

            const anchor = root.querySelector('.js_attributes, .o_wsale_product_configurator, .product_price')
                        || root;
            anchor.parentNode.insertBefore(matrix, anchor.nextSibling);

            root.classList.add('sp-matrix-active');
            console.log('[SP][matrix] creado con éxito — Color:', color.name, 'Talla:', size.name);
        }

        onReady(ensureMatrix);
        const obs = new MutationObserver(() => ensureMatrix());
        obs.observe(document.body, { childList: true, subtree: true });
    })();
});