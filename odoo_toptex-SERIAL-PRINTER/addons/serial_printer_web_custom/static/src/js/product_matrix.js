/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

/* -------------------- helpers de imagen -------------------- */

// Intenta extraer una URL de imagen de un swatch/label (img o background-image)
function getSwatchImage(inp) {
    const lab = inp.closest("label") || inp.parentElement;
    if (!lab) return "";

    // 1) <img src> dentro del label
    const img = lab.querySelector("img");
    if (img?.getAttribute("src")) return img.getAttribute("src");
    if (img?.getAttribute("data-src")) return img.getAttribute("data-src");

    // 2) background-image inline (algunos themes)
    const withBg = lab.querySelector('[style*="background-image"]') || lab;
    const bg = window.getComputedStyle(withBg).getPropertyValue("background-image");
    // background-image: url("...") -> extrae url
    const m = bg && bg !== "none" ? bg.match(/url\(["']?(.*?)["']?\)/i) : null;
    return m ? m[1] : "";
}

// Imagen principal del producto (fallback)
function getMainImageSrc(scope) {
    // varios selectores típicos en Odoo 18/themes
    const candidates = [
        ".o_wsale_product_img img",
        ".product_detail_img img",
        ".o_product_page_gallery img",
        ".carousel img",
        ".o_website_img img",
        ".img-fluid",
    ];
    for (const sel of candidates) {
        const el = scope.querySelector(sel);
        if (!el) continue;
        const src = el.getAttribute("src") || el.getAttribute("data-src");
        if (src) return src;
        // <source srcset> como fallback de <picture>
        const srcset = el.getAttribute?.("srcset") || el.getAttribute?.("data-srcset");
        if (srcset) return srcset.split(",")[0].trim().split(" ")[0];
    }
    return "";
}

/* -------------------- atributos -------------------- */

// Buscar los bloques de atributos (Color, Talla) en la ficha
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = Array.from(
        scope.querySelectorAll(
            // Odoo 18 + themes
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
                const id = parseInt(
                    inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                    10
                ) || 0;

                const txt = (
                    inp.closest("label")?.textContent ||
                    inp.getAttribute("title") || ""
                ).replace(/\s+/g, " ").trim();

                const img = getSwatchImage(inp);

                return id ? { id, text: txt, img } : null;
            })
            .filter(Boolean);

        if (options.length) blocks.push({ name, options, el });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// Ordenar tallas: numéricas (6,8,10...) o estándar (XS, S, M...)
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

/* -------------------- render -------------------- */

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

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

/* -------------------- inserción/posicion -------------------- */

// punto “seguro” para anclar la matriz justo tras los atributos
function findAttributesArea(page, color, size) {
    // 1) contenedor de atributos clásico
    let el = page.querySelector(".js_attributes");
    if (el) return el;

    // 2) formularios de configurador
    el = page.querySelector("form.o_wsale_product_configurator, form.o_product_configurator");
    if (el) return el;

    // 3) usa el padre directo de los radios
    el = color?.el?.closest(".js_attribute, .o_product_configurator, form") ||
         size?.el?.closest(".js_attribute, .o_product_configurator, form");
    if (el) return el;

    // 4) último recurso: el formulario del carrito
    el = page.querySelector('form[action*="/shop/cart"]');
    if (el) return el;

    return null;
}

function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    const existing = page.querySelector("#sp-matrix");
    if (existing) existing.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info("[SP] Matrix: faltan atributos Color y/o Talla. No se pinta.");
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    const fallbackImg = getMainImageSrc(page);
    const html = renderGrid(color, size, fallbackImg);
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    const matrixEl = tmp.firstElementChild;

    const anchor = findAttributesArea(page, color, size);
    if (anchor) {
        anchor.insertAdjacentElement("afterend", matrixEl);
    } else {
        page.appendChild(matrixEl); // si no encontramos nada, mantenemos el comportamiento anterior
    }

    document.body.classList.add("sp-matrix-active");
    console.log("[SP] Matrix lista (UI) insertada tras atributos.");
}

/* -------------------- arranque -------------------- */

onReady(() => {
    ensureMatrix();
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});