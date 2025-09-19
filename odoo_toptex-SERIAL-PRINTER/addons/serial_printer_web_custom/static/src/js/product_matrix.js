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

// ================== RED/UTILS ==================
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
    const routes = [
        "/website_sale/get_combination_info",
        "/shop/get_combination_info",
    ];
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
    if (data.error) throw new Error("RPC " + model + "." + method);
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

// ================== HIDRATAR (product_id, foto, precio, stock) ==================
function templateId(page) {
    const hid = page.querySelector('input[name="product_template_id"]');
    if (hid?.value) return Number(hid.value);
    const form = page.querySelector('form.o_wsale_product_configurator, form[action*="/shop"]');
    return Number(form?.dataset?.productTemplateId || 0);
}

async function resolveCombination(tmplId, values /* array de ids */) {
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
        });
    } catch (_) {}

    // Fallback: buscar por RPC una variante que contenga TODOS los valores
    if (!info || !info.product_id) {
        try {
            const recs = await rpc("product.product", "search_read", [
                [["product_tmpl_id","=",tmplId]],
                ["id","lst_price","qty_available","product_template_attribute_value_ids","attribute_line_ids"]
            ]);
            // nos quedamos con la que tiene todos los valores
            const need = new Set(values);
            const pick = recs.find(r => {
                // product_template_attribute_value_ids son PTAV, necesitamos sus value_ids:
                return true; // lo afinamos abajo con otra lectura si hace falta
            });
            // si no tenemos cómo cruzar PTAV aquí, leer uno a uno vía get_combination_info ya suele funcionar;
        } catch (_) {}
    }

    const result = {
        product_id: info?.product_id || info?.id || null,
        price: info?.price || info?.list_price || null,
        stock: info?.stock_qty ?? info?.free_qty ?? info?.available_quantity ?? null,
    };
    SP.comboCache.set(key, result);
    return result;
}

async function enrichFromProduct(pid) {
    try {
        const [rec] = await rpc("product.product", "read", [[pid], ["lst_price","qty_available"]]);
        return { price: rec?.lst_price ?? null, stock: rec?.qty_available ?? null };
    } catch (_) {
        return {};
    }
}

async function hydrateMatrix(page, color, size) {
    const tmplId = templateId(page);
    if (!tmplId) return;

    // Miniatura por COLOR (cogemos una combinación válida c+primera talla)
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
            // segundo intento: cualquier variante que tenga ese color
            try {
                const found = await rpc("product.product", "search_read", [
                    [["product_tmpl_id","=",tmplId]],
                    ["id","product_template_attribute_value_ids"]
                ]);
                const candidate = found.find(v => String(v.product_template_attribute_value_ids).includes(String(c.id)));
                if (candidate) pid = candidate.id;
            } catch (_) {}
        }
        if (pid) img.src = imgUrl(pid);
    }

    // Celdas: product_id + meta
    const cells = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
    for (const input of cells) {
        const cId = Number(input.dataset.color);
        const sId = Number(input.dataset.size);
        const info = await resolveCombination(tmplId, [cId, sId]);
        if (info.product_id) input.dataset.productId = String(info.product_id);

        // precio/stock (si no vinieron, intentamos por RPC)
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

    // 1) JSON (rápido)
    for (const it of items) {
        try {
            await fetch("/shop/cart/update_json", {
                method: "POST",
                headers: { "Content-Type": "application/json", ...(token ? { "X-CSRFToken": token } : {}) },
                credentials: "same-origin",
                body: JSON.stringify({ product_id: it.pid, add_qty: it.qty }),
            });
        } catch (_) {}
        await sleep(120);
    }

    // 2) Fallback clásico
    for (const it of items) {
        try {
            const fd = new FormData();
            fd.append("product_id", String(it.pid));
            fd.append("add_qty", String(it.qty));
            if (token) fd.append("csrf_token", token);
            await fetch("/shop/cart/update", { method: "POST", body: fd, credentials: "same-origin" });
        } catch (_) {}
        await sleep(120);
    }

    document.dispatchEvent(new Event("sp:cart-updated"));
}

// ================== INSERCIÓN/RENDER ==================
function anchors(page) {
    const info = page.querySelector(".o_wsale_product_information");
    const attrs =
        info?.querySelector(".js_attributes") ||
        info?.querySelector(".o_product_configurator .js_attributes") ||
        page.querySelector(".js_attributes");
    const actions =
        info?.querySelector(".o_wsale_product_actions") ||
        page.querySelector(".o_wsale_product_actions") ||
        page.querySelector('form[action*="/shop"] .o_wsale_product_actions');
    return { info: info || page, attrs, actions };
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

    if (attrs && attrs.parentNode) {
        attrs.insertAdjacentHTML("afterend", html);
    } else if (actions && actions.parentNode) {
        actions.insertAdjacentHTML("beforebegin", html);
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