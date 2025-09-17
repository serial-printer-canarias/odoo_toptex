/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// Utilidad: ejecutar cuando el DOM está listo
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: ".o_wsale_product_page",

    start() {
        onReady(() => this._buildMatrix());
        return this._super(...arguments);
    },

    // Obtiene grupos de atributos (nombre + opciones)
    _getAttributeBlocks() {
        const root =
            this.el.querySelector(".o_wsale_product_configurator") || this.el;

        const groups = [...root.querySelectorAll(
            ".o_wsale_attribute, .js_product .attribute"  // soporta plantillas distintas
        )];

        return groups.map((g) => {
            const name = (
                g.querySelector(".o_wsale_attribute_name, .attribute_name, .o_variant_label")?.textContent || ""
            ).trim();
            const radios = [...g.querySelectorAll('input[type="radio"]')].map((r) => {
                const lbl = root.querySelector(`label[for="${r.id}"]`);
                const txt = (lbl?.textContent || r.getAttribute("data-value_name") || r.value || "").trim();
                return { input: r, text: txt };
            });
            return { name, radios, el: g };
        });
    },

    _buildMatrix() {
        try {
            const blocks = this._getAttributeBlocks();
            if (!blocks.length) return;

            const colorBlock = blocks.find((b) => /color/i.test(b.name));
            const sizeBlock  = blocks.find((b) => /(talla|size)/i.test(b.name));
            if (!colorBlock || !sizeBlock) {
                // No hay las dos dimensiones, no renderizamos (evita errores)
                return;
            }

            // Contenedor (idempotente)
            let container = this.el.querySelector("#sp-matrix");
            if (!container) {
                container = document.createElement("div");
                container.id = "sp-matrix";
                container.className = "sp-matrix card border rounded p-3 my-3";
                // lo ponemos después del bloque de tallas
                sizeBlock.el.after(container);
            }
            container.innerHTML = "";

            // Tabla
            const table = document.createElement("table");
            table.className = "sp-matrix-table";

            const thead = document.createElement("thead");
            const trh = document.createElement("tr");
            trh.appendChild(document.createElement("th")); // esquina
            sizeBlock.radios.forEach((s) => {
                const th = document.createElement("th");
                th.textContent = s.text;
                trh.appendChild(th);
            });
            thead.appendChild(trh);
            table.appendChild(thead);

            const tbody = document.createElement("tbody");
            colorBlock.radios.forEach((c) => {
                const tr = document.createElement("tr");
                const th = document.createElement("th");
                th.textContent = c.text;
                tr.appendChild(th);

                sizeBlock.radios.forEach((s) => {
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

            // Botón (por ahora solo visual; el add to cart múltiple lo cableamos después)
            const hint = document.createElement("div");
            hint.className = "text-muted small mt-2";
            hint.textContent = "Indica cantidades por color y talla. (Añadido masivo se activa en el siguiente paso)";
            container.appendChild(hint);
        } catch (e) {
            console.error("[SP] Error construyendo la matriz:", e);
        }
    },
});