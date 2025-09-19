/** @odoo-module **/

// ===== DOM ready =====
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// ===== Estado mínimo global =====
const SP = (window.__SP ||= { rendering: false, bound: false, comboCache: new Map() });

// ===== helpers de red =====
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
    // intentamos varias rutas conocidas de Odoo
    const routes = [
        "/website_sale/get_combination_info",
        "/shop/get_combination_info",
        "/shop/get_combination_info_variant",
    ];
    for (const r of routes) {
        try { return await postJson(r, payload); } catch (_) {}
    }
    throw new Error("No combination route");
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
function getCsrfToken() {
    const m = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
}
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// ===== lectura de bloques de atributos (Color/Talla) =====
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

// ===== orden de tallas =====
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase()), ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// ===== helpers varios =====
function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;",
    }[c]));
}
function getTemplateId(page) {
    const hid = page.querySelector('input[name="product_template_id"]');
    if (hid?.value) return Number(hid.value);
    const form = page.querySelector('form.o_wsale_product_configurator, form[action*="/shop"]');
    return Number(form?.dataset?.productTemplateId || 0);
}
const imgUrlForProduct = (pid) => `/web/image/product.product/${pid}/image_128`;

// ===== HTML de la matriz =====
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => thead += `<th>${escapeHtml(s.text)}</th>`);
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
            <button type="button" id="sp-add-selection" class="btn btn-primary">Añadir selección</button>
        </div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// ===== hidratar (product_id, imagen, precio, stock) =====
async function hydrateMatrix(page, color, size) {
    const tmplId = getTemplateId(page);
    if (!tmplId) return;

    // miniaturas por color: color + primera talla si existe (NO reordenamos ids)
    const firstSize = size.options[0]?.id;
    for (const c of color.options) {
        const combo = [c.id, firstSize].filter(Boolean);
        const key = `${tmplId}|${combo.join("-")}`;
        let data = SP.comboCache.get(key);
        if (!data) {
            try {
                data = await getCombinationInfo({ product_template_id: tmplId, combination: combo, add_qty: 1 });
            } catch (_) {}
            if (data) SP.comboCache.set(key, data);
        }
        const pid = data?.product_id || data?.id;
        const img = page.querySelector(`tr[data-row-color="${c.id}"] .sp-color__img`);
        if (img && pid) img.src = imgUrlForProduct(pid);
    }

    // celdas
    const cells = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
    for (const input of cells) {
        const cId = Number(input.dataset.color);
        const sId = Number(input.dataset.size);
        const combo = [cId, sId].filter(Boolean);
        const key = `${tmplId}|${combo.join("-")}`;
        let data = SP.comboCache.get(key);
        if (!data) {
            try {
                data = await getCombinationInfo({ product_template_id: tmplId, combination: combo, add_qty: 1 });
            } catch (_) {}
            if (data) SP.comboCache.set(key, data);
        }
        const pid = data?.product_id || data?.id || null;
        if (pid) input.dataset.productId = String(pid);

        const meta = input.parentElement.querySelector(".sp-meta");
        let price = data?.price || data?.list_price || null;
        let stock = data?.stock_qty ?? data?.free_qty ?? data?.available_quantity ?? null;

        if ((!price || stock == null) && pid) {
            try {
                const [rec] = await rpc("product.product", "read", [[pid], ["lst_price","qty_available"]]);
                price = price ?? rec?.lst_price;
                stock = stock ?? rec?.qty_available;
            } catch (_) {}
        }
        const parts = [];
        if (price != null) parts.push(`Precio: ${price}`);
        if (stock != null) parts.push(`Stock: ${stock}`);
        meta.textContent = parts.join(" · ");
    }
}

// ===== añadir selección =====
async function addAllToCart(page) {
    const rows = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"))
        .map((i) => ({ pid: Number(i.dataset.productId || 0), qty: Number(i.value || 0) }))
        .filter((x) => x.pid && x.qty > 0);
    if (!rows.length) return;

    const csrf = getCsrfToken();

    // 1º intento: JSON
    for (const r of rows) {
        try {
            await fetch("/shop/cart/update_json", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(csrf ? { "X-CSRFToken": csrf } : {}),
                },
                body: JSON.stringify({ product_id: r.pid, add_qty: r.qty }),
                credentials: "same-origin",
            });
        } catch (_) {}
        await wait(120);
    }

    // Verificación rápida: si el carrito no subió, intentamos formulario clásico
    // (no bloquea si ya entraron)
    for (const r of rows) {
        try {
            const fd = new FormData();
            fd.append("product_id", String(r.pid));
            fd.append("add_qty", String(r.qty));
            if (csrf) fd.append("csrf_token", csrf);
            await fetch("/shop/cart/update", {
                method: "POST",
                body: fd,
                credentials: "same-origin",
                redirect: "manual",
            });
        } catch (_) {}
        await wait(120);
    }

    document.dispatchEvent(new Event("sp:cart-updated"));
}

// ===== inserción estable y sin duplicados =====
async function ensureMatrix() {
    if (SP.rendering) return;
    SP.rendering = true;

    const page = document.querySelector(".o_wsale_product_page");
    if (!page) { SP.rendering = false; return; }

    // limpiar duplicados
    page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) { document.body.classList.remove("sp-matrix-active"); SP.rendering=false; return; }

    const html = renderGrid(color, size);

    // puntos de anclaje (de más específico a más genérico)
    const attrs =
        page.querySelector(".o_wsale_product_information .js_attributes") ||
        page.querySelector(".o_wsale_product_information .o_product_configurator .js_attributes") ||
        page.querySelector(".o_wsale_product_information .o_product_configurator") ||
        page.querySelector(".js_attributes");

    const actions =
        page.querySelector(".o_wsale_product_information .o_wsale_product_actions") ||
        page.querySelector(".o_wsale_product_actions") ||
        page.querySelector('form[action*="/shop"] .o_wsale_product_actions');

    if (attrs && attrs.parentNode) {
        attrs.insertAdjacentHTML("afterend", html);
    } else if (actions && actions.parentNode) {
        actions.insertAdjacentHTML("beforebegin", html);
    } else {
        // como último recurso la ponemos al final del contenedor de información (columna derecha)
        const info = page.querySelector(".o_wsale_product_information") || page;
        info.insertAdjacentHTML("beforeend", html);
    }
    document.body.classList.add("sp-matrix-active");

    await hydrateMatrix(page, color, size);

    const addBtn = page.querySelector("#sp-add-selection");
    if (addBtn) addBtn.addEventListener("click", () => addAllToCart(page));

    if (!SP.bound) {
        SP.bound = true;
        page.addEventListener("change", (ev) => {
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    }
    SP.rendering = false;
}

// ===== arranque =====
onReady(ensureMatrix);