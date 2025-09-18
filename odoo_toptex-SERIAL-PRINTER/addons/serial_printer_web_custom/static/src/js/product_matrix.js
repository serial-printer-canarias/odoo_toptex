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

        const options = radios
            .map((inp) => {
                const id = parseInt(
                    inp.dataset.valueId ||
                    inp.dataset.attributeValueId ||
                    inp.value ||
                    "0",
                    10
                ) || 0;

                const txt = (
                    inp.closest("label")?.textContent ||
                    inp.getAttribute("title") ||
                    ""
                ).replace(/\s+/g, " ").trim();

                return id ? { id, text: txt, _radio: inp } : null;
            })
            .filter(Boolean);

        if (options.length) blocks.push({ name, options });
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
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
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

// === Insertar justo debajo de .js_attributes (si existe) ===
function insertAfterAttributes(html, page) {
    const attrs = page.querySelector(".js_attributes");
    if (attrs) {
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        attrs.insertAdjacentElement("afterend", tmp.firstElementChild);
    } else {
        // fallback
        page.insertAdjacentHTML("beforeend", html);
    }
}

// === Encontrar la miniatura del color (img en el label o background-image del swatch) ===
function findColorImageSrc(colorId, scope) {
    const input = scope.querySelector(
        `input[type="radio"][data-value-id="${colorId}"],
         input[type="radio"][data-attribute-value-id="${colorId}"],
         input[type="radio"][value="${colorId}"]`
    );
    if (!input) return null;

    const label = scope.querySelector(`label[for="${input.id}"]`) || input.closest("label");
    if (!label) return null;

    const img = label.querySelector("img");
    if (img && img.src) return img.src;

    const sw = label.querySelector(".o_variant_image, .o_variant_color, .variant_img, span, i");
    if (sw) {
        const bg = getComputedStyle(sw).backgroundImage;
        const m = /url\(["']?(.*?)["']?\)/.exec(bg);
        if (m && m[1]) return m[1];
    }
    return null;
}

// === Rellenar miniaturas por fila de color ===
function fillColorThumbs(page) {
    const scope = page;
    const rows = page.querySelectorAll("#sp-matrix tr[data-color-id]");
    let fallback = null;

    const mainImg = page.querySelector(
        ".o_wsale_product_images img, #o-carousel-product .carousel-item.active img, .o_gallery_img"
    );
    if (mainImg) fallback = mainImg.src;

    rows.forEach((tr) => {
        const cid = tr.getAttribute("data-color-id");
        const src = findColorImageSrc(cid, scope) || fallback || "";
        const imgEl = tr.querySelector(".sp-color__img");
        if (imgEl && src) imgEl.src = src;
    });
}

// === Evitar duplicados y pintar ===
function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    // Elimina TODAS las matrices previas (por recargas/ediciones o listeners duplicados)
    page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info("[SP] Matrix: faltan atributos Color y/o Talla. No se pinta.");
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    insertAfterAttributes(renderGrid(color, size), page);
    fillColorThumbs(page);
    document.body.classList.add("sp-matrix-active");
    console.log("[SP] Matrix lista (UI).");
}

// === Arranque (un solo listener) ===
onReady(() => {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    ensureMatrix();

    if (!page.dataset.spMatrixBound) {
        page.dataset.spMatrixBound = "1";
        page.addEventListener("change", (ev) => {
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    }
});