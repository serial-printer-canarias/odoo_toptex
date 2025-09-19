/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// Estado global sencillo para evitar renders múltiples
const SP = (window.__SP ||= { rendering: false, bound: false });

// === Buscar bloques de atributos (Color/Talla) en la ficha ===
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
            const id = Number(
                inp.dataset.valueId ||
                inp.dataset.attributeValueId ||
                inp.value ||
                0
            );
            if (!id) return null;
            const text = (
                inp.closest("label")?.textContent ||
                inp.getAttribute("title") ||
                ""
            ).replace(/\s+/g, " ").trim();

            return { id, text, _radio: inp };
        }).filter(Boolean);

        if (options.length) blocks.push({ name, el, options });
    });

    // detectar color/talla por nombre
    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// === Ordena tallas (numéricas o estándar) ===
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a,b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase()), ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric:true });
    });
}

// === Escapar HTML simple ===
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// === Intentar encontrar una miniatura por color ===
function findThumbSrcForColor(colorOpt, page) {
    // 1) ¿hay imagen dentro del label del radio de color?
    const lbl = colorOpt._radio?.closest("label");
    const imgInLabel = lbl?.querySelector("img");
    if (imgInLabel?.src) return imgInLabel.src;

    // 2) ¿algún thumbnail/carrusel que mencione el color o sus ids?
    const colorTxt = (colorOpt.text || "").trim().toLowerCase();
    const thumbs = page.querySelectorAll("img, source");
    for (const t of thumbs) {
        const alt = (t.alt || t.title || t.getAttribute?.("data-alt") || "").toLowerCase();
        if (alt && colorTxt && alt.includes(colorTxt) && t.src) return t.src;
        const dataVals = t.getAttribute?.("data-attribute_value_ids") || "";
        if (dataVals && dataVals.split(",").map(x=>x.trim()).includes(String(colorOpt.id)) && t.src) {
            return t.src;
        }
    }

    // 3) fallback: imagen principal
    const mainImg = page.querySelector(".o_wsale_product_images img, .o_carousel_product img, .product_detail_img img");
    if (mainImg?.src) return mainImg.src;

    return ""; // se usa placeholder por CSS
}

// === Construir HTML de la matriz (solo UI) ===
function renderGrid(color, size, page) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        const thumb = findThumbSrcForColor(c, page);
        tbody += `<tr data-row-color="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="" ${thumb ? `src="${escapeHtml(thumb)}"` : ""}/>
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
        <div class="sp-actions">
            <button type="button" id="sp-add-selection" class="btn btn-primary o_add_to_cart">Añadir selección</button>
        </div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// === Insertar/actualizar la matriz ===
function ensureMatrix() {
    if (SP.rendering) return;
    SP.rendering = true;

    const page = document.querySelector(".o_wsale_product_page");
    if (!page) { SP.rendering = false; return; }

    // Eliminar cualquier matriz previa (evita duplicados)
    page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        document.body.classList.remove("sp-matrix-active");
        SP.rendering = false;
        return;
    }

    // Dónde colocarla: justo DESPUÉS de los atributos si existen
    const attrs = page.querySelector(".js_attributes");
    const host  = attrs || page.querySelector("form.o_wsale_product_configurator") || page;
    host.insertAdjacentHTML(attrs ? "afterend" : "beforeend", renderGrid(color, size, page));
    document.body.classList.add("sp-matrix-active");

    // Bind del botón "Añadir selección"
    const addBtn = page.querySelector("#sp-add-selection");
    if (addBtn) addBtn.addEventListener("click", () => addAllToCart(page));

    SP.rendering = false;

    // Enlazar una sola vez el listener de cambios de radios para reconstruir sin duplicar
    if (!SP.bound) {
        SP.bound = true;
        page.addEventListener("change", (ev) => {
            if (SP.rendering) return; // ignorar cambios internos
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    }
}

// === Helpers carrito ===
function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }

function getCsrfToken(page) {
    const inp = page.querySelector('input[name="csrf_token"]');
    if (inp?.value) return inp.value;
    const m = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
}

// Cambiar temporalmente selección de radios para obtener product_id actual
async function selectCombinationAndGetProductId(page, colorId, sizeId) {
    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) return null;

    // guardar selección actual
    const selectedColor = color.options.find(o => o._radio.checked);
    const selectedSize  = size.options.find(o => o._radio.checked);

    // seleccionar deseados
    const c = color.options.find(o => o.id === Number(colorId));
    const s = size.options.find(o => o.id === Number(sizeId));
    if (!c || !s) return null;

    c._radio.checked = true;
    c._radio.dispatchEvent(new Event("change", { bubbles: true }));
    s._radio.checked = true;
    s._radio.dispatchEvent(new Event("change", { bubbles: true }));

    // esperar a que Odoo actualice product_id
    await sleep(120);
    const pid = page.querySelector('input[name="product_id"]')?.value || null;

    // restaurar selección anterior (si la había)
    if (selectedColor && selectedColor._radio !== c._radio) {
        selectedColor._radio.checked = true;
        selectedColor._radio.dispatchEvent(new Event("change", { bubbles: true }));
    }
    if (selectedSize && selectedSize._radio !== s._radio) {
        selectedSize._radio.checked = true;
        selectedSize._radio.dispatchEvent(new Event("change", { bubbles: true }));
    }

    return pid ? Number(pid) : null;
}

async function addAllToCart(page) {
    const qtyInputs = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
    const lines = qtyInputs
        .map(i => ({ color: Number(i.dataset.color), size: Number(i.dataset.size), qty: Number(i.value || 0) }))
        .filter(l => l.qty > 0);

    if (!lines.length) return;

    const csrf = getCsrfToken(page);

    for (const line of lines) {
        const productId = await selectCombinationAndGetProductId(page, line.color, line.size);
        if (!productId) continue;

        await fetch("/shop/cart/update_json", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(csrf ? { "X-CSRFToken": csrf } : {}),
            },
            body: JSON.stringify({
                product_id: productId,
                add_qty: line.qty,
            }),
            credentials: "same-origin",
        }).catch(()=>{});
        // pequeña pausa para no saturar
        await sleep(120);
    }

    // refrescar mini carrito (si existe hook) o emitir evento
    const ev = new Event("sp:cart-updated");
    document.dispatchEvent(ev);
}

// === Arranque ===
onReady(ensureMatrix);