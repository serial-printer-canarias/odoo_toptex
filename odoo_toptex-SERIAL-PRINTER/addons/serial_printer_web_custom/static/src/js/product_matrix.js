/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Dónde anclar la tabla (debajo de los atributos) ===
function getAttrsContainer(page) {
    return (
        page.querySelector(".js_attributes") ||
        page.querySelector("form.o_wsale_product_configurator .js_attributes") ||
        page.querySelector("form.o_wsale_product_configurator") ||
        page.querySelector(".o_wsale_product_configurator") ||
        null
    );
}

// === Buscar bloques de atributos (Color, Talla) ===
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = Array.from(
        scope.querySelectorAll(
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
                inp.value || "0",
                10
            ) || 0;

            const txt = (
                inp.closest("label")?.textContent ||
                (inp.id ? (scope.querySelector(`label[for="${inp.id}"]`)?.textContent || "") : "") ||
                inp.getAttribute("title") ||
                ""
            ).replace(/\s+/g, " ").trim();

            return id ? { id, text: txt } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));
    if (size) size.options = sortSizes(size.options);

    return { color, size };
}

// === Ordenar tallas (numéricas o estándar) ===
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

// === Miniatura para un color: busca <img> o background en el label ===
function getColorThumbSrc(page, colorId) {
    const sel = `input[type="radio"][data-value-id="${colorId}"],
                 input[type="radio"][data-attribute-value-id="${colorId}"]`;
    const inp = page.querySelector(sel);
    if (inp) {
        const label = inp.closest("label") || (inp.id ? page.querySelector(`label[for="${inp.id}"]`) : null);
        if (label) {
            const im = label.querySelector("img");
            if (im?.src) return im.src;

            const bg = getComputedStyle(label).backgroundImage;
            const m = bg && bg !== "none" ? bg.match(/url\(["']?([^"')]+)["']?\)/) : null;
            if (m?.[1]) return m[1];
        }
    }
    // Fallback: imagen principal visible
    const gallery = page.querySelector('.o_carousel_product .carousel-item.active img, img.js_product_img, img[class*="product"]');
    return gallery?.src || "";
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[c]));
}

// === HTML de la matriz (solo UI) ===
function renderGrid(page, color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        const thumb = getColorThumbSrc(page, c.id);
        tbody += `<tr data-color-id="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" src="${thumb}" alt="">
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
        tbody += "</tr>";
    });
    tbody += "</tbody>";

    return `
      <div id="sp-matrix" class="sp-matrix-box">
        <table class="sp-matrix__table">${thead}${tbody}</table>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// === Inserta/actualiza matriz (debajo de los atributos; sin duplicados) ===
function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    // Limpia duplicados
    page.querySelectorAll("#sp-matrix").forEach((el) => el.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info("[SP] Matrix: faltan Color y/o Talla. No se pinta.");
        return;
    }

    const anchor = getAttrsContainer(page) || page;
    anchor.insertAdjacentHTML("afterend", renderGrid(page, color, size));
    console.log("[SP] Matrix renderizada debajo de atributos.");
}

// === Arranque ===
onReady(() => {
    ensureMatrix();
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    // Si cambian radios, re-pintamos
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});