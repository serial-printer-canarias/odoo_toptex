/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

function escapeHtml(s) {
    const d = document.createElement("div");
    d.innerText = String(s ?? "");
    return d.innerHTML;
}

function looksLike(name, regex) {
    return regex.test((name || "").toLowerCase());
}

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page",

    start() {
        // evita duplicados
        if (this.el.querySelector(".sp-matrix__table")) {
            return this._super(...arguments);
        }
        this._build();
        return this._super(...arguments);
    },

    // === helpers ===
    _collectAttributeBlocks() {
        // bloques estandar del configurador (data-attribute_name con radios)
        const blocks = [];
        this.$(".js_product .js_attributes [data-attribute_name]").each(function () {
            const $b = $(this);
            const name = ($b.attr("data-attribute_name") || "").trim();
            const options = $b.find('input[type="radio"]').map(function () {
                const $inp = $(this);
                const id = parseInt(
                    $inp.data("value_id") || $inp.data("attribute_value_id") || $inp.val(),
                    10
                );
                const label = ($inp.closest("label").text() || $inp.attr("title") || "").trim();
                return { id, label, $inp };
            }).get();
            if (options.length) blocks.push({ name, options, $el: $b });
        });
        return blocks;
    },

    _pickAxes(blocks) {
        const color = blocks.find(b => looksLike(b.name, /(color|couleur|farbe|colou?r|colore|kleur)/i)) || blocks[0];
        const size  = blocks.find(b => looksLike(b.name, /(size|talla|taille|größe|grosse|taglia|maat)/i)) || blocks[1];
        return { color, size };
    },

    _getTemplateId() {
        // Odoo 18 suele poner data-oe-id en la raíz del product template
        const root = this.el.closest('[data-oe-model="product.template"]');
        if (root && root.dataset.oeId) return parseInt(root.dataset.oeId, 10);
        // fallback: hidden input
        const hid = this.el.querySelector('input[name="product_template_id"]') ||
                    this.el.querySelector('input[name="product_id"]');
        return hid ? parseInt(hid.value, 10) : 0;
    },

    async _fetchVariantMap(tmplId) {
        const res = await jsonrpc("/sp/matrix/variant_map", { product_template_id: tmplId });
        return (res && res.ok) ? res.items : [];
    },

    // === build UI ===
    async _build() {
        const blocks = this._collectAttributeBlocks();
        if (blocks.length === 0) return; // producto sin atributos

        const { color, size } = this._pickAxes(blocks);
        if (!color) return;

        const tmplId = this._getTemplateId();
        if (!tmplId) return;

        const map = await this._fetchVariantMap(tmplId);
        // índice por par (colorId,sizeId) -> variant
        const keyOf = (c, s) => [c, s].filter(Boolean).sort((a,b)=>a-b).join("-");
        const byKey = new Map();
        for (const it of map) {
            const key = keyOf(...it.ptav_ids);
            byKey.set(key, it);
        }

        // ancla ya existe por XML
        const anchor = this.el.querySelector("#sp-matrix");
        if (!anchor) return;

        // tabla
        const table = document.createElement("table");
        table.className = "sp-matrix__table";
        const thead = document.createElement("thead");
        const hr = document.createElement("tr");
        const th0 = document.createElement("th");
        th0.className = "sp-sticky-left";
        th0.innerHTML = "Color";
        hr.appendChild(th0);

        const sizeOpts = size ? size.options : [{ id: 0, label: "One Size" }];
        sizeOpts.forEach(o => {
            const th = document.createElement("th");
            th.innerHTML = escapeHtml(o.label);
            hr.appendChild(th);
        });
        thead.appendChild(hr);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        color.options.forEach(c => {
            const tr = document.createElement("tr");
            tr.dataset.colorId = String(c.id);

            const th = document.createElement("th");
            th.className = "sp-sticky-left";
            th.innerHTML = `
                <div class="sp-color">
                  <img class="sp-color__img" alt="">
                  <span class="sp-color__name">${escapeHtml(c.label)}</span>
                </div>`;
            tr.appendChild(th);

            sizeOpts.forEach(s => {
                const td = document.createElement("td");
                td.dataset.sizeId = String(s.id || 0);
                td.innerHTML = `
                  <div class="sp-cell">
                    <input class="sp-qty" type="number" min="0" step="1" value="0">
                    <div class="sp-meta">
                      <span class="sp-price"></span>
                      <span class="sp-stock"></span>
                    </div>
                  </div>`;
                tbody.appendChild(tr).appendChild(td);

                // hidrata: imagen, precio, stock, variant_id
                const info = byKey.get(keyOf(c.id, s.id || 0));
                if (info) {
                    td.querySelector(".sp-qty").dataset.variantId = String(info.variant_id);
                    td.querySelector(".sp-price").textContent = this._fmtPrice(info.price);
                    td.querySelector(".sp-stock").textContent = `Stock: ${info.stock}`;
                    const img = tr.querySelector(".sp-color__img");
                    if (img && !img.src) img.src = info.image_url;
                } else {
                    td.classList.add("sp-unavailable");
                }
            });

            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        anchor.innerHTML = ""; // por si se reconstruye tras cambiar atributos
        anchor.appendChild(table);

        // botón
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-primary mt-2 sp-add-to-cart";
        btn.textContent = "Añadir selección";
        btn.addEventListener("click", () => this._addAllToCart());
        anchor.appendChild(btn);
    },

    _fmtPrice(v) {
        try {
            const lang = document.documentElement.lang || "es-ES";
            const curr = document.querySelector("[data-website-currency-code]")?.dataset.websiteCurrencyCode || "EUR";
            return new Intl.NumberFormat(lang, { style: "currency", currency: curr }).format(v || 0);
        } catch {
            return (Math.round((v || 0) * 100) / 100).toFixed(2);
        }
    },

    async _addAllToCart() {
        const inputs = this.el.querySelectorAll("#sp-matrix .sp-qty");
        const lines = [];
        inputs.forEach(inp => {
            const qty = parseFloat(inp.value || "0");
            const pid = parseInt(inp.dataset.variantId || "0", 10);
            if (qty > 0 && pid) lines.push({ product_id: pid, qty });
        });
        if (!lines.length) return;

        const res = await jsonrpc("/sp/matrix/cart/add_multi", { lines });
        if (res && res.ok) {
            // refrescamos la página/cart badge
            window.location.reload();
        }
    },
});