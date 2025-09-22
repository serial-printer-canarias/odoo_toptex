/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Buscar bloques de atributos y detectar Color/Talla ===
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = Array.from(
        scope.querySelectorAll(
            '[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div'
        )
    );

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
            const id = parseInt(
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                10
            ) || 0;
            const txt = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
                .replace(/\s+/g, " ")
                .trim();
            return id ? { id, text: txt, _radio: inp } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options, el });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// === Ordena tallas: numéricas o estándar ===
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a,b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase()), ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
}

// === Construye el HTML de la matriz (UI) ===
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${escapeHtml(s.text)}</th>`; });
    thead += '</tr></thead>';

    let tbody = '<tbody>';
    color.options.forEach((c) => {
        tbody += `<tr data-color-id="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="" />
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
        tbody += '</tr>';
    });
    tbody += '</tbody>';

    return `
      <div id="sp-matrix" class="sp-matrix-box">
        <table class="sp-matrix__table">${thead}${tbody}</table>
        <button type="button" id="sp-matrix-add" class="btn btn-primary mt-2">Añadir selección</button>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// === Inserta/actualiza la matriz y engancha eventos ===
async function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    const anchor =
        document.getElementById("sp-matrix-anchor") ||
        page.querySelector(".js_attributes") ||
        page.querySelector("form.o_wsale_product_configurator") ||
        page;

    const prev = page.querySelector("#sp-matrix");
    if (prev) prev.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    anchor.insertAdjacentHTML("beforeend", renderGrid(color, size));
    document.body.classList.add("sp-matrix-active");

    // datos backend (imágenes / precio / stock)
    try {
        const curVariantId = parseInt(
            page.querySelector('input[name="product_id"]')?.value || "0",
            10
        ) || 0;

        const resp = await fetch(`/sp_matrix/v1/variants?variant_id=${curVariantId}`, {
            credentials: "same-origin",
        });
        if (resp.ok) {
            const data = await resp.json();
            for (const [colorId, url] of Object.entries(data.images || {})) {
                const img = page.querySelector(`tr[data-color-id="${colorId}"] .sp-color__img`);
                if (img) img.src = url;
            }
            const matrix = page.querySelector("#sp-matrix");
            matrix.dataset.combos = JSON.stringify(data.combos || {});
            matrix.dataset.templateId = String(data.template_id || "");
        }
    } catch (e) {}

    // handler Añadir selección
    const addBtn = page.querySelector("#sp-matrix-add");
    addBtn?.addEventListener("click", async () => {
        const matrix = page.querySelector("#sp-matrix");
        const combos = JSON.parse(matrix?.dataset?.combos || "{}");

        const qtyInputs = Array.from(page.querySelectorAll("#sp-matrix input.sp-qty"));
        const toSend = [];
        qtyInputs.forEach((inp) => {
            const q = parseInt(inp.value || "0", 10) || 0;
            if (!q) return;
            const c = String(inp.dataset.color), s = String(inp.dataset.size);
            const key = `${c}-${s}`;
            const combo = combos[key];
            if (combo?.product_id) {
                toSend.push({ product_id: combo.product_id, qty: q });
            }
        });

        if (!toSend.length) return;

        try {
            const r = await fetch("/sp_matrix/v1/add", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ lines: toSend }),
            });
            if (r.ok) {
                qtyInputs.forEach((i) => (i.value = ""));
                document.querySelectorAll(".my_cart_quantity").forEach((el) => {
                    const n = parseInt(el.textContent || "0", 10) || 0;
                    const add = toSend.reduce((acc, it) => acc + (it.qty || 0), 0);
                    el.textContent = String(n + add);
                });
            }
        } catch (e) {}
    });
}

// === Arranque y reconstrucción si cambian radios ===
onReady(() => {
    ensureMatrix();
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});