/**  Serial Printer – Product Matrix (Odoo 18, ES modules)
 *   Inserta una matriz de cantidades por Color × Talla en la ficha de producto.
 *   - Foto por color (imagen de la variante)
 *   - Precio por combinación (si lo devuelve Odoo)
 *   - Stock: usa stock_quantity de combination_info; si no, intenta read(qty_available)
 *   - Botón “Añadir selección” agrega todas las celdas >0 al carrito
 */

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

const Q = (root, sel) => root.querySelector(sel);
const QA = (root, sel) => Array.from(root.querySelectorAll(sel));

/** Helpers --------------------------------------------------------------- */
async function getCombinationInfo(args) {
    // Primero la ruta de website_sale; si falla, intenta la de sale
    try {
        return await jsonrpc("/shop/get_combination_info", args);
    } catch (_) {
        try {
            return await jsonrpc("/sale/get_combination_info", args);
        } catch (__) {
            return null;
        }
    }
}

async function readStock(variantId) {
    try {
        const res = await jsonrpc("/web/dataset/call_kw", {
            model: "product.product",
            method: "read",
            args: [[variantId], ["qty_available"]],
            kwargs: {},
        });
        return (res && res[0] && typeof res[0].qty_available === "number")
            ? res[0].qty_available
            : null;
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
    // Bloques estándar website_sale
    const blocks = [];
    QA($page, ".js_product .js_attributes [data-attribute_name]").forEach((el) => {
        const name = (el.getAttribute("data-attribute_name") || "").trim();
        const options = [];
        QA(el, "input[type='radio']").forEach((inp) => {
            const id =
                parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0", 10) || 0;
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

/** Widget ---------------------------------------------------------------- */
publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page",
    disabledInEditableMode: false,

    start() {
        // Evitar duplicados
        if (Q(this.el, "#sp-matrix")) return this._super(...arguments);
        this._buildIfPossible();
        return this._super(...arguments);
    },

    /** Construir matriz si hay al menos 1D (color) y opcionalmente talla. */
    async _buildIfPossible() {
        const page = this.el;
        const blocks = detectBlocks(page);
        if (!blocks.length) return;

        const { color, size } = pickColorSize(blocks);
        if (!color) return;

        // Anchor robusto: debajo del bloque de precio o, si no existe, al final
        const anchor =
            Q(page, ".product_price") ||
            Q(page, ".o_wsale_product_information") ||
            Q(page, ".js_product") ||
            page;

        const matrix = document.createElement("div");
        matrix.id = "sp-matrix";
        matrix.className = "sp-matrix o-pt-3 o-mt-2";
        anchor.parentNode.insertBefore(matrix, anchor.nextSibling);

        // Tabla
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
                tbody.appendChild(tr);
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

        // Hidratar con info (precio/stock/variant_id + foto color)
        await this._hydrateCells(matrix);
    },

    /** Args para combination_info */
    _comboArgs(avIds) {
        const tmplId =
            parseInt(Q(this.el, "[data-product-template-id]")?.dataset.productTemplateId || "0", 10) ||
            parseInt(Q(this.el, "input[name='product_id']")?.value || "0", 10) ||
            0;

        const pricelistId =
            parseInt(Q(this.el, "[data-pricelist-id]")?.dataset.pricelistId || "0", 10) || 0;

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
        const page = this;

        const queue = cells.slice();
        const workers = new Array(6).fill(0).map(async function worker() {
            while (queue.length) {
                const td = queue.shift();
                const colorId = parseInt(td.dataset.colorId || td.closest("tr")?.dataset.colorId || "0", 10);
                const sizeId  = parseInt(td.dataset.sizeId || "0", 10);

                const avIds = sizeId ? [colorId, sizeId] : [colorId];
                const info = await getCombinationInfo(page._comboArgs(avIds));

                if (info && info.product_id) {
                    // Guardar variant id en el input
                    const input = Q(td, ".sp-qty");
                    input.dataset.variantId = String(info.product_id);

                    // Precio
                    if (typeof info.price === "number") {
                        Q(td, ".sp-price").textContent = fmtPrice(info.price);
                    }

                    // Stock
                    let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
                    if (stock === null) stock = await readStock(info.product_id);
                    if (stock !== null) Q(td, ".sp-stock").textContent = `Stock: ${stock}`;

                    // Foto del color (una vez por fila)
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
                calls.push(jsonrpc("/shop/cart/update_json", {
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