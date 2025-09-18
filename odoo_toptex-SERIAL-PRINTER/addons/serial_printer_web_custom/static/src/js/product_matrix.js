/** Odoo 18 – Frontend **/
odoo.define('serial_printer_web_custom.product_matrix', [
    'web.public.widget',     // <- SOLO esta dependencia. Nada de web.ajax.
], function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    // ---------- Utils ----------
    function onReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    // Orden “inteligente” de tallas (XXS..5XL y números: 6,8,10…)
    function sizeKey(txt) {
        const t = String(txt || '').trim().toUpperCase();
        const map = {
            'XXS': 0, 'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5,
            '2XL': 6, 'XXL': 6, '3XL': 7, '4XL': 8, '5XL': 9,
        };
        if (t in map) return map[t];
        const m = t.match(/(\d+)/);
        return m ? parseInt(m[1], 10) : 9999;
    }

    // Localiza grupos de atributos (Color, Talla) en distintas plantillas
    function getAttributeBlocks(scope) {
        const blocks = [];
        const groupCandidates = scope.querySelectorAll(
            '[data-attribute_name], .js_attribute, .o_variant_attribute, .variant_attribute'
        );

        groupCandidates.forEach((el) => {
            // Nombre del grupo
            const name =
                (el.getAttribute('data-attribute_name') || '') ||
                (el.querySelector('.attribute_name, .o_variant_label, legend, .form-label, label')?.textContent || '');
            const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
            if (!radios.length) return;

            const options = radios.map((inp) => {
                const id = parseInt(inp.dataset.valueId || inp.value || '0', 10) || null;
                const lab = el.querySelector(`label[for="${inp.id}"]`) || inp.closest('label');
                const text = (lab ? lab.textContent : (inp.value || '')).replace(/\s+/g, ' ').trim();
                return id ? { id, text, input: inp } : null;
            }).filter(Boolean);

            if (options.length) {
                blocks.push({
                    name: (name || '').trim(),
                    options,
                    el,
                });
            }
        });
        return blocks;
    }

    // Crea el HTML de la tabla
    function renderGrid(color, size) {
        // Ordenar tallas
        size.options.sort((a, b) => sizeKey(a.text) - sizeKey(b.text));

        let thead = `<th class="sp-sticky-left"></th>`;
        size.options.forEach((s) => {
            thead += `<th><div class="sp-meta"><strong>${s.text}</strong></div></th>`;
        });

        const rows = color.options.map((c) => {
            let tds = `<td class="sp-sticky-left">
                <div class="sp-color">
                    <span class="sp-color__name">${c.text}</span>
                </div>
            </td>`;
            size.options.forEach((s) => {
                // De momento no calculamos el variant_id aquí; lo conectamos en el paso 4.
                tds += `<td>
                    <div class="sp-cell">
                        <input type="number" min="0" step="1" value="0"
                               class="sp-qty"
                               data-color-id="${c.id}"
                               data-size-id="${s.id}">
                        <div class="sp-meta"></div>
                    </div>
                </td>`;
            });
            return `<tr>${tds}</tr>`;
        }).join('');

        return `
        <div id="sp-matrix" class="mt-3">
            <table class="sp-matrix__table">
                <thead><tr>${thead}</tr></thead>
                <tbody>${rows}</tbody>
            </table>
            <div class="mt-2">
                <button type="button" class="btn btn-primary sp-matrix-add">
                    Añadir selección
                </button>
                <small class="text-muted ms-2">Indica cantidades por color y talla.</small>
            </div>
        </div>`;
    }

    // ---------- Widget ----------
    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',

        start() {
            onReady(() => this._mountMatrix());
            return this._super(...arguments);
        },

        _mountMatrix() {
            // Evitar duplicados
            if (document.getElementById('sp-matrix')) return;

            const root = this.el || document;
            const attrsWrap =
                root.querySelector('.js_product .js_attributes') ||
                root.querySelector('.o_wsale_product_configurator') ||
                root.querySelector('.js_product');

            if (!attrsWrap) {
                console.warn('[SP] No se encontraron atributos en la página.');
                return;
            }

            const blocks = getAttributeBlocks(attrsWrap);
            if (!blocks.length) {
                console.warn('[SP] No se detectaron grupos de atributos.');
                return;
            }

            // Detectar COLOR y TALLA por nombre (con fallback por orden)
            const colorBlock =
                blocks.find((b) => /colou?r/i.test(b.name)) || blocks[0];
            const sizeBlock =
                blocks.find((b) => /(talla|size|taille|größe|maat)/i.test(b.name)) || blocks[1];

            if (!colorBlock || !sizeBlock) {
                console.warn('[SP] Faltan bloques de Color o Talla.', { blocks });
                return;
            }

            // Oculta los radios originales sólo cuando la matriz está activa
            this.el.classList.add('sp-matrix-active');

            // Insertar la tabla justo debajo de los atributos
            const html = renderGrid(colorBlock, sizeBlock);
            const holder = document.createElement('div');
            holder.innerHTML = html;
            attrsWrap.parentNode.insertBefore(holder, attrsWrap.nextSibling);

            // (Paso 4) Conectaremos aquí el click de ".sp-matrix-add" para añadir al carrito.
            holder.querySelector('.sp-matrix-add')?.addEventListener('click', () => {
                alert('UI lista. En el siguiente paso conectamos el carrito.');
            });

            console.log('[SP] Matrix montada');
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});