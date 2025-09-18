/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Buscar los bloques de atributos (Color, Talla) en la ficha ===
function getAttributeBlocks(scope) {
    const blocks = [];
    // Soporta distintas plantillas: contenedores con radios y nombre del atributo
    const containers = Array.from(
        scope.querySelectorAll(
            // Odoo 18 (casos habituales)
            '[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div'
        )
    );

    containers.forEach((el) => {
        const name = (
            el.getAttribute("data-attribute_name") ||
            el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
            el.getAttribute("name") ||
            ""
        ).trim().toLowerCase();

        const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
        if (!radios.length) return;

        const options = radios.map((inp) => {
            const id = parseInt(
                inp.dataset.valueId ||
                inp.dataset.attributeValueId ||
                inp.value ||
                "0",
                10
            ) || 0;

            const txt = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                .replace(/\s+/g, " ")
                .trim();

            return id ? { id, text: txt, _radio: inp } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options, _el: el });
    });

    // Detecta color y talla por nombre
    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// === Ordena tallas (numéricas o estándar) ===
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!isNaN(na) && !isNaN(nb)) return na - nb; // 6, 8, 10...

        const ia = std.indexOf(a.text.toUpperCase());
        const ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;      // XS < S < M...

        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// === Devuelve URL de miniatura para un color (si hay imagen de variante) ===
function getThumbUrlForColor(colorId) {
    // 1) Miniaturas con data-attribute_value_ids (típicas en carrusel)
    const nodes = document.querySelectorAll(
        '.o_carousel_product_images [data-attribute_value_ids],' +
        '.o_product_images [data-attribute_value_ids],' +
        '.o_product_image [data-attribute_value_ids],' +
        '.o_product_img [data-attribute_value_ids]'
    );
    for (const n of nodes) {
        const ids = (n.getAttribute('data-attribute_value_ids') || '')
            .split(',')
            .map(s => s.trim());
        if (ids.includes(String(colorId))) {
            const img = n.querySelector('img');
            if (img?.src) return img.src;
            const bg = getComputedStyle(n).backgroundImage;
            if (bg && bg !== 'none') return bg.replace(/^url\(["']?(.+?)["']?\)$/, '$1');
        }
    }

    // 2) Imagen dentro de la etiqueta del radio del color
    const input = document.querySelector(
        `input[type="radio"][data-value-id="${colorId}"], input[type="radio"][data-attribute-value-id="${colorId}"]`
    );
    if (input) {
        const lbl = input.closest('label');
        const img = lbl?.querySelector('img');
        if (img?.src) return img.src;
        const bg = lbl && getComputedStyle(lbl).backgroundImage;
        if (bg && bg !== 'none') return bg.replace(/^url\(["']?(.+?)["']?\)$/, '$1');
    }

    // 3) Fallback a imagen principal
    const main = document.querySelector(
        '.o_carousel_product_images .carousel-item.active img,' +
        '.o_product_image img,' +
        '.o_product_img img'
    );
    return main?.src || '';
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// === Construye el HTML de la matriz (solo UI) ===
function renderGrid(color, size, imgByColor) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += '</tr></thead>';

    let tbody = '<tbody>';
    color.options.forEach((c) => {
        const url = imgByColor[c.id] || '';
        tbody += `<tr>
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" src="${escapeHtml(url)}" alt="">
                    <span>${escapeHtml(c.text)}</span>
                </div>
            </th>`;
        size.options.forEach((s) => {
            tbody += `<td>
                <div class="sp-cell">
                    <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric"
                           placeholder="0" data-color="${c.id}" data-size="${s.id}">
                    <div class="sp-meta"></div>
                </div>
            </td>`;
        });
        tbody += '</tr>';
    });
    tbody += '</tbody>';

    return `
      <div id="sp-matrix" class="sp-matrix-box">
        <table class="sp-matrix__table">${thead}${tbody}</table>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// === Inserta/actualiza la matriz en la ficha ===
function ensureMatrix() {
    const page = document.querySelector('.o_wsale_product_page');
    if (!page) return;

    // Evita duplicados
    page.querySelector('#sp-matrix')?.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info('[SP] Matrix: faltan atributos Color y/o Talla. No se pinta.');
        document.body.classList.remove('sp-matrix-active');
        return;
    }

    // Precalcula miniaturas por color
    const imgByColor = {};
    color.options.forEach(o => { imgByColor[o.id] = getThumbUrlForColor(o.id); });

    // HTML matriz
    const html = renderGrid(color, size, imgByColor);

    // Colocar JUSTO DESPUÉS del bloque de atributos
    const attrBlock =
        page.querySelector('.js_attributes') ||
        page.querySelector('form.o_wsale_product_configurator') ||
        page;
    attrBlock.insertAdjacentHTML('afterend', html);

    document.body.classList.add('sp-matrix-active');
    console.log('[SP] Matrix lista (solo UI).');
}

// === Arranque / Reconstrucción ante cambios de radios ===
onReady(() => {
    ensureMatrix();

    const page = document.querySelector('.o_wsale_product_page');
    if (!page) return;

    // Si el usuario cambia un radio (color/talla), reconstruimos
    page.addEventListener('change', (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });

    // Por si el configurador actualiza el DOM (owl renders)
    const mo = new MutationObserver((muts) => {
        if (muts.some(m => m.addedNodes.length || m.removedNodes.length)) {
            // micro debounce
            clearTimeout(window.__spMatrixT);
            window.__spMatrixT = setTimeout(ensureMatrix, 100);
        }
    });
    mo.observe(page, { childList: true, subtree: true });
});