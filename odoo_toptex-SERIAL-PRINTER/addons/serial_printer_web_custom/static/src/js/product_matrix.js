/** @odoo-module **/

import { jsonrpc } from "@web/core/network/rpc_service";

/* ---------- utilidades ---------- */
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

function qsa(root, sel) { return Array.from(root.querySelectorAll(sel)); }

function getAttrBlocks(root) {
    // Buscamos los bloques de atributos (Color, Talla, …) en varias estructuras
    const containers =
        qsa(root, ".o_wsale_product_configurator")        // v17/18
        || qsa(root, ".o_product_configurator")
        || qsa(root, ".js_add_cart_variants");

    const out = [];
    containers.forEach(c => {
        qsa(c, "[data-attribute_name]").forEach(el => {
            const labelEl = el.querySelector("label, .o_variant_label, .label");
            const name = (labelEl?.textContent || el.getAttribute("data-attribute_name") || "")
                .trim().toLowerCase();
            const radios = qsa(el, 'input[type="radio"]');
            if (!radios.length) return;
            const options = radios.map(r => {
                const lab = el.querySelector(`label[for="${r.id}"]`);
                const text = (lab?.textContent || r.value || "").trim();
                const valId = r.dataset.valueId || r.value || "";
                return { id: valId, text, input: r };
            });
            if (options.length) out.push({ el, name, options });
        });
    });
    return out;
}

const isColor = (n) => /color|colour|couleur/i.test(n || "");
const isSize  = (n) => /size|talla|taille|größe|maat/i.test(n || "");

function renderGrid(color, size) {
    const table = document.createElement("table");
    table.className = "sp-matrix";

    const thead = document.createElement("thead");
    const hr = document.createElement("tr");
    hr.appendChild(document.createElement("th"));
    size.options.forEach(o => {
        const th = document.createElement("th");
        th.textContent = o.text;
        hr.appendChild(th);
    });
    thead.appendChild(hr);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    color.options.forEach(co => {
        const tr = document.createElement("tr");

        const th = document.createElement("th");
        th.textContent = co.text;
        tr.appendChild(th);

        size.options.forEach(so => {
            const td = document.createElement("td");
            const inp = document.createElement("input");
            inp.type = "number";
            inp.min = "0";
            inp.step = "1";
            inp.className = "sp-qty";
            inp.dataset.colorId = co.id;
            inp.dataset.sizeId = so.id;
            td.appendChild(inp);
            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });
    table.appendChild(tbody);

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-primary mt-2 sp-add";
    btn.textContent = "Añadir líneas";

    const wrap = document.createElement("div");
    wrap.className = "sp-matrix-wrap my-3";
    wrap.appendChild(table);
    wrap.appendChild(btn);

    return { wrap, btn };
}

async function getVariantId(templateId, valueIds) {
    // Servicio estándar de website_sale
    const res = await jsonrpc("/website_sale/get_combination_info", {
        product_template_id: templateId,
        combination: valueIds.map(Number),
        add_qty: 1,
        parent_combination: [],
    });
    return res?.product_id || 0;
}

function getTemplateId(root) {
    const el = root.querySelector('input[name="product_template_id"], input[name="product_template"]');
    return Number(el?.value || 0);
}

/* ---------- inicio ---------- */
onReady(() => {
    const root = document.querySelector(".o_wsale_product_page");
    if (!root) return;

    const blocks = getAttrBlocks(document);
    const color = blocks.find(b => isColor(b.name)) || null;
    const size  = blocks.find(b => isSize(b.name))  || null;

    if (!color || !size) {
        console.debug("[SP] Sin Color/Talla: matriz no aplicada.");
        return;
    }

    const qtyBox = root.querySelector(".o_wsale_product_qty, .o_product_add_to_cart, .quantity");
    const { wrap, btn } = renderGrid(color, size);
    (qtyBox?.parentElement || root).insertBefore(wrap, qtyBox || root.firstChild);

    const templateId = getTemplateId(root);

    btn.addEventListener("click", async () => {
        const lines = qsa(wrap, "input.sp-qty").filter(i => Number(i.value) > 0);
        if (!lines.length) return;

        for (const i of lines) {
            const valIds = [i.dataset.colorId, i.dataset.sizeId].map(Number).filter(Boolean);
            let productId = 0;
            if (templateId && valIds.length) {
                productId = await getVariantId(templateId, valIds);
            }
            if (productId) {
                await jsonrpc("/shop/cart/update_json", {
                    product_id: productId,
                    add_qty: Number(i.value),
                    display: false,
                });
            }
        }
        window.location.reload();
    });

    console.log("[SP] Matriz cargada.");
});