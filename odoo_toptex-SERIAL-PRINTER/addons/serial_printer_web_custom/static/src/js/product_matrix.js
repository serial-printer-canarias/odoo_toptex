/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Buscar los bloques de atributos (Color, Talla) en la ficha ===
function getAttributeBlocks(scope) {
    const blocks = [];
    // Contenedores posibles de atributos (Odoo 18 y themes)
    const containers = Array.from(
        scope.querySelectorAll(
            '[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div'
        )
    );

    containers.forEach((el) => {
        const name = (
            el.getAttribute("data-attribute_name") ||
            el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
            el.getAttribute("name") || ""
        ).trim().toLowerCase();

        const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
        if (!radios.length) return;

        const options = radios
            .map((inp) => {
                const id =
                    parseInt(
                        inp.dataset.valueId ||
                        inp.dataset.attributeValueId ||
                        inp.value || "0",
                        10
                    ) || 0;

                const txt = (
                    inp.closest("label")?.textContent ||
                    inp.getAttribute("title") || ""
                ).replace(/\s+/g, " ").trim();

                // Intentar capturar imagen del swatch si existe
                const imgEl =
                    inp.closest("label")?.querySelector("img") ||
                    inp.parentElement?.querySelector("img");
                const img = imgEl?.src || "";

                return id ? { id, text: txt, img } : null;
            })
            .filter(Boolean);

        if (options.length) {
            // guardamos también el elemento para usarlo como ancla
            blocks.push({ name, options, el });
        }
    });

    // Detecta color y talla por nombre
    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));
    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// === Ordenar tallas: numéricas (6,8,10...) o estándar (XS, S, M...) ===
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

// === Construye el HTML de la matriz (solo UI) ===
function renderGrid(color, size, fallbackImg) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        const imgSrc = c.img || fallbackImg || "";
        tbody += `<tr>
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="" src="${imgSrc}"/>
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
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
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

    // Miniatura fallback = imagen principal del producto si no hay swatch con <img>
    const fallbackImg =
        page.querySelector(".o_wsale_product_img img, .product_detail_img img")?.src || "";

    const html = renderGrid(color, size, fallbackImg);
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    const matrixEl = tmp.firstElementChild;

    // === POSICIÓN: justo DESPUÉS del bloque de atributos ===
    // Buscamos primero el contenedor de atributos; si no, form del configurador.
    const attrsBox =
        page.querySelector(".js_attributes") ||
        color?.el?.closest(".js_attributes") ||
        size?.el?.closest(".js_attributes") ||
        color?.el?.closest("form.o_wsale_product_configurator, .o_product_configurator") ||
        size?.el?.closest("form.o_wsale_product_configurator, .o_product_configurator");

    if (attrsBox) {
        attrsBox.insertAdjacentElement("afterend", matrixEl);
    } else {
        // Último recurso: lo añadimos al final de la columna principal
        page.appendChild(matrixEl);
    }

    document.body.classList.add("sp-matrix-active");
    console.log("[SP] Matrix lista (UI) insertada tras atributos.");
}

// === Arranque ===
onReady(() => {
    ensureMatrix();
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});