odoo.define('serial_printer_web_custom.product_matrix', [], function (require) {
    'use strict';

    // Inyecta un CSS mínimo para la tabla (evita depender del SCSS)
    (function injectStyle(){
        if (document.getElementById('sp-matrix-style')) return;
        const css = `
            .o_sp_matrix{margin:1rem 0;overflow-x:auto}
            .o_sp_matrix table{width:100%;border-collapse:collapse}
            .o_sp_matrix th,.o_sp_matrix td{border:1px solid #e5e7eb;padding:.5rem;text-align:center}
            .o_sp_matrix th{white-space:nowrap}
            .o_sp_matrix input.qty{width:72px;text-align:center}
        `;
        const s = document.createElement('style');
        s.id = 'sp-matrix-style';
        s.textContent = css;
        document.head.appendChild(s);
    })();

    function ready(fn){ document.readyState !== 'loading' ? fn() : document.addEventListener('DOMContentLoaded', fn); }

    // Busca bloques de atributos en distintas versiones de Odoo
    function findAttributeBlocks(root){
        const nodes = Array.from(root.querySelectorAll(
            '[data-attribute_name], [data-attribute-name], .o_variant_attribute, .js_attribute'
        ));
        const blocks = [];
        for (const el of nodes){
            const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
            if (!radios.length) continue;

            let name =
                el.getAttribute('data-attribute_name') ||
                el.getAttribute('data-attribute-name') || '';
            if (!name){
                const label = el.querySelector('.o_variant_label, .attribute_name, legend, .label');
                name = (label && label.textContent || '').trim();
            }

            const options = radios.map(r => {
                const lbl = r.closest('label') || el.querySelector(`label[for="${r.id}"]`);
                const txt = (lbl ? lbl.textContent : r.value || '').trim();
                const id  = r.value || r.dataset.value_id || r.getAttribute('data-value_id') || r.id;
                return { id, text: txt, input: r };
            });

            blocks.push({ name: (name||'').toLowerCase(), el, options });
        }
        return blocks;
    }

    ready(function(){
        const page = document.querySelector('.o_wsale_product_page');
        if (!page){ console.log('[SP] matrix: página de producto no encontrada'); return; }

        const blocks = findAttributeBlocks(page);
        console.log('[SP] matrix: bloques detectados =>', blocks.map(b => ({name:b.name, n:b.options.length})));
        if (blocks.length < 2){ console.log('[SP] matrix: no hay suficientes atributos'); return; }

        const isColor = n => /(color|colour|colou?r)/i.test(n);
        const isSize  = n => /(size|talla|taille|maat|größe|taglia)/i.test(n);

        const color = blocks.find(b => isColor(b.name)) || blocks[0];
        const size  = blocks.find(b => isSize(b.name))  || blocks[1];

        // Construye grid
        const holder = document.createElement('div'); holder.className = 'o_sp_matrix';
        const table  = document.createElement('table');
        const thead  = document.createElement('thead');
        const trh    = document.createElement('tr');
        trh.appendChild(document.createElement('th')); // esquina vacía
        size.options.forEach(opt => { const th=document.createElement('th'); th.textContent=opt.text; trh.appendChild(th); });
        thead.appendChild(trh); table.appendChild(thead);

        const tbody = document.createElement('tbody');
        color.options.forEach(c => {
            const tr = document.createElement('tr');
            const th = document.createElement('th'); th.textContent = c.text; tr.appendChild(th);
            size.options.forEach(s => {
                const td = document.createElement('td');
                const inp = document.createElement('input');
                inp.type='number'; inp.min='0'; inp.step='1'; inp.className='qty';
                inp.dataset.colorId=c.id; inp.dataset.sizeId=s.id;
                td.appendChild(inp); tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
        table.appendChild(tbody); holder.appendChild(table);

        // Inserta el grid justo después del último bloque de atributos
        const allAttr = Array.from(page.querySelectorAll('[data-attribute_name], [data-attribute-name], .o_variant_attribute, .js_attribute'));
        const last    = allAttr.length ? allAttr[allAttr.length-1] : null;
        (last && last.parentNode) ? last.parentNode.insertBefore(holder, last.nextSibling) : page.appendChild(holder);

        console.log('[SP] Matrix cargada ✔️');
    });

    return {};
});