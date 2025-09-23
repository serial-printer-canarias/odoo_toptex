/**  Serial Printer – Product Matrix (Odoo 18, ES modules sin rpc_service)
 *   Grid Color × Talla con foto, precio y stock + botón "Añadir selección".
 */

import publicWidget from "@web/legacy/js/public/public_widget";

const Q  = (root, sel) => root.querySelector(sel);
const QA = (root, sel) => Array.from(root.querySelectorAll(sel));

/* ---------------- JSON-RPC sin dependencias ---------------- */
async function rpc(route, params) {
    const payload = { jsonrpc: "2.0", method: "call", params };
    const headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    };
    // CSRF si está disponible (website suele tenerlo)
    if (window.odoo?.csrf_token) headers["X-CSRFToken"] = window.odoo.csrf_token;

    const res = await fetch(route, {
        method: "POST",
        credentials: "same-origin",
        headers,
        body: JSON.stringify(payload),
    });

    let data = null;
    try { data = await res.json(); } catch (_) {}
    if (!res.ok || !data) throw new Error(`RPC ${route} failed`);
    if (data.error) throw new Error(data.error.message || `RPC ${route} error`);
    return data.result;
}

async function getCombinationInfo(args) {
    try {
        return await rpc("/shop/get_combination_info", args);
    } catch (_) {
        try {
            return await rpc("/sale/get_combination_info", args);
        } catch (__) {
            return null;
        }
    }
}

async function readStock(variantId) {
    try {
        const r = await rpc("/web/dataset/call_kw", {
            model: "product.product",
            method: "read",
            args: [[variantId], ["qty_available"]],
            kwargs: {},
        });
        return (r && r[0] && typeof r[0].qty_available === "number") ? r[0].qty_available : null;
    } catch {
        return null;
    }
}

function fmtPrice(v) {
    try {
        const lang = document.documentElement.lang || "es-ES";
        const curr = document.querySelector("[data-website-currency-code]")?.dataset.websiteCurrencyCode || "EUR";
        return new Intl.NumberFormat(lang, { style: "currency", currency: curr }).format(v);
    } catch {
        return (Math.round(v * 100) / 100).toFixed(2);
    }
}

function detectBlocks($page) {
    const blocks = [];
    QA($page, ".js_product .js_attributes [data-attribute_name]").forEach((el) => {
        const name = (el.getAttribute("data-attribute_name") || "").trim();
        const options = [];
        QA(el, "input[type='radio']").forEach((inp) => {
            const id = parseInt(
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0", 10
            ) || 0;
            const label = (inp.closest("label")?.textContent || inp.title || "").trim();
            if (id) options.push({ id, name: label });
        });
        if (options.length) blocks.push({ name, options, el });
    });
    return blocks;
}

function pickColorSize(blocks) {
    const isColor = (n) => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || "");
    const isSize  = (n) => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || "");
    let color = blocks.find((b) => isColor(b.name));
    let size  = blocks.find((b) => isSize(b.name));
    if (!color && blocks.length) color = blocks[0];
    if (!size && blocks.length > 1) size = blocks[1];
    return { color, size };
}

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page",
    disabledInEditableMode: false,

    start() {
        if (Q(this.el, "#sp-matrix")) return this._super(...arguments); // evitar duplicados
        this._buildIfPossible();
        return this._super(...arguments);
    },

    async _buildIfPossible() {
        const page = this.el;
        const blocks = detectBlocks(page);
        if (!blocks.length) return;

        const { color, size } = pickColorSize(blocks);
        if (!color) return;

        // Anchor: debajo del precio; si no existe, debajo de la info del producto o al final
        const anchor =
            Q(page, ".product_price") ||
            Q(page, ".o_wsale_product_information") ||
            Q(page, ".js_product") ||
            page;

        const matrix = document.createElement("div");
        matrix.id = "sp-matrix";
        matrix.className = "sp-matrix o-pt-3 o-mt-2";
        anchor.parentNode.insertBefore(matrix, anchor.nextSibling);

        const table = document.createElement("table");
        table.className = "sp-matrix__table";
        const thead = document.createElement("thead");
        const trh = document.createElement("tr");
        const thLeft = document.createElement("th");
        thLeft.className = "sp-sticky-left";
        thLeft.textContent = "Color";
        trh.appendChild(thLeft);

        const columns = size ? size.options : [{ id: 0, name: "Qty" }];
        columns.forEach((o) => {
            const th = document.createElement("th");
            th.textContent = o.name || "Qty";
            trh.appendChild(th);
        });
        thead.appendChild(trh);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");

        for (const c of color.options) {
            const tr = document.createElement("tr");
            tr.dataset.colorId = String(c.id);

            const th = document.createElement("th");
            th.className = "sp-sticky-left";
            th.innerHTML = `
                <div class="sp-color">
                  <img class="sp-color__img" alt="">
                  <span class="sp-color__name">${_.escape(c.name)}</span>
                </div>`;
            tr.appendChild(th);

            for (const s of columns) {
                const td = document.createElement("td");
                td.dataset.sizeId = String(s.id);
                td.innerHTML = `
                  <div class="sp-cell">
                    <input type="number" min="0" step="1"
                           class="sp-qty"
                           data-color-id="${c.id}"
                           data-size-id="${s.id}">
                    <div class="sp-meta">
                      <span class="sp-price"></span>
                      <span class="sp-stock"></span>
                    </div>
                  </div>`;
                tr.appendChild(td);
            }
            tbody.appendChild(tr);
        }

        table.appendChild(tbody);
        matrix.appendChild(table);

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-primary mt-2 sp-add-to-cart";
        btn.textContent = "Añadir selección";
        btn.addEventListener("click", (ev) => this._onAddAllToCart(ev));
        matrix.appendChild(btn);

        await this._hydrateCells(matrix);
    },

    _comboArgs(avIds) {
        // Varias formas de encontrar el template id según tema
        const candidates = [
            "[data-product-template-id]",
            ".js_product[data-product-template-id]",
            "input[name='product_template_id']",
        ];
        let tmplId = 0;
        for (const sel of candidates) {
            const el = Q(this.el, sel);
            if (el) {
                const v = el.dataset?.productTemplateId || el.value;
                tmplId = parseInt(v || "0", 10) || 0;
                if (tmplId) break;
            }
        }
        // Último recurso: el hidden product_id (no ideal, pero ayuda)
        if (!tmplId) {
            const pid = parseInt(Q(this.el, "input[name='product_id']")?.value || "0", 10) || 0;
            if (pid) return { product_id: pid, combination: avIds, add_qty: 1, parent_combination: [] };
        }

        const pricelistId = parseInt(Q(this.el, "[data-pricelist-id]")?.dataset.pricelistId || "0", 10) || 0;

        return {
            product_template_id: tmplId || undefined,
            product_id: 0,
            combination: avIds,
            add_qty: 1,
            parent_combination: [],
            pricelist_id: pricelistId || undefined,
        };
    },

    async _hydrateCells(root) {
        const cells = QA(root, "td");
        const queue = cells.slice();
        const self = this;

        const workers = new Array(6).fill(0).map(async function run() {
            while (queue.length) {
                const td = queue.shift();
                const colorId = parseInt(td.dataset.colorId || td.closest("tr")?.dataset.colorId || "0", 10);
                const sizeId  = parseInt(td.dataset.sizeId || "0", 10);
                const avIds = sizeId ? [colorId, sizeId] : [colorId];

                const info = await getCombinationInfo(self._comboArgs(avIds));
                if (info && info.product_id) {
                    const input = Q(td, ".sp-qty");
                    input.dataset.variantId = String(info.product_id);

                    if (typeof info.price === "number") {
                        Q(td, ".sp-price").textContent = fmtPrice(info.price);
                    }

                    let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
                    if (stock === null) stock = await readStock(info.product_id);
                    if (stock !== null) Q(td, ".sp-stock").textContent = `Stock: ${stock}`;

                    const row = td.closest("tr");
                    const img = Q(row, ".sp-color__img");
                    if (!img.getAttribute("src")) {
                        img.setAttribute("src", `/web/image/product.product/${info.product_id}/image_128`);
                    }
                } else {
                    td.classList.add("sp-unavailable");
                }
            }
        });

        await Promise.all(workers);
    },

    _onAddAllToCart(ev) {
        ev.preventDefault();
        const inputs = QA(this.el, "#sp-matrix .sp-qty");
        const calls = [];
        inputs.forEach((inp) => {
            const qty = parseFloat(inp.value || "0");
            const product_id = parseInt(inp.dataset.variantId || "0", 10);
            if (qty > 0 && product_id) {
                calls.push(rpc("/shop/cart/update_json", {
                    product_id,
                    add_qty: qty,
                    display: false,
                }));
            }
        });
        if (!calls.length) return;
        Promise.all(calls).then(() => window.location.reload());
    },
});

export default publicWidget.registry.SerialPrinterMatrix;