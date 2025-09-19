/** @odoo-module **/

// ============ Utilidad: DOM listo ============
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// ============ Bloques de atributos (Color / Talla) ============
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
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                10
            ) || 0;
            const txt = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                .replace(/\s+/g, " ").trim();
            return id ? { id, text: txt, _radio: inp } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options, _el: el });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b)  => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// ============ Ordena tallas ============
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

// ============ Render tabla (UI) ============
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
        <div class="sp-actions"><button type="button" id="sp-add-selected" class="btn btn-primary">
            Añadir selección
        </button></div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// ============ Posicionamiento / ancla ============
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

// ============ Miniaturas por color (placeholder si no hay) ============
function getColorThumbSrc(page, colorId) {
    const radio = page.querySelector(
        `input[type="radio"][data-value-id="${colorId}"], input[type="radio"][data-attribute-value-id="${colorId}"]`
    );
    const lbl = radio ? (radio.closest("label") || page.querySelector(`label[for="${radio?.id}"]`)) : null;
    const img = lbl?.querySelector("img");
    if (img?.src) return img.src;

    const bgHost = lbl?.querySelector('[style*="background-image"]') || lbl;
    if (bgHost?.style?.backgroundImage && bgHost.style.backgroundImage !== "none") {
        const url = bgHost.style.backgroundImage.slice(4, -1).replace(/["']/g, "");
        if (url) return url;
    }
    // Placeholder/imagen del atributo (si existe) — si no, Odoo devuelve placeholder
    return `/web/image/product.attribute.value/${colorId}/image_1920/64x64`;
}
function fillColorThumbs(page, color) {
    color.options.forEach((c) => {
        const img = page.querySelector(`#sp-matrix tr[data-color-id="${c.id}"] img.sp-color__img`);
        if (img) {
            img.src = getColorThumbSrc(page, c.id);
            img.loading = "lazy";
            img.decoding = "async";
        }
    });
}

// ============ Helpers: PT id / Pricelist / CSRF / JSON-RPC ============
function getProductTemplateId(page) {
    return (
        page.querySelector('form.o_wsale_product_configurator')?.dataset.productTemplateId ||
        page.querySelector('input[name="product_template_id"]')?.value ||
        page.querySelector('[data-oe-model="product.template"]')?.getAttribute('data-oe-id') ||
        null
    );
}
function getPricelistId(page) {
    return (
        page.querySelector('input[name="pricelist_id"]')?.value ||
        document.body.dataset.pricelistId ||
        null
    );
}
function getCsrfToken() {
    return document.querySelector('input[name="csrf_token"]')?.value || null;
}
async function jsonRpc(url, params) {
    const body = { jsonrpc: "2.0", method: "call", params };
    const res  = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        credentials: "same-origin",
    });
    const data = await res.json().catch(() => ({}));
    if (data && Object.prototype.hasOwnProperty.call(data, "result")) return data.result;
    throw new Error(`RPC error: ${url}`);
}

// ============ Combination info (precio/stock/product_id) ============
async function getCombinationInfo(page, ptId, combination) {
    const payload = {
        product_template_id: parseInt(ptId, 10),
        combination: combination,          // lista de ids de atributos (color, talla)
        add_qty: 1,
        pricelist_id: getPricelistId(page),
    };
    try {
        return await jsonRpc("/shop/get_combination_info", payload);
    } catch (e) {
        // fallback (algunas builds nuevas)
        return await jsonRpc("/sale/get_combination_info", payload);
    }
}

// ============ Add to cart (múltiples) ============
async function addToCart(productId, qty, ptId, combination) {
    const params = {
        product_id: productId,
        add_qty: qty,
        combination: combination,
        product_template_id: parseInt(ptId, 10),
        csrf_token: getCsrfToken(),
    };
    return jsonRpc("/shop/cart/update_json", params);
}

// ============ Pintar/actualizar matriz ============
let _debounceTimer = null;
function ensureMatrix() {
    if (window.__sp_building) return;
    window.__sp_building = true;
    try {
        const page = document.querySelector(".o_wsale_product_page");
        if (!page) return;

        // Evita duplicados de matriz
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

        // Miniaturas (placeholder si no hay imagen del atributo)
        fillColorThumbs(page, color);

        // Lazy precio/stock al enfocar una celda
        const ptId = getProductTemplateId(page);
        page.querySelectorAll("#sp-matrix input.sp-qty").forEach((inp) => {
            inp.addEventListener("focus", async () => {
                const td   = inp.closest("td");
                const meta = td.querySelector(".sp-meta");
                if (meta.dataset.loaded) return;
                const colorId = parseInt(inp.dataset.color, 10);
                const sizeId  = parseInt(inp.dataset.size, 10);
                try {
                    const info = await getCombinationInfo(page, ptId, [colorId, sizeId]);
                    td.dataset.productId = info.product_id || "";
                    meta.innerHTML = [
                        info.price ? (`${info.price.toFixed ? info.price.toFixed(2) : info.price}`) : "",
                        (info.product_qty || info.virtual_available || info.qty_available) ? 
                            `Stock: ${info.product_qty ?? info.virtual_available ?? info.qty_available}` : ""
                    ].filter(Boolean).join(" · ");
                    meta.dataset.loaded = "1";
                } catch {
                    meta.innerHTML = "";
                }
            });
        });

        // Botón "Añadir selección"
        page.querySelector("#sp-add-selected")?.addEventListener("click", async () => {
            const ptId2 = getProductTemplateId(page);
            const inputs = Array.from(page.querySelectorAll("#sp-matrix input.sp-qty"))
                .map((i) => ({ el: i, q: parseInt(i.value || "0", 10) || 0 }))
                .filter((x) => x.q > 0);

            if (!inputs.length) return;

            for (const { el, q } of inputs) {
                const colorId = parseInt(el.dataset.color, 10);
                const sizeId  = parseInt(el.dataset.size, 10);
                try {
                    // Aseguramos product_id con la combinación
                    const info = await getCombinationInfo(page, ptId2, [colorId, sizeId]);
                    const pid  = info.product_id;
                    if (pid) {
                        await addToCart(pid, q, ptId2, [colorId, sizeId]);
                        el.value = ""; // limpiar después de añadir
                    }
                } catch (e) {
                    // si falla una combinación, seguimos con el resto
                    // (no mostramos alertas para no molestar al usuario)
                    console.warn("[SP] addToCart fallo combinación", colorId, sizeId, e);
                }
            }
            // Refrescar mini carrito si existe
            document.querySelector(".js_cart")?.dispatchEvent(new Event("click", { bubbles: true }));
        });

    } finally {
        window.__sp_building = false;
    }
}

// ============ Arranque ============
onReady(() => {
    ensureMatrix();

    // Reconstruir si cambian radios (evita duplicados porque siempre borramos antes)
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (!ev.target.matches('input[type="radio"]')) return;
        clearTimeout(_debounceTimer);
        _debounceTimer = setTimeout(() => ensureMatrix(), 60);
    });
});