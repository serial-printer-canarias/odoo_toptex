/** @odoo-module **/

// === DOM ready ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// Estado global mínimo
const SP = (window.__SP ||= { rendering: false, bound: false });
SP.comboCache = new Map(); // key: `${tmpl}|${ids.join('-')}` -> payload combo

// --- Utilidades de red ---
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
async function getCombinationInfo(payload) {
    try {
        return await postJson("/website_sale/get_combination_info", payload);
    } catch (_) {
        return await postJson("/shop/get_combination_info", payload);
    }
}
async function rpc(model, method, args = [], kwargs = {}) {
    const res = await fetch("/web/dataset/call_kw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: { model, method, args, kwargs, context: {} },
            id: Date.now(),
        }),
        credentials: "same-origin",
    });
    const data = await res.json();
    return data.result;
}

// --- Lectura de bloques de atributos (Color/Talla) ---
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
        )
            .trim()
            .toLowerCase();

        const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
        if (!radios.length) return;

        const options = radios
            .map((inp) => {
                const id = Number(
                    inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || 0
                );
                if (!id) return null;
                const text = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                    .replace(/\s+/g, " ")
                    .trim();
                return { id, text, _radio: inp };
            })
            .filter(Boolean);

        if (options.length) blocks.push({ name, el, options });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));
    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// --- Orden de tallas ---
function sortSizes(opts) {
    const std = [
        "2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL",
    ];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase()), ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// --- Helpers varios ---
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}
function getTemplateId(page) {
    const hid = page.querySelector('input[name="product_template_id"]');
    if (hid?.value) return Number(hid.value);
    const form = page.querySelector('form.o_wsale_product_configurator, form[action*="/shop"]');
    return Number(form?.dataset?.productTemplateId || 0);
}
function imgUrlForProduct(pid) {
    return `/web/image/product.product/${pid}/image_128`;
}
function getCsrfToken(page) {
    const inp = page.querySelector('input[name="csrf_token"]');
    if (inp?.value) return inp.value;
    const m = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// --- HTML matriz ---
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => (thead += `<th>${escapeHtml(s.text)}</th>`));
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
                    <div class="sp-meta"> </div>
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
            <button type="button" id="sp-add-selection" class="btn btn-primary">Añadir selección</button>
        </div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// --- Hidratar (product_id, imagen, precio, stock) ---
async function hydrateMatrix(page, color, size) {
    const tmplId = getTemplateId(page);
    if (!tmplId) return;

    // Miniatura por color usando (color + primera talla) SIN ordenar la combinación
    const firstSize = size.options[0]?.id;
    for (const c of color.options) {
        const combo = [c.id, firstSize].filter(Boolean); // NO ordenar
        const key = `${tmplId}|${combo.join("-")}`;
        let data = SP.comboCache.get(key);
        if (!data) {
            try {
                data = await getCombinationInfo({
                    product_template_id: tmplId,
                    combination: combo,
                    add_qty: 1,
                });
            } catch (_) {}
            if (data) SP.comboCache.set(key, data);
        }
        const imgEl = page.querySelector(`tr[data-row-color="${c.id}"] .sp-color__img`);
        const pid = data?.product_id || data?.id;
        const imageUrl =
            data?.image_url ||
            data?.variant_image_url ||
            data?.product_image ||
            (pid ? imgUrlForProduct(pid) : "");
        if (imgEl && imageUrl) imgEl.src = imageUrl;
    }

    // Celdas: resolvemos product_id y meta
    const cells = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
    for (const input of cells) {
        const cId = Number(input.dataset.color);
        const sId = Number(input.dataset.size);
        const combo = [cId, sId].filter(Boolean); // NO ordenar
        const key = `${tmplId}|${combo.join("-")}`;
        let data = SP.comboCache.get(key);
        if (!data) {
            try {
                data = await getCombinationInfo({
                    product_template_id: tmplId,
                    combination: combo,
                    add_qty: 1,
                });
            } catch (_) {}
            if (data) SP.comboCache.set(key, data);
        }
        const pid = data?.product_id || data?.id || null;
        if (pid) input.dataset.productId = String(pid);

        // Meta: precio/stock (si llega) o consultamos por RPC
        const meta = input.parentElement.querySelector(".sp-meta");
        let price = data?.price || data?.list_price || null;
        let stock = data?.stock_qty ?? data?.free_qty ?? data?.available_quantity ?? null;

        if ((!price || stock == null) && pid) {
            try {
                const [rec] = await rpc("product.product", "read", [[pid], ["lst_price", "qty_available"]]);
                price = price ?? rec?.lst_price;
                stock = stock ?? rec?.qty_available;
            } catch (_) { /* ignoramos si no hay permisos */ }
        }

        const parts = [];
        if (price != null) parts.push(`Precio: ${price}`);
        if (stock != null) parts.push(`Stock: ${stock}`);
        meta.textContent = parts.join(" · ");
    }
}

// --- Añadir selección ---
async function addAllToCart(page) {
    const rows = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"))
        .map((i) => ({ pid: Number(i.dataset.productId || 0), qty: Number(i.value || 0) }))
        .filter((x) => x.pid && x.qty > 0);

    if (!rows.length) return;

    const csrf = getCsrfToken(page);
    for (const r of rows) {
        await fetch("/shop/cart/update_json", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(csrf ? { "X-CSRFToken": csrf } : {}),
            },
            body: JSON.stringify({ product_id: r.pid, add_qty: r.qty }),
            credentials: "same-origin",
        }).catch(() => {});
        await wait(120);
    }
    document.dispatchEvent(new Event("sp:cart-updated"));
}

// --- Inserción estable y sin duplicados ---
async function ensureMatrix() {
    if (SP.rendering) return;
    SP.rendering = true;

    const page = document.querySelector(".o_wsale_product_page");
    if (!page) { SP.rendering = false; return; }

    // Elimina duplicados si los hubiera
    page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) { document.body.classList.remove("sp-matrix-active"); SP.rendering=false; return; }

    // Punto de inserción principal: justo debajo de los atributos
    const attrs =
        page.querySelector(".js_attributes") ||
        page.querySelector(".o_wsale_variants") ||
        page.querySelector(".o_product_configurator .js_attributes");

    // Fallback: antes del bloque de acciones (Add to cart), para no caer en "More information"
    const actions =
        page.querySelector(".o_wsale_product_information .o_wsale_product_actions") ||
        page.querySelector(".o_wsale_product_actions");

    const html = renderGrid(color, size);
    if (attrs && attrs.parentNode) {
        attrs.insertAdjacentHTML("afterend", html);
    } else if (actions && actions.parentNode) {
        actions.insertAdjacentHTML("beforebegin", html);
    } else {
        // último recurso: al inicio del contenido principal
        page.insertAdjacentHTML("afterbegin", html);
    }
    document.body.classList.add("sp-matrix-active");

    await hydrateMatrix(page, color, size);

    // Botón "Añadir selección"
    const addBtn = page.querySelector("#sp-add-selection");
    if (addBtn) addBtn.addEventListener("click", () => addAllToCart(page));

    // Re-construcción al cambiar radios (sin duplicar)
    if (!SP.bound) {
        SP.bound = true;
        page.addEventListener("change", (ev) => {
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    }

    SP.rendering = false;
}

// --- Arranque ---
onReady(ensureMatrix);