/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// Estado y cachés simples
const SP = (window.__SP ||= { rendering: false, bound: false });
SP.comboCache = new Map(); // key: `${tmpl}|${ids.join('-')}` -> {product_id, image_url, price, stock}

// ==== Helpers de red / endpoints ====
async function postJson(url, payload) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        credentials: "same-origin",
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
}

// Intenta /website_sale/get_combination_info y si no existe, /shop/get_combination_info
async function getCombinationInfo(payload) {
    try {
        return await postJson("/website_sale/get_combination_info", payload);
    } catch (_) {
        return await postJson("/shop/get_combination_info", payload);
    }
}

// === Buscar bloques de atributos (Color/Talla) ===
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = Array.from(
        scope.querySelectorAll('[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div')
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
            const id = Number(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || 0);
            if (!id) return null;
            const text = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                .replace(/\s+/g, " ")
                .trim();
            return { id, text, _radio: inp };
        }).filter(Boolean);

        if (options.length) blocks.push({ name, el, options });
    });

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

// === ID de plantilla ===
function getTemplateId(page) {
    const hid = page.querySelector('input[name="product_template_id"]');
    if (hid?.value) return Number(hid.value);
    // fallback leve (por si la vista cambia)
    const form = page.querySelector('form[action*="/shop"]');
    return Number(form?.dataset?.productTemplateId || 0);
}

// === Construir HTML de la matriz ===
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        tbody += `<tr data-row-color="${c.id}">
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
                    <div class="sp-meta">—</div>
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

// === Hidratar celdas con product_id + miniaturas/price/stock ===
async function hydrateMatrix(page, color, size) {
    const tmplId = getTemplateId(page);
    if (!tmplId) return;

    const cells = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
    const firstSize = size.options[0]?.id;

    // miniaturas por fila (color)
    for (const c of color.options) {
        // intentar cachear a partir de combinación [color + primera talla]
        const comboIds = [c.id, firstSize].filter(Boolean).map(Number).sort((a,b)=>a-b);
        const key = `${tmplId}|${comboIds.join("-")}`;

        let data = SP.comboCache.get(key);
        if (!data) {
            try {
                data = await getCombinationInfo({
                    product_template_id: tmplId,
                    combination: comboIds,
                    add_qty: 1,
                });
            } catch (_) { data = null; }
            if (data) SP.comboCache.set(key, data);
        }

        const img = page.querySelector(`tr[data-row-color="${c.id}"] .sp-color__img`);
        const imageUrl =
            data?.image_url ||
            data?.variant_image_url ||
            data?.product_image ||
            data?.product_variant?.image_url ||
            "";
        if (img && imageUrl) img.src = imageUrl;
    }

    // hidratar cada celda
    for (const input of cells) {
        const colorId = Number(input.dataset.color);
        const sizeId  = Number(input.dataset.size);
        const comboIds = [colorId, sizeId].filter(Boolean).map(Number).sort((a,b)=>a-b);
        const key = `${tmplId}|${comboIds.join("-")}`;

        let data = SP.comboCache.get(key);
        if (!data) {
            try {
                data = await getCombinationInfo({
                    product_template_id: tmplId,
                    combination: comboIds,
                    add_qty: 1,
                });
            } catch (_) { data = null; }
            if (data) SP.comboCache.set(key, data);
        }

        const pid = data?.product_id || data?.id || null;
        if (pid) input.dataset.productId = String(pid);

        const meta = input.parentElement?.querySelector(".sp-meta");
        if (meta) {
            const price = data?.price || data?.list_price || data?.price_unit;
            const stock = data?.stock_qty ?? data?.free_qty ?? data?.available_quantity;
            let txt = "";
            if (price != null) txt += `Precio: ${price}`;
            if (stock != null) txt += (txt ? " · " : "") + `Stock: ${stock}`;
            meta.textContent = txt || "";
        }
    }
}

// === Añadir selección al carrito ===
function getCsrfToken(page) {
    const inp = page.querySelector('input[name="csrf_token"]');
    if (inp?.value) return inp.value;
    const m = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
}
function sleep(ms){ return new Promise(r=>setTimeout(r, ms)); }

async function addAllToCart(page) {
    const items = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"))
        .map(i => ({
            pid: Number(i.dataset.productId || 0),
            qty: Number(i.value || 0),
        }))
        .filter(x => x.qty > 0);

    if (!items.length) return;

    const csrf = getCsrfToken(page);
    for (const it of items) {
        if (!it.pid) continue;
        await fetch("/shop/cart/update_json", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(csrf ? { "X-CSRFToken": csrf } : {}),
            },
            body: JSON.stringify({ product_id: it.pid, add_qty: it.qty }),
            credentials: "same-origin",
        }).catch(()=>{});
        await sleep(120);
    }
    document.dispatchEvent(new Event("sp:cart-updated"));
}

// === Insertar/actualizar matriz (posición estable) ===
async function ensureMatrix() {
    if (SP.rendering) return;
    SP.rendering = true;

    const page = document.querySelector(".o_wsale_product_page");
    if (!page) { SP.rendering = false; return; }

    // limpiar duplicados
    page.querySelectorAll("#sp-matrix").forEach(n => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) { document.body.classList.remove("sp-matrix-active"); SP.rendering=false; return; }

    // insertar SIEMPRE justo debajo de los atributos
    const attrs = page.querySelector(".js_attributes");
    const anchor = attrs || page.querySelector("form.o_wsale_product_configurator") || page;
    anchor.insertAdjacentHTML("afterend", renderGrid(color, size));
    document.body.classList.add("sp-matrix-active");

    // hidratar (product_id, miniaturas, precios…)
    await hydrateMatrix(page, color, size);

    // botón
    const addBtn = page.querySelector("#sp-add-selection");
    if (addBtn) addBtn.addEventListener("click", () => addAllToCart(page));

    // reconstruir al cambiar un radio, sin duplicar (quitamos, insertamos, re-hidratar)
    if (!SP.bound) {
        SP.bound = true;
        page.addEventListener("change", (ev) => {
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    }

    SP.rendering = false;
}

// === Arranque ===
onReady(ensureMatrix);