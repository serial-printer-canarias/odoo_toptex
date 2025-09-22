/** @odoo-module **/

(function () {
    "use strict";

    const DBG = true;
    const log = (...a) => DBG && console.log("[SP-MATRIX]", ...a);

    // -------------------- Utilidades --------------------
    function onReady(fn) {
        if (document.readyState !== "loading") fn();
        else document.addEventListener("DOMContentLoaded", fn);
    }
    function root() {
        return document.querySelector(".o_wsale_product_page, .oe_website_sale");
    }
    function escapeHtml(s) {
        return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }
    function formatMoney(n) {
        const val = Number(n || 0);
        try { return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(val); }
        catch { return val.toFixed(2); }
    }
    function getTemplateId(r) {
        const el = r.querySelector('input[name="product_template_id"]')
                || r.querySelector('[data-product-template-id]');
        const v = el ? (el.value || el.dataset.productTemplateId) : "0";
        return parseInt(v || "0", 10) || 0;
    }

    // Localiza el contenedor de atributos y dónde insertar
    function findAttributesBlock(r) {
        return (
            r.querySelector(".o_wsale_product_configurator .js_attributes") ||
            r.querySelector(".js_attributes") ||
            r.querySelector(".o_wsale_product_configurator") ||
            r.querySelector("form.o_wsale_product_configurator fieldset")
        );
    }

    // Lee Color/Talla desde radios visibles
    function getAttributeBlocks(r) {
        const blocks = [];
        const containers = Array.from(
            r.querySelectorAll('[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div')
        );
        containers.forEach((el) => {
            const name = (
                el.getAttribute("data-attribute_name") ||
                el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
                el.getAttribute("name") || ""
            ).trim().toLowerCase();

            const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
            if (!radios.length) return;

            const options = radios.map((inp) => {
                const id = parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0", 10) || 0;
                const text = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                    .replace(/\s+/g, " ").trim();
                return id ? { id, text } : null;
            }).filter(Boolean);

            if (options.length) blocks.push({ name, options, el });
        });

        let color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
        let size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

        if (!size) size = { name: "one size", options: [{ id: -1, text: "One Size" }] };
        return { color, size };
    }

    // Construcción del grid
    function renderGrid(color, size) {
        let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
        size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
        thead += "</tr></thead>";

        let tbody = "<tbody>";
        color.options.forEach((c) => {
            tbody += `<tr data-color-id="${c.id}">
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

        const el = document.createElement("div");
        el.id = "sp-matrix";
        el.className = "sp-matrix-box";
        el.innerHTML = `
            <div class="sp-matrix__hdr">Indica cantidades por color y talla.</div>
            <table class="sp-matrix__table">${thead}${tbody}</table>
            <button type="button" class="btn btn-primary sp-add">Añadir selección</button>
        `;
        return el;
    }

    // Estado en memoria: mapa color-size -> variante
    const MatrixState = {
        map: Object.create(null), // key = `${color}-${size}`
        put(rec) { this.map[`${rec.color_id}-${rec.size_id}`] = rec; },
        get(c, s) { return this.map[`${c}-${s}`]; },
        clear() { this.map = Object.create(null); },
    };

    async function fetchVariants(templateId) {
        if (!templateId) return null;
        const res = await fetch(`/sp/matrix/variants/${templateId}`, { credentials: "same-origin" });
        if (!res.ok) throw new Error("variants_fetch_failed");
        const data = await res.json();
        if (!data.ok) throw new Error("variants_payload_error");
        return data;
    }

    function fillImagesAndMeta(r, color, size) {
        // Imagen por fila (toma la primera combinación disponible)
        color.options.forEach((c) => {
            const rec = size.options
                .map((s) => MatrixState.get(c.id, s.id))
                .find(Boolean);
            const img = r.querySelector(`#sp-matrix tr[data-color-id="${c.id}"] img.sp-color__img`);
            if (img && rec && rec.image) img.src = rec.image;
        });

        // Meta por celda (stock + precio) y product_id
        r.querySelectorAll("#sp-matrix input.sp-qty").forEach((inp) => {
            const key = MatrixState.get(inp.dataset.color, inp.dataset.size);
            const meta = inp.closest(".sp-cell").querySelector(".sp-meta");
            if (key) {
                inp.dataset.productId = key.product_id;
                meta.textContent = `On hand: ${key.qty_available} • ${formatMoney(key.price)}`;
                inp.disabled = false;
            } else {
                meta.textContent = "—";
                inp.value = "";
                inp.disabled = true; // no hay variante para esa combinación
            }
        });
    }

    async function ensureMatrix() {
        const r = root();
        if (!r) return;

        // Borra instancias previas
        r.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

        const { color, size } = getAttributeBlocks(r);
        if (!color || !size) {
            log("Faltan atributos (Color/Talla). No se pinta.");
            return;
        }

        const block = findAttributesBlock(r) || r;
        const grid = renderGrid(color, size);
        // Inserta justo debajo de los atributos
        block.parentNode.insertBefore(grid, block.nextSibling);

        // Trae variantes, guarda mapa y pinta fotos/metas
        try {
            MatrixState.clear();
            const tmplId = getTemplateId(r);
            const data = await fetchVariants(tmplId);
            data.records.forEach((rec) => MatrixState.put(rec));
            fillImagesAndMeta(r, color, size);
        } catch (e) {
            log("Error cargando variantes:", e);
        }

        // Click "Añadir selección" => manda líneas al carrito
        grid.querySelector(".sp-add").addEventListener("click", async () => {
            const lines = [];
            r.querySelectorAll("#sp-matrix input.sp-qty").forEach((inp) => {
                const qty = parseFloat(inp.value || "0");
                const pid = parseInt(inp.dataset.productId || "0", 10);
                if (pid && qty > 0) lines.push({ product_id: pid, qty });
            });
            if (!lines.length) return;

            try {
                const res = await fetch("/sp/matrix/add", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ lines }),
                    credentials: "same-origin",
                });
                const out = await res.json();
                if (out.ok) {
                    log("Añadido al carrito. Cantidad:", out.cart_qty);
                    // feedback simple
                    grid.querySelector(".sp-add").classList.add("sp-ok");
                    setTimeout(() => grid.querySelector(".sp-add").classList.remove("sp-ok"), 800);
                }
            } catch (err) {
                console.error("Add-to-cart error:", err);
            }
        });
    }

    // -------------------- Arranque --------------------
    onReady(() => {
        const r = root();
        if (!r) return;

        log("product_matrix.js cargado (frontend)");
        ensureMatrix();

        // Si cambian radios, reconstruimos (y NO se duplica)
        r.addEventListener("change", (ev) => {
            if (ev.target.matches('input[type="radio"]')) ensureMatrix();
        });
    });
})();