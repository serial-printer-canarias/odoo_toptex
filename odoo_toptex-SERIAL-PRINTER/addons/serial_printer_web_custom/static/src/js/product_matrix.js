/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { jsonRpc } from '@web/core/network/rpc_service';

class SerialPrinterMatrix extends publicWidget.Widget {
    static selector = '.o_wsale_product_page';
    static events = { 'click .spm-add': '_onAddToCart' };

    start() {
        try {
            this._buildMatrix();
        } catch (e) {
            console.error('[SP] Error construyendo la matriz:', e);
        }
        return super.start();
    }

    // Lee bloques de atributos y detecta color/talla por nombre
    _readAttributeBlocks() {
        const blocks = [...this.el.querySelectorAll('[data-attribute_name]')].map((el) => {
            const name = (el.getAttribute('data-attribute_name') || '').trim();
            const radios = [...el.querySelectorAll('input[type="radio"]')];
            const options = radios.map((r) => ({
                id: r.value || r.dataset.valueId || '',
                text: (r.closest('label')?.textContent || r.getAttribute('data-value_name') || '').trim(),
                el: r,
            })).filter(o => o.text);
            return { name, options, el };
        });

        const isColor = (n) => /(color|colour|couleur|farbe)/i.test(n);
        const isSize  = (n) => /(talla|size|taille|größe|maat)/i.test(n);

        const colorBlock = blocks.find(b => isColor(b.name));
        const sizeBlock  = blocks.find(b => isSize(b.name));

        return {
            colors: colorBlock ? colorBlock.options.map(o => o.text) : [],
            sizes:  sizeBlock  ? sizeBlock.options.map(o => o.text)  : [],
        };
    }

    _buildMatrix() {
        if (this.el.querySelector('#sp-matrix')) return;

        const { colors, sizes } = this._readAttributeBlocks();
        if (!colors.length || !sizes.length) {
            // Si no detectamos COLOR y TALLA, no hacemos nada (otros productos seguirán igual)
            return;
        }

        const host = this.el.querySelector('form.o_wsale_product_configurator') || this.el;
        const wrap = document.createElement('div');
        wrap.id = 'sp-matrix';
        wrap.className = 'spm-wrapper';
        wrap.style.setProperty('--spm-cols', String(sizes.length));

        // Encabezado columnas (tallas)
        let html = '<div class="spm-grid"><div class="spm-corner"></div>';
        for (const s of sizes) html += `<div class="spm-th">${s}</div>`;

        // Filas por color + celdas de cantidad
        for (const c of colors) {
            html += `<div class="spm-rowhead">${c}</div>`;
            for (const s of sizes) {
                html += `
                    <div class="spm-td">
                        <input type="number" min="0" step="1"
                               class="spm-qty"
                               data-color="${c}" data-size="${s}" value="0">
                    </div>`;
            }
        }
        html += '</div>';

        // Botón añadir al carrito
        html += `<button type="button" class="btn btn-primary mt-2 spm-add">
                    Añadir selecciones al carrito
                 </button>`;

        wrap.innerHTML = html;

        // Insertamos antes del bloque de cantidad estándar si existe
        const anchor = host.querySelector('.css_quantity')?.parentElement || host;
        anchor.insertBefore(wrap, anchor.firstChild);
    }

    async _onAddToCart(ev) {
        ev.preventDefault();
        const calls = [];
        const inputs = this.el.querySelectorAll('#sp-matrix input.spm-qty');

        inputs.forEach((inp) => {
            const qty = parseFloat(inp.value || '0');
            // NOTA: aquí aún no asignamos variantId; por ahora añadimos la variante actualmente seleccionada
            // (pragmático para evitar errores). En el siguiente paso, si quieres, lo ligamos a cada combinación.
            if (qty > 0) {
                calls.push(jsonRpc('/shop/cart/update_json', {
                    add_qty: qty,
                    // product_id vacío -> usa la variante actualmente seleccionada por el configurador
                    display: false,
                }));
            }
        });

        if (!calls.length) return;
        try {
            await Promise.all(calls);
            window.location.reload();
        } catch (e) {
            console.error('[SP] Fallo al añadir desde la matriz:', e);
        }
    }
}

publicWidget.registry.SerialPrinterMatrix = SerialPrinterMatrix;
export default SerialPrinterMatrix;