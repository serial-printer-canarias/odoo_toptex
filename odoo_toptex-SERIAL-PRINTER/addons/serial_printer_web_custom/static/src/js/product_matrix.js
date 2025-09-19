/** @odoo-module **/

// ================== DOM READY ==================
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// ================== ESTADO ==================
const SP = (window.__SP ||= {
    rendering: false,
    bound: false,
    comboCache: new Map(),   // key: tmpl|val-val  -> {product_id, price, stock}
});

// ================== UTILS ==================
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function csrf() {
    const m = document.cookie.match(/(?:^|;)\s*csrf_token=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : "";
}

async function postJSON(url, payload) {
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        credentials: "same-origin",
    });
    if (!res.ok) throw new Error(url + " -> HTTP " + res.status);
    return res.json();
}

async function getCombinationInfo(payload) {
    const routes = ["/shop/get_combination_info", "/website_sale/get_combination_info"];
    for (const r of routes) {
        try { return await postJSON(r, payload); } catch (_) {}
    }
    throw new Error("no-combination-route");
}

async function rpc(model, method, args = [], kwargs = {}) {
    const res = await fetch("/web/dataset/call_kw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
            jsonrpc: "2.0",
            method: "call",
            params: { model, method, args, kwargs, context: {} },
            id: Date.now(),
        }),
    });
    const data = await res.json();
    if (data?.error) throw new Error("RPC " + model + "." + method);
    return data.result;
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;",
    }[c]));
}
const imgUrl = (pid) => `/web/image/product.product/${pid}/image_128`;

// ================== ATRIBUTOS (COLOR/TALLA) ==================
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = Array.from(scope.querySelectorAll(
        '[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div'
    ));

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
                .replace(/\s+/g, " ").trim();
            return { id, text, _radio: inp };
        }).filter(Boolean);

        if (options.length) blocks.push({ name, el, options });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));
    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

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

// ================== HTML ==================
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => thead += `<th>${escapeHtml(s.text)}</th>`);
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        tbody += `<tr data-row-color="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="">
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
          <button id="sp-add-selection" type="button" class="btn btn-primary">Añadir selección</button>
        </div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// ================== DATOS (variante, foto, precio, stock) ==================
function templateId(page) {
    const hid = page.querySelector('input[name="product_template_id"]');
    if (hid?.value) return Number(hid.value);
    const form = page.querySelector('form.o_wsale_product_configurator, form[action*="/shop"]');
    return Number(form?.dataset?.productTemplateId || 0);
}

async function resolveCombination(tmplId, values /* array PTAV ids */) {
    const key = `${tmplId}|${values.slice().sort((a,b)=>a-b).join("-")}`;
    if (SP.comboCache.has(key)) return SP.comboCache.get(key);

    let info = null;
    try {
        info = await getCombinationInfo({
            product_template_id: tmplId,
            combination: values,
            add_qty: 1,
            only_template: false,
            parent_combination: [],
            no_variant_attribute_values: [],
        });
    } catch (_) {}

    let product_id = info?.product_id || info?.id || null;
    let price = info?.price ?? info?.list_price ?? null;
    let stock = info?.stock_qty ?? info?.free_qty ?? null;

    // Fallback robusto por RPC si aún no hay product_id
    if (!product_id) {
        try {
            const recs = await rpc("product.product", "search_read", [
                [["product_tmpl_id","=",tmplId]],
                ["id","lst_price","qty_available","product_template_attribute_value_ids"]
            ]);
            const need = new Set(values.map(Number));
            const pick = recs.find(r => {
                const got = (r.product_template_attribute_value_ids || []).map(Number);
                return [...need].every(v => got.includes(v));
            });
            if (pick) {
                product_id = pick.id;
                if (price == null) price = pick.lst_price ?? null;
                if (stock == null) stock = pick.qty_available ?? null;
            }
        } catch (_) {}
    }

    const result = { product_id, price, stock };
    SP.comboCache.set(key, result);
    return result;
}

async function enrichFromProduct(pid) {
    try {
        const [rec] = await rpc("product.product", "read", [[pid], ["lst_price","qty_available"]]);
        return { price: rec?.lst_price ?? null, stock: rec?.qty_available ?? null };
    } catch (_) { return {}; }
}

async function hydrateMatrix(page, color, size) {
    const tmplId = templateId(page);
    if (!tmplId) return;

    // Miniatura por COLOR (usando primera talla disponible)
    const firstSize = size.options[0]?.id;
    for (const c of color.options) {
        const row = page.querySelector(`tr[data-row-color="${c.id}"]`);
        const img = row?.querySelector(".sp-color__img");
        if (!img) continue;

        let combo = [c.id];
        if (firstSize) combo.push(firstSize);
        const info = await resolveCombination(tmplId, combo);
        let pid = info.product_id;

        if (!pid) {
            // último intento: cualquier variante que contenga ese color
            try {
                const recs = await rpc("product.product", "search_read", [
                    [["product_tmpl_id","=",tmplId]],
                    ["id","product_template_attribute_value_ids"]
                ]);
                const cand = recs.find(v => (v.product_template_attribute_value_ids||[]).map(Number).includes(Number(c.id)));
                if (cand) pid = cand.id;
            } catch (_) {}
        }

        if (pid) img.src = imgUrl(pid);
    }

    // Celdas: product_id + meta (precio/stock)
    const cells = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
    for (const input of cells) {
        const cId = Number(input.dataset.color);
        const sId = Number(input.dataset.size);
        const info = await resolveCombination(tmplId, [cId, sId]);
        if (info.product_id) input.dataset.productId = String(info.product_id);

        let price = info.price, stock = info.stock;
        if (info.product_id && (price == null || stock == null)) {
            const more = await enrichFromProduct(info.product_id);
            if (price == null) price = more.price ?? null;
            if (stock == null) stock = more.stock ?? null;
        }
        const meta = input.parentElement.querySelector(".sp-meta");
        const bits = [];
        if (price != null) bits.push(`Precio: ${price}`);
        if (stock != null) bits.push(`Stock: ${stock}`);
        meta.textContent = bits.join(" · ");
    }
}

// ================== AÑADIR AL CARRITO ==================
async function addSelection(page) {
    const items = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"))
        .map(i => ({ pid: Number(i.dataset.productId || 0), qty: Number(i.value || 0) }))
        .filter(x => x.pid && x.qty > 0);

    if (!items.length) return;

    const token = csrf();

    // JSON
    for (const it of items) {
        try {
            await fetch("/shop/cart/update_json", {
                method: "POST",
                headers: { "Content-Type": "application/json", ...(token ? { "X-CSRFToken": token } : {}) },
                credentials: "same-origin",
                body: JSON.stringify({ product_id: it.pid, add_qty: it.qty }),
            });
        } catch (_) {}
        await sleep(100);
    }
    // Fallback clásico
    for (const it of items) {
        try {
            const fd = new FormData();
            fd.append("product_id", String(it.pid));
            fd.append("add_qty", String(it.qty));
            if (token) fd.append("csrf_token", token);
            await fetch("/shop/cart/update", { method: "POST", body: fd, credentials: "same-origin" });
        } catch (_) {}
        await sleep(100);
    }

    document.dispatchEvent(new Event("sp:cart-updated"));
}

// ================== INSERCIÓN/RENDER ==================
function anchors(page) {
    const info = page.querySelector(".o_wsale_product_information") || page;
    const attrs  = info.querySelector(".js_attributes");
    const form   = info.querySelector("form.o_wsale_product_configurator, form[action*=\"/shop\"]") || page.querySelector("form[action*=\"/shop\"]");
    const actions = info.querySelector(".o_wsale_product_actions") || form?.querySelector(".o_wsale_product_actions");
    return { info, attrs, actions };
}

async function ensureMatrix() {
    if (SP.rendering) return;
    SP.rendering = true;

    const page = document.querySelector(".o_wsale_product_page");
    if (!page) { SP.rendering = false; return; }

    // borra duplicados
    page.querySelectorAll("#sp-matrix").forEach(n => n.remove());

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) { document.body.classList.remove("sp-matrix-active"); SP.rendering = false; return; }

    const html = renderGrid(color, size);
    const { info, attrs, actions } = anchors(page);

    // **Posición fija: SIEMPRE antes del Add to cart**
    if (actions && actions.parentNode) {
        actions.insertAdjacentHTML("beforebegin", html);
    } else if (attrs && attrs.parentNode) {
        attrs.insertAdjacentHTML("afterend", html);
    } else {
        info.insertAdjacentHTML("beforeend", html);
    }
    document.body.classList.add("sp-matrix-active");

    await hydrateMatrix(page, color, size);

    const btn = page.querySelector("#sp-add-selection");
    if (btn) btn.addEventListener("click", () => addSelection(page));

    if (!SP.bound) {
        SP.bound = true;
        page.addEventListener("change", (ev) => {
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    }
    SP.rendering = false;
}

// ================== START ==================
onReady(ensureMatrix);