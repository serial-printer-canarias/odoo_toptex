/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Buscar los bloques de atributos (Color, Talla) en la ficha ===
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
                inp.getAttribute("title") || ""
            ).replace(/\s+/g, " ").trim();

            return id ? { id, text: txt, _radio: inp } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options });
    });

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
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase());
        const ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// === HTML de la matriz (solo UI) ===
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

// === Miniatura por color (label > img, o cualquier hijo con background-image, o data-*) ===
function findColorImageSrc(colorId, scope) {
    const input = scope.querySelector(
        `input[type="radio"][data-value-id="${colorId}"],
         input[type="radio"][data-attribute-value-id="${colorId}"],
         input[type="radio"][value="${colorId}"]`
    );
    if (!input) return null;

    const label = scope.querySelector(`label[for="${input.id}"]`) || input.closest("label");
    if (!label) return null;

    // 1) <img> dentro del label
    const img = label.querySelector("img");
    if (img?.src) return img.src;

    // 2) Algún hijo con background-image
    const withBg = Array.from(label.querySelectorAll("*")).find((n) => {
        const bg = getComputedStyle(n).backgroundImage;
        return bg && bg !== "none" && /url\(/i.test(bg);
    });
    if (withBg) {
        const bg = getComputedStyle(withBg).backgroundImage;
        const m = /url\(["']?(.*?)["']?\)/.exec(bg);
        if (m?.[1]) return m[1];
    }

    // 3) Atributos data comunes
    const dataUrl = label.dataset.imageUrl || label.dataset.img || input.dataset.img || "";
    if (dataUrl) return dataUrl;

    return null;
}

function fillColorThumbs(page) {
    const rows = page.querySelectorAll("#sp-matrix tr[data-color-id]");
    const mainImg = page.querySelector(
        ".o_wsale_product_images img, #o-carousel-product .carousel-item.active img, .o_gallery_img"
    );
    const fallback = mainImg?.src || "";
    rows.forEach((tr) => {
        const cid = tr.getAttribute("data-color-id");
        const src = findColorImageSrc(cid, page) || fallback;
        const imgEl = tr.querySelector(".sp-color__img");
        if (imgEl && src) imgEl.src = src;
    });
}

// === Insertar la matriz: preferencia 1) justo después de los atributos ===
function placeMatrix(html, page) {
    const attrs = page.querySelector(".js_attributes");
    if (attrs) {
        attrs.insertAdjacentHTML("afterend", html);
        return true;
    }
    // 2) antes del botón Add to Cart (por si falla lo anterior)
    const btn = page.querySelector(
        'button[name="add_to_cart"], button[name="add"], a.js_add_to_cart, .o_wsale_product_btn .btn-primary, .o_add_to_cart'
    );
    if (btn) {
        btn.insertAdjacentHTML("beforebegin", html);
        return true;
    }
    // 3) último recurso
    page.insertAdjacentHTML("beforeend", html);
    return false;
}

// === Evitar duplicados y pintar ===
function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info("[SP] Matrix: faltan atributos Color y/o Talla. No se pinta.");
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    const html = renderGrid(color, size);
    placeMatrix(html, page);
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