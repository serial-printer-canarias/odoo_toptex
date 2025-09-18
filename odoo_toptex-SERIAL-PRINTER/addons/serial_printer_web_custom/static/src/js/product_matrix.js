/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Buscar los bloques de atributos (Color, Talla) en la ficha ===
function getAttributeBlocks(scope) {
    const blocks = [];
    // Soporta distintas plantillas: busca contenedores con radios y nombre del atributo
    const containers = Array.from(
        scope.querySelectorAll(
            // Odoo 18 (varios casos habituales)
            '[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div'
        )
    );

    containers.forEach((el) => {
        const name =
            (el.getAttribute("data-attribute_name") ||
                el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
                el.getAttribute("name") ||
                "")
                .trim()
                .toLowerCase();

        const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
        if (!radios.length) return;

        const options = radios
            .map((inp) => {
                const id =
                    parseInt(
                        inp.dataset.valueId ||
                            inp.dataset.attributeValueId ||
                            inp.value ||
                            "0",
                        10
                    ) || 0;
                const txt =
                    (inp.closest("label")?.textContent ||
                        inp.getAttribute("title") ||
                        "")
                        .replace(/\s+/g, " ")
                        .trim();
                return id ? { id, text: txt } : null;
            })
            .filter(Boolean);

        if (options.length) blocks.push({ name, options });
    });

    // Detecta color y talla por nombre
    const color = blocks.find((b) =>
        /(color|colour|colou?r|c[oó]lor)/i.test(b.name)
    );
    const size = blocks.find((b) =>
        /(size|talla|talle|taille|größe|maat)/i.test(b.name)
    );

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// === Ordenar tallas: numéricas (6,8,10...) o estándar (XS, S, M...) ===
function sortSizes(opts) {
    const std = [
        "2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL",
    ];
    return [...opts].sort((a, b) => {
        // Si ambas son numéricas (p. ej., 6 UK, 8 UK), ordena por número
        const na = parseFloat(a.text);
        const nb = parseFloat(b.text);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;

        // Si ambas son estándar
        const ia = std.indexOf(a.text.toUpperCase());
        const ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;

        // Fallback al orden alfabético natural
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// === Construye el HTML de la matriz (solo UI) ===
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => {
        thead += `<th>${escapeHtml(s.text)}</th>`;
    });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        tbody += `<tr>
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

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[c]));
}

// === Inserta/actualiza la matriz en la ficha ===
function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    // Evita duplicados
    const existing = page.querySelector("#sp-matrix");
    if (existing) existing.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info("[SP] Matrix: faltan atributos Color y/o Talla. No se pinta.");
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    const host =
        page.querySelector(".js_attributes") ||
        page.querySelector("form.o_wsale_product_configurator") ||
        page;

    host.insertAdjacentHTML("beforeend", renderGrid(color, size));
    document.body.classList.add("sp-matrix-active");

    console.log("[SP] Matrix lista (solo UI).");
}

// === Arranque ===
onReady(() => {
    ensureMatrix();
    // Si el usuario cambia algo en radios (poco común porque los ocultamos), reconstruimos
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});