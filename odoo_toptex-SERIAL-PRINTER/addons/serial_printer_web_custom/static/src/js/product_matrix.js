/** @odoo-module **/

// ================== Utilidad: DOM listo ==================
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// ================== Buscar bloques de atributos ==================
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = Array.from(
        scope.querySelectorAll('[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div')
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
            const id = (parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0", 10) || 0);
            const txt = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                .replace(/\s+/g, " ").trim();
            return id ? { id, text: txt, _radio: inp } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options, _el: el });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// ================== Ordenar tallas ==================
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase());
        const ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// ================== Construir HTML matriz ==================
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += '</tr></thead>';

    let tbody = '<tbody>';
    color.options.forEach((c) => {
        tbody += `<tr data-color-id="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="" />
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
        tbody += `</tr>`;
    });
    tbody += '</tbody>';

    return `
      <div id="sp-matrix" class="sp-matrix-box">
        <table class="sp-matrix__table">${thead}${tbody}</table>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// ================== Utilidades de inserción/posicionamiento ==================
function commonAncestor(el1, el2) {
    if (!el1) return el2 || null;
    if (!el2) return el1 || null;
    const set = new Set();
    for (let a = el1; a; a = a.parentElement) set.add(a);
    for (let b = el2; b; b = b.parentElement) if (set.has(b)) return b;
    return null;
}

function findAnchor(page, colorEl, sizeEl) {
    const both = commonAncestor(colorEl, sizeEl);
    if (both) return both;
    return page.querySelector(".js_attributes") ||
           page.querySelector("form.o_wsale_product_configurator") ||
           page;
}

// ================== Miniatura por color (mejorada) ==================
function getColorThumbSrc(page, colorId) {
    // 1) Localiza el radio del color
    const radio = page.querySelector(
        `input[type="radio"][data-value-id="${colorId}"], input[type="radio"][data-attribute-value-id="${colorId}"]`
    );
    const lbl = radio ? (radio.closest("label") || page.querySelector(`label[for="${radio.id}"]`)) : null;

    // 2) Imagen directa dentro del label
    const imgInLabel = lbl?.querySelector("img");
    if (imgInLabel?.src) return imgInLabel.src;

    // 3) Atributos de datos frecuentes
    const dataCandidates = [
        "img", "image", "src", "original", "thumbnail", "thumb", "colorImage", "valueImage"
    ];
    for (const key of dataCandidates) {
        const v = radio?.dataset?.[key] || lbl?.dataset?.[key];
        if (v) return v;
    }

    // 4) background-image en label o swatch interno
    const bgHost = lbl?.querySelector('[style*="background-image"]') || lbl;
    if (bgHost?.style?.backgroundImage && bgHost.style.backgroundImage !== "none") {
        const url = bgHost.style.backgroundImage.slice(4, -1).replace(/["']/g, "");
        if (url) return url;
    }

    // 5) URL directa al modelo product.attribute.value (seguro aunque no haya imagen -> placeholder)
    return `/web/image/product.attribute.value/${colorId}/image_1920/64x64`;
}

function fillColorThumbs(page, color) {
    color.options.forEach((c) => {
        const img = page.querySelector(`#sp-matrix tr[data-color-id="${c.id}"] img.sp-color__img`);
        if (!img) return;
        img.src = getColorThumbSrc(page, c.id);
        img.loading = "lazy";
        img.decoding = "async";
    });
}

// ================== Pintar/actualizar matriz ==================
let _debounceTimer = null;

function ensureMatrix() {
    if (window.__sp_building) return;
    window.__sp_building = true;
    try {
        const page = document.querySelector(".o_wsale_product_page");
        if (!page) return;

        // evita duplicados
        document.querySelectorAll("#sp-matrix").forEach((el) => el.remove());

        const { color, size } = getAttributeBlocks(page);
        if (!color || !size) {
            document.body.classList.remove("sp-matrix-active");
            return;
        }

        const anchor = findAnchor(page, color._el, size._el);
        if (!anchor) return;

        anchor.insertAdjacentHTML("afterend", renderGrid(color, size));
        document.body.classList.add("sp-matrix-active");

        // miniaturas por color
        fillColorThumbs(page, color);
    } finally {
        window.__sp_building = false;
    }
}

// ================== Arranque ==================
onReady(() => {
    ensureMatrix();

    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (!ev.target.matches('input[type="radio"]')) return;
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(() => ensureMatrix(), 50);
    });
});