/** @odoo-module **/

// ===== Utilidad: ejecutar cuando el DOM está listo =====
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// Utilidades DOM
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

// ===== Datos base =====
function getProductTemplateId() {
    const a = $('input[name="product_template_id"]');
    if (a && a.value) return parseInt(a.value, 10) || null;
    const b = $('.o_wsale_product_page [data-product-template-id]');
    if (b && b.dataset.productTemplateId) return parseInt(b.dataset.productTemplateId, 10) || null;
    return null;
}

// ===== Lectura de atributos (Color / Talla) desde el HTML de Odoo =====
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = $$('[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div', scope);

    containers.forEach((el) => {
        const name = (
            el.getAttribute("data-attribute_name") ||
            el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
            el.getAttribute("name") ||
            ""
        ).trim().toLowerCase();

        const radios = $$('input[type="radio"]', el);
        if (!radios.length) return;

        const options = radios.map((inp) => {
            const id = parseInt(
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                10
            ) || 0;

            const txt = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                .replace(/\s+/g, " ").trim();

            return id ? { id, text: txt } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// ===== Ordenación de tallas (númericas y estándar) =====
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase()), ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// ===== Render de la tabla (solo UI) =====
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
        <div class="sp-actions">
          <button type="button" class="sp-add-selection o_wsale_apply btn btn-primary">Añadir selección</button>
        </div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// ===== RPC helper contra rutas estándar de Odoo =====
async function rpc(url, payload) {
    const resp = await fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(payload || {}),
        credentials: "same-origin",
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
}

// ===== Poblar miniaturas por color (variante) =====
async function populateColorImages(color) {
    const ptId = getProductTemplateId();
    if (!ptId || !color) return;

    for (const c of color.options) {
        const tr = document.querySelector(`#sp-matrix tr[data-color-id="${c.id}"]`);
        const img = tr?.querySelector("img.sp-color__img");
        if (!img) continue;

        try {
            // Normalmente basta con pasar solo el color: Odoo resolverá una combinación válida
            const info = await rpc("/website_sale/get_combination_info", {
                product_template_id: ptId,
                combination: [c.id],
                add_qty: 1,
            });

            // Campos típicos según versión/tema:
            const url = info?.image_url || info?.display_image || info?.variant_image || null;
            if (url) img.src = url;
            else {
                // Fallback: usa la imagen principal si no hay específica
                const main = $(".o_wsale_product_img img, .product_detail_img img, .carousel img");
                if (main?.src) img.src = main.src;
            }
        } catch (e) {
            console.warn("[SP] imagen variante color", c.id, e);
        }
    }
}

// ===== Precio/stock por celda al enfocar =====
function wireMetaOnFocus() {
    const ptId = getProductTemplateId();
    if (!ptId) return;
    $$("#sp-matrix input.sp-qty").forEach((inp) => {
        inp.addEventListener("focus", async () => {
            const colorId = parseInt(inp.dataset.color, 10);
            const sizeId  = parseInt(inp.dataset.size, 10);
            const meta = inp.closest(".sp-cell").querySelector(".sp-meta");
            meta.textContent = "…";
            try {
                const info = await rpc("/website_sale/get_combination_info", {
                    product_template_id: ptId,
                    combination: [colorId, sizeId],
                    add_qty: 1,
                });
                // Mostramos lo que devuelva cada instalación (html/strings)
                const priceHtml = info?.price_html || (info?.price ? `${info.price}` : "");
                const stockHtml = info?.stock_availability || info?.availability || "";
                meta.innerHTML = [priceHtml, stockHtml].filter(Boolean).join(" · ");
            } catch (e) {
                meta.textContent = "";
                console.warn("[SP] meta precio/stock", e);
            }
        });
    });
}

// ===== Añadir selección (varias líneas) al carrito real =====
function wireAddSelection() {
    const btn = $("#sp-matrix .sp-add-selection");
    if (!btn) return;

    btn.addEventListener("click", async () => {
        const ptId = getProductTemplateId();
        if (!ptId) return;

        const cells = $$("#sp-matrix input.sp-qty");
        const tasks = [];
        for (const inp of cells) {
            const qty = parseInt(inp.value, 10) || 0;
            if (qty <= 0) continue;
            const colorId = parseInt(inp.dataset.color, 10);
            const sizeId  = parseInt(inp.dataset.size, 10);

            // 1) resolvemos el product_id exacto de la combinación
            tasks.push((async () => {
                try {
                    const info = await rpc("/website_sale/get_combination_info", {
                        product_template_id: ptId,
                        combination: [colorId, sizeId],
                        add_qty: qty,
                    });
                    const product_id = info?.product_id;
                    if (!product_id) return;

                    // 2) añadimos al carrito
                    await rpc("/shop/cart/update_json", {
                        product_id,
                        add_qty: qty,
                        display: true,
                    });
                } catch (e) {
                    console.warn("[SP] add to cart", colorId, sizeId, e);
                }
            })());
        }

        await Promise.all(tasks);
        // Refrescamos mini resumen/total
        window.location.reload();
    });
}

// ===== Inserta/actualiza la matriz, siempre debajo de los atributos =====
function ensureMatrix() {
    const page = $(".o_wsale_product_page");
    if (!page) return;

    // El host deseado: bloque de atributos
    const attrBlock = $(".js_attributes", page);
    if (!attrBlock) {
        // Si no hay atributos, ocultamos matriz
        const existing = $("#sp-matrix");
        if (existing) existing.remove();
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    // Evitar duplicados
    const existing = $("#sp-matrix");
    if (existing) existing.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    // Insertar justo después del bloque de atributos
    attrBlock.insertAdjacentHTML("afterend", renderGrid(color, size));
    document.body.classList.add("sp-matrix-active");

    // Poblar imágenes y wiring
    populateColorImages(color);
    wireMetaOnFocus();
    wireAddSelection();
    console.log("[SP] product_matrix.js cargado");
}

// ===== Arranque =====
onReady(() => {
    ensureMatrix();

    // Si cambian radios, reconstruimos (sin duplicar)
    const page = $(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});