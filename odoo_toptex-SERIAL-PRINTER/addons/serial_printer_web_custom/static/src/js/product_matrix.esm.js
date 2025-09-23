/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

const NS = (window._sp = window._sp || {});
NS.debug = NS.debug || {};

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page",
    start() {
        // evita duplicados y solo en páginas de producto
        if (this.el.querySelector("#sp-matrix")) return this._super(...arguments);
        const anchor = this.el.querySelector("#sp-matrix-anchor");
        if (!anchor) return this._super(...arguments);

        const blocks = this._getAttributeBlocks();
        if (blocks.length < 2) return this._super(...arguments);
        const { color, size } = this._pickColorAndSize(blocks);
        if (!color || !size) return this._super(...arguments);

        // construir contenedor
        const matrix = document.createElement("div");
        matrix.id = "sp-matrix";
        matrix.className = "sp-matrix o-pt-3";
        anchor.after(matrix);

        // tabla
        const table = document.createElement("table");
        table.className = "sp-matrix__table";
        const thead = document.createElement("thead");
        thead.innerHTML = `<tr><th class="sp-sticky-left">Color</th>${size.options.map(o=>`<th>${_.escape(o.name||"")}</th>`).join("")}</tr>`;
        const tbody = document.createElement("tbody");

        color.options.forEach(c => {
            const tr = document.createElement("tr");
            tr.dataset.colorId = c.id;
            tr.innerHTML = `
                <th class="sp-sticky-left">
                  <div class="sp-color">
                    <img class="sp-color__img" alt="">
                    <span class="sp-color__name">${_.escape(c.name||"")}</span>
                  </div>
                </th>`;
            size.options.forEach(s => {
                const td = document.createElement("td");
                td.dataset.sizeId = s.id;
                td.innerHTML = `
                  <div class="sp-cell">
                    <input type="number" min="0" step="1" class="sp-qty"
                           data-color-id="${c.id}" data-size-id="${s.id}">
                    <div class="sp-meta">
                      <span class="sp-price"></span>
                      <span class="sp-stock"></span>
                    </div>
                  </div>`;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });

        table.appendChild(thead);
        table.appendChild(tbody);
        matrix.appendChild(table);

        // botón
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-primary mt-2 sp-add-to-cart";
        btn.textContent = "Añadir selección";
        btn.addEventListener("click", this._onAddAllToCart.bind(this));
        matrix.appendChild(btn);

        // hidratar datos
        this._hydrateCells().catch(()=>{});
        return this._super(...arguments);
    },

    // --- utilidades ---
    _getAttributeBlocks() {
        const out = [];
        this.el.querySelectorAll(".js_product .js_attributes [data-attribute_name]").forEach(el => {
            const name = (el.getAttribute("data-attribute_name") || "").trim();
            const options = [...el.querySelectorAll("input[type='radio']")].map(inp => {
                const id = parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value, 10);
                const label = (inp.closest("label")?.textContent || inp.getAttribute("title") || "").trim();
                return { id, name: label };
            }).filter(o => Number.isFinite(o.id));
            if (options.length) out.push({ name, options, el });
        });
        NS.debug.blocks = () => out.map(b => ({ name: b.name, count: b.options.length }));
        return out;
    },

    _pickColorAndSize(blocks) {
        const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n||"");
        const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n||"");
        let color = blocks.find(b => isColor(b.name));
        let size  = blocks.find(b => isSize(b.name));
        if (!color && blocks.length) color = blocks[0];
        if (!size  && blocks.length > 1) size  = blocks[1];
        return { color, size };
    },

    _tmplId() {
        return parseInt(
            this.el.querySelector("[data-product-template-id]")?.dataset.productTemplateId ||
            this.el.querySelector("input[name='product_id']")?.value || 0,
            10
        );
    },

    _pricelistId() {
        return parseInt(
            document.querySelector("[data-pricelist-id]")?.dataset.pricelistId || 0,
            10
        );
    },

    _comboArgs(avIds) {
        return {
            product_template_id: this._tmplId() || undefined,
            product_id: 0,
            combination: avIds,           // lista de attribute_value_ids (color, talla)
            add_qty: 1,
            parent_combination: [],
            pricelist_id: this._pricelistId() || undefined,
        };
    },

    async _fetchCombination(avIds) {
        // Primero website_sale (Odoo 17/18)
        try {
            return await jsonrpc("/shop/get_combination_info", this._comboArgs(avIds));
        } catch (e) {
            // Fallback a /sale/ por si el tema o versión expone esa ruta
            try {
                return await jsonrpc("/sale/get_combination_info", this._comboArgs(avIds));
            } catch {
                return null;
            }
        }
    },

    async _getStock(variantId) {
        try {
            const res = await jsonrpc("/web/dataset/call_kw", {
                model: "product.product",
                method: "read",
                args: [[variantId], ["qty_available"]],
                kwargs: {},
            });
            return (res && res[0] && typeof res[0].qty_available === "number") ? res[0].qty_available : null;
        } catch { return null; }
    },

    async _hydrateCells() {
        const cells = Array.from(this.el.querySelectorAll("#sp-matrix td"));
        const workers = 6;
        const queue = cells.slice();

        const run = async () => {
            while (queue.length) {
                const td = queue.shift();
                const colorId = parseInt(td.closest("tr")?.dataset.colorId || td.querySelector(".sp-qty")?.dataset.colorId || "0", 10);
                const sizeId  = parseInt(td.dataset.sizeId || td.querySelector(".sp-qty")?.dataset.sizeId || "0", 10);
                if (!colorId || !sizeId) { td.classList.add("sp-unavailable"); continue; }

                const info = await this._fetchCombination([colorId, sizeId]);
                if (!info || !info.product_id) { td.classList.add("sp-unavailable"); continue; }

                // id variante
                td.querySelector(".sp-qty").dataset.variantId = info.product_id;

                // precio
                if (typeof info.price === "number") {
                    td.querySelector(".sp-price").textContent = this._fmtPrice(info.price);
                }

                // stock (info o fallback)
                let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
                if (stock === null) stock = await this._getStock(info.product_id);
                if (stock !== null) td.querySelector(".sp-stock").textContent = `Stock: ${stock}`;

                // foto por color (una vez por fila)
                const img = td.closest("tr").querySelector(".sp-color__img");
                if (!img.getAttribute("src")) {
                    img.src = `/web/image/product.product/${info.product_id}/image_128`;
                }
            }
        };

        await Promise.all(new Array(workers).fill(0).map(run));
    },

    _fmtPrice(v) {
        try {
            const lang = document.documentElement.lang || "es-ES";
            const curr = document.querySelector("[data-website-currency-code]")?.dataset.websiteCurrencyCode || "EUR";
            return new Intl.NumberFormat(lang, { style: "currency", currency: curr }).format(v);
        } catch { return (Math.round(v*100)/100).toFixed(2); }
    },

    async _onAddAllToCart(ev) {
        ev.preventDefault();
        const inputs = Array.from(this.el.querySelectorAll("#sp-matrix .sp-qty"));
        const jobs = [];
        for (const inp of inputs) {
            const qty = parseFloat(inp.value || "0");
            const variantId = parseInt(inp.dataset.variantId || "0", 10);
            if (qty > 0 && variantId) {
                jobs.push(jsonrpc("/shop/cart/update_json", {
                    product_id: variantId,
                    add_qty: qty,
                    display: false,
                }));
            }
        }
        if (!jobs.length) return;
        try { await Promise.all(jobs); window.location.reload(); } catch { /* no-op */ }
    },
});

export default publicWidget.registry.SerialPrinterMatrix;