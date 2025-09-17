/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

const COLOR_KEYS = ["color","colour","couleur","farbe","colore"];
const SIZE_KEYS  = ["talla","size","taille","größe","groesse","taglia"];

function norm(txt="") { return txt.trim().toLowerCase(); }

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page",

    start() {
        // Observa el DOM porque Odoo puede inyectar los atributos tarde
        this._mounted = false;
        this._observer = new MutationObserver(() => this._tryBuild());
        this._observer.observe(this.el, { childList: true, subtree: true });
        // Primer intento inmediato
        this._tryBuild();
        return this._super(...arguments);
    },

    destroy() {
        this._observer && this._observer.disconnect();
        this._super(...arguments);
    },

    _tryBuild() {
        if (this._mounted) return;

        const { colorBlock, sizeBlock } = this._findBlocks();
        if (!colorBlock || !sizeBlock) return; // aún no están listos

        this._buildMatrix(colorBlock, sizeBlock);
        this._mounted = true;
        this._observer && this._observer.disconnect();
        // console.log("[SP] Matrix montada");
    },

    _findBlocks() {
        const root =
            this.el.querySelector(".o_wsale_product_configurator") || this.el;

        // soportar distintas plantillas de Odoo
        const groups = [...root.querySelectorAll(
            ".o_wsale_attribute, .js_product .attribute, [data-attribute_name], [data-attribute-name]"
        )];

        const parsed = groups.map((g) => {
            // nombre del grupo a partir de varios sitios
            const name =
                g.getAttribute("data-attribute_name") ||
                g.getAttribute("data-attribute-name") ||
                g.querySelector("[data-attribute_name]")?.getAttribute("data-attribute_name") ||
                g.querySelector("[data-attribute-name]")?.getAttribute("data-attribute-name") ||
                g.querySelector(".o_wsale_attribute_name, .attribute_name, .o_variant_label")?.textContent ||
                "";

            const radios = [...g.querySelectorAll('input[type="radio"]')].map((r) => {
                const lbl = root.querySelector(`label[for="${r.id}"]`);
                const txt = r.dataset.valueName || r.getAttribute("data-value_name") || r.value || lbl?.textContent || "";
                return { input: r, text: txt.trim() };
            });

            return { name: name.trim(), radios, el: g };
        });

        const colorBlock = parsed.find((b) => {
            const n = norm(b.name);
            return COLOR_KEYS.some((k) => n.includes(k)) && b.radios.length;
        });

        const sizeBlock = parsed.find((b) => {
            const n = norm(b.name);
            return SIZE_KEYS.some((k) => n.includes(k)) && b.radios.length;
        });

        return { colorBlock, sizeBlock };
    },

    _buildMatrix(colorBlock, sizeBlock) {
        // contenedor idempotente
        let container = this.el.querySelector("#sp-matrix");
        if (!container) {
            container = document.createElement("div");
            container.id = "sp-matrix";
            container.className = "sp-matrix card border rounded p-3 my-3";
            sizeBlock.el.after(container);
        }
        container.innerHTML = "";

        const table = document.createElement("table");
        table.className = "sp-matrix-table";

        const thead = document.createElement("thead");
        const trh = document.createElement("tr");
        trh.appendChild(document.createElement("th")); // esquina
        sizeBlock.radios.forEach((s) => {
            const th = document.createElement("th");
            th.textContent = s.text;
            thead.appendChild(trh);
            trh.appendChild(th);
        });
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        colorBlock.radios.forEach((c) => {
            const tr = document.createElement("tr");
            const th = document.createElement("th");
            th.textContent = c.text;
            tr.appendChild(th);

            sizeBlock.radios.forEach(() => {
                const td = document.createElement("td");
                const input = document.createElement("input");
                input.type = "number";
                input.min = "0";
                input.step = "1";
                input.className = "sp-qty";
                td.appendChild(input);
                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        container.appendChild(table);

        const hint = document.createElement("div");
        hint.className = "text-muted small mt-2";
        hint.textContent = "Indica cantidades por color y talla.";
        container.appendChild(hint);
    },
});