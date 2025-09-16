/** addons/serial_printer_web_custom/static/src/js/product_matrix.js **/
odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';

    // Utilidad simple para ejecutar cuando el DOM está listo
    function onReady(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    // Detecta los bloques de atributos (Color, Talla, etc.) en la ficha
    function getAttributeBlocks() {
        // Odoo cambia clases entre versiones; buscamos varias opciones
        const blocks = Array.from(document.querySelectorAll(
            '.js_attribute, .o_wsale_product_configurator .row > div, [data-attribute_name]'
        )).map(el => {
            const labelEl = el.querySelector('.form-label, .o_variant_label, label, .attribute_name');
            const name = (labelEl?.textContent || el.getAttribute('data-attribute_name') || '').trim().toLowerCase();
            const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
            if (!name || !radios.length) return null;
            const options = radios.map(r => {
                // Odoo suele poner data-value_id en el input o en el <li> contenedor
                const li = r.closest('li,[data-value_id]');
                const id = r.dataset.valueId || li?.dataset.valueId || r.value;
                // El texto visible puede estar en el label asociado o en el botón/etiqueta
                const txt =
                    (r.closest('label')?.textContent ||
                     li?.textContent ||
                     r.getAttribute('data-value_name') ||
                     '').trim();
                return id ? { id, text: txt } : null;
            }).filter(Boolean);
            return options.length ? { name, el, options } : null;
        }).filter(Boolean);

        // Intenta reconocer color y talla por nombre
        const isColor = n => /(color|colour|couleur|farbe)/i.test(n);
        const isSize  = n => /(talla|size|taille|größe|maat|taglia)/i.test(n);

        const color = blocks.find(b => isColor(b.name)) || blocks[0];
        const size  = blocks.find(b => isSize(b.name))  || blocks[1];

        return { color, size };
    }

    // Construye el grid HTML
    function renderGrid({ color, size }) {
        if (!color || !size) return;
        if (document.querySelector('#sp-matrix')) return; // evitar duplicados

        const container = document.createElement('div');
        container.id = 'sp-matrix';
        container.className = 'sp-matrix';

        // Cabecera con tallas (columnas)
        const header = document.createElement('div');
        header.className = 'sp-matrix__row sp-matrix__row--header';
        header.appendChild(document.createElement('div')).className = 'sp-matrix__cell sp-matrix__cell--corner';
        size.options.forEach(opt => {
            const c = document.createElement('div');
            c.className = 'sp-matrix__cell sp-matrix__cell--head';
            c.textContent = opt.text || opt.id;
            header.appendChild(c);
        });
        container.appendChild(header);

        // Filas por color
        color.options.forEach(col => {
            const row = document.createElement('div');
            row.className = 'sp-matrix__row';
            const head = document.createElement('div');
            head.className = 'sp-matrix__cell sp-matrix__cell--rowhead';
            head.textContent = col.text || col.id;
            row.appendChild(head);

            size.options.forEach(sz => {
                const cell = document.createElement('div');
                cell.className = 'sp-matrix__cell';
                const input = document.createElement('input');
                input.type = 'number';
                input.min = '0';
                input.step = '1';
                input.value = '';
                input.placeholder = '0';
                input.className = 'sp-matrix__qty';
                // Guardamos las claves para conectar con el carrito en el siguiente paso
                input.dataset.colorId = col.id;
                input.dataset.sizeId = sz.id;
                cell.appendChild(input);
                row.appendChild(cell);
            });

            container.appendChild(row);
        });

        // Botón de añadir múltiples
        const actions = document.createElement('div');
        actions.className = 'sp-matrix__actions';
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-primary sp-matrix__add';
        btn.textContent = odoo && odoo._t ? odoo._t('Add to cart (matrix)') : 'Add to cart (matrix)';
        actions.appendChild(btn);
        container.appendChild(actions);

        // Inserta el grid *después* del selector de variantes
        const variantsWrapper =
            document.querySelector('.o_wsale_product_configurator') ||
            color.el.closest('.o_wsale_product_configurator, .product-configurator, form') ||
            document.querySelector('#product_details, .o_wsale_product_page') ||
            document.querySelector('main');

        variantsWrapper?.appendChild(container);

        // De momento, solo feedback visual (no carrito)
        btn.addEventListener('click', () => {
            // Esto es solo para comprobar que el grid “funciona”
            const filled = Array.from(container.querySelectorAll('.sp-matrix__qty'))
                .filter(i => parseFloat(i.value || '0') > 0)
                .map(i => ({
                    colorId: i.dataset.colorId,
                    sizeId: i.dataset.sizeId,
                    qty: parseFloat(i.value),
                }));
            if (!filled.length) {
                alert('Introduce cantidades en el grid.');
                return;
            }
            console.log('[SP] Cantidades capturadas (grid):', filled);
            alert('Grid OK. Cantidades capturadas en consola. (Conectamos al carrito en el siguiente paso).');
        });
    }

    onReady(() => {
        try {
            const blocks = getAttributeBlocks();
            if (!blocks.color || !blocks.size) {
                console.warn('[SP] No se detectaron correctamente los atributos de Color/Talla.');
                return;
            }
            renderGrid(blocks);
            console.log('[SP] Matriz cargada.');
        } catch (e) {
            console.error('[SP] Error al construir la matriz:', e);
        }
    });
});