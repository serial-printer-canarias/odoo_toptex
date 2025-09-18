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
            // Odoo 18 (casos habituales de atributos)
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

        const options = radios.map((inp) => {
            const id = parseInt(
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                10
            ) || 0;
            const txt = (
                inp.closest("label")?.textContent ||
                inp.getAttribute("title") ||
                ""
            ).replace(/\s+/g, " ").trim();
            return id ? { id, text: txt } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options });
    });

    // Detecta color y talla por nombre
    const color = blocks.find(b => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find(b => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

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

// === Mapa idColor -> media (img o swatch) desde el DOM ===
function buildColorMediaMap(scope, colorBlock) {
    const map = new Map();

    // Imagen principal (fallback)
    const fallbackImg =
        scope.querySelector('.o_wsale_product_images img, .o_wsale_product_gallery img, #product_detail_img, .o_carousel_product img');
    const fallbackSrc = fallbackImg?.currentSrc || fallbackImg?.src || "";

    for (const opt of colorBlock.options) {
        const sel = [
            `input[data-value-id="${opt.id}"]`,
            `input[data-attribute-value-id="${opt.id}"]`,
            `input[value="${opt.id}"]`
        ].join(',');

        const inp  = scope.querySelector(sel);
        const lab  = inp ? (inp.closest('label') || inp.parentElement) : null;

        // 1) ¿Tiene imagen en la etiqueta?
        const labImg = lab?.querySelector('img');
        if (labImg?.src) {
            map.set(opt.id, { type: 'img', src: labImg.currentSrc || labImg.src });
            continue;
        }

        // 2) ¿Tiene swatch de color (background-color)?
        const colorEl = lab?.querySelector('[style*="background-color"], .css_attribute_color');
        const bg = colorEl ? (colorEl.style.backgroundColor || getComputedStyle(colorEl).backgroundColor) : "";
        if (bg) {
            map.set(opt.id, { type: 'swatch', color: bg });
            continue;
        }

        // 3) Fallback a imagen principal
        if (fallbackSrc) {
            map.set(opt.id, { type: 'img', src: fallbackSrc });
        }
    }

    return map;
}

// === Construye el HTML de la matriz (solo UI) ===
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        tbody += `
          <tr>
            <th class="sp-sticky-left">
              <div class="sp-color">
                <span class="sp-color__media" data-color-id="${c.id}"></span>
                <span class="sp-color__name">${escapeHtml(c.text)}</span>
              </div>
            </th>
        `;
        size.options.forEach((s) => {
            tbody += `
              <td>
                <div class="sp-cell">
                  <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric"
                         placeholder="0" data-color="${c.id}" data-size="${s.id}">
                  <div class="sp-meta"></div>
                </div>
              </td>
            `;
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

function populateColorMedia(scope, mediaMap) {
    const spots = scope.querySelectorAll('#sp-matrix .sp-color__media[data-color-id]');
    spots.forEach((el) => {
        const id = parseInt(el.getAttribute('data-color-id'), 10);
        const media = mediaMap.get(id);
        if (!media) return;
        if (media.type === 'img' && media.src) {
            el.innerHTML = `<img class="sp-color__img" src="${media.src}" alt="">`;
        } else if (media.type === 'swatch' && media.color) {
            el.innerHTML = `<span class="sp-swatch" style="background:${media.color}"></span>`;
        }
    });
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
    page.querySelector("#sp-matrix")?.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        console.info("[SP] Matrix: faltan atributos Color y/o Talla. No se pinta.");
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    // 1) Insertar JUSTO DESPUÉS del bloque de atributos (encima de “Personalizar”)
    const attrBlock = page.querySelector(".js_attributes");
    const html = renderGrid(color, size);
    if (attrBlock) {
        attrBlock.insertAdjacentHTML("afterend", html);
    } else {
        // fallback seguro (último recurso)
        (page.querySelector("form.o_wsale_product_configurator") || page)
            .insertAdjacentHTML("afterbegin", html);
    }

    // 2) Poner miniaturas/swatch por color
    const mediaMap = buildColorMediaMap(page, color);
    populateColorMedia(page, mediaMap);

    // Mantener visibles los radios (pediste no ocultarlos de momento)
    document.body.classList.add("sp-matrix-active");

    console.log("[SP] Matrix lista (UI + media por color).");
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