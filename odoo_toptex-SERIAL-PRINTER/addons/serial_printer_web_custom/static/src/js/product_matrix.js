odoo.define('serial_printer_web_custom.product_matrix', [], function (require) {
    'use strict';

    // Ejecutar cuando el DOM esté listo
    function onReady(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    onReady(function () {
        const page = document.querySelector('.o_wsale_product_page');
        if (!page) return;

        try {
            // Buscar bloques de atributos (Color / Talla)
            const blocks = Array.from(page.querySelectorAll('[data-attribute_name]')).map(el => {
                const name = (el.getAttribute('data-attribute_name') || '').trim().toLowerCase();
                const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
                const options = radios.map(r => {
                    const lbl = r.closest('label') || el.querySelector(`label[for="${r.id}"]`);
                    return {
                        id: r.value || r.dataset.value_id || r.getAttribute('data-value_id') || r.id,
                        text: (lbl ? (lbl.textContent || '').trim() : r.value || '').trim(),
                        input: r,
                    };
                });
                return { name, el, options };
            });

            const isColor = n => /(color|colour|colou?r|colou?r name)/i.test(n);
            const isSize  = n => /(size|talla|taille|maat)/i.test(n);

            const color = blocks.find(b => isColor(b.name)) || blocks[0];
            const size  = blocks.find(b => isSize(b.name))  || blocks[1];
            if (!color || !size) return; // nada que dibujar

            // Construir el grid HTML
            const holder = document.createElement('div');
            holder.className = 'o_sp_matrix';
            const table = document.createElement('table');

            const thead = document.createElement('thead');
            const trh = document.createElement('tr');
            trh.appendChild(document.createElement('th')); // esquina vacía
            size.options.forEach(opt => {
                const th = document.createElement('th');
                th.textContent = opt.text;
                trh.appendChild(th);
            });
            thead.appendChild(trh);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            color.options.forEach(c => {
                const tr = document.createElement('tr');
                const th = document.createElement('th');
                th.textContent = c.text;
                tr.appendChild(th);

                size.options.forEach(s => {
                    const td = document.createElement('td');
                    const inp = document.createElement('input');
                    inp.type = 'number';
                    inp.min = '0';
                    inp.step = '1';
                    inp.className = 'qty';
                    inp.dataset.colorId = c.id;
                    inp.dataset.sizeId = s.id;
                    td.appendChild(inp);
                    tr.appendChild(td);
                });

                tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            holder.appendChild(table);

            // Insertar debajo de los atributos
            const anchor = size.el || page.querySelector('#product_details');
            anchor.parentNode.insertBefore(holder, anchor.nextSibling);

            console.log('[SP] Matrix cargada');
        } catch (err) {
            console.error('[SP] Error al construir la matriz:', err);
        }
    });

    return {};
});