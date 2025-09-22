/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Helpers DOM ===
const $ = (sel, scope = document) => scope.querySelector(sel);
const $$ = (sel, scope = document) => Array.from(scope.querySelectorAll(sel));
const esc = (s) =>
    String(s || "").replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));

// === Detectar bloques de atributos (Color, Talla) ===
function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = $$(
        // Cubre la mayoría de plantillas de Odoo 16/17/18
        '.js_attributes > div, [data-attribute_name], .o_product_configurator [name], .js_attribute',
        scope
    );

    for (const el of containers) {
        const name = (
            el.getAttribute("data-attribute_name") ||
            el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
            el.getAttribute("name") ||
            ""
        ).trim().toLowerCase();

        const radios = $$('input[type="radio"][data-value-id], input[type="radio"][data-attribute-value-id], input[type="radio"][value]', el);
        if (!radios.length) continue;

        const options = radios.map((inp) => {
            const id = parseInt(
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                10
            );
            if (!id) return null;
            const text = (inp.closest("label")?.textContent || inp.title || "")
                .replace(/\s+/g, " ")
                .trim();
            return { id, text, _radio: inp };
        }).filter(Boolean);

        if (options.length) blocks.push({ name, el, radios, options });
    }

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    if (size) size.options = sortSizes(size.options);
    return { color, size };
}

// === Ordenación de tallas: numéricas o estándar ===
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase());
        const ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// === Detección de IDs base (product_id actual, template y pricelist) ===
function getPageIds(page) {
    const currentProductId =
        parseInt(($('input[name="product_id"]', page) || {}).value || "0", 10) ||
        parseInt(page.getAttribute("data-product-id") || "0", 10) || 0;

    // Muy común en website_sale: distintos sitios donde puede estar
    const templateId =
        parseInt(($('input[name="product_template_id"]', page) || {}).value || "0", 10) ||
        parseInt(page.getAttribute("data-product-template-id") || "0", 10) ||
        // A veces viene en un contenedor editable
        parseInt(($('[data-oe-model="product.template"][data-oe-id]', page) || {}).dataset?.oeId || "0", 10) || 0;

    // Pricelist (si no está, Odoo usa la de sesión)
    const pricelistId =
        parseInt(($('input[name="pricelist_id"]', page) || {}).value || "0", 10) ||
        parseInt(document.body.getAttribute("data-pricelist-id") || "0", 10) || 0;

    return { currentProductId, templateId, pricelistId };
}

// === Pide a Odoo la combinación (product_id) y devuelve también URL miniatura ===
const _comboCache = new Map(); // clave: "colorId-sizeId" -> data
async function fetchCombinationInfo({ templateId, currentProductId, pricelistId }, colorId, sizeId) {
    const key = `${colorId || 0}-${sizeId || 0}`;
    if (_comboCache.has(key)) return _comboCache.get(key);

    const combination = [colorId, sizeId].filter(Boolean);
    const res = await fetch("/shop/combination_info", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            product_template_id: templateId || undefined,
            product_id: currentProductId || undefined,
            combination,
            add_qty: 1,
            pricelist_id: pricelistId || undefined,
        }),
        credentials: "same-origin",
    });
    if (!res.ok) throw new Error("combination_info failed");
    const data = await res.json();

    const productId = data.product_id || 0;
    const price = data.price || 0;
    const imageUrl = productId ? `/web/image/product.product/${productId}/image_128` : "";

    const out = { productId, price, imageUrl, ok: !!productId };
    _comboCache.set(key, out);
    return out;
}

// === Construcción del HTML del grid ===
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    (size ? size.options : [{ text: "One Size", id: 0 }]).forEach((s) => {
        thead += `<th>${esc(s.text)}</th>`;
    });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        tbody += `<tr data-color-id="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="">
                    <span>${esc(c.text)}</span>
                </div>
            </th>`;
        (size ? size.options : [{ id: 0 }]).forEach((s) => {
            tbody += `<td>
                <div class="sp-cell" data-size-id="${s.id}">
                    <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric" placeholder="0">
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
        <button type="button" class="sp-add btn btn-primary mt-2">Añadir selección</button>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// === Inserta el grid en el sitio correcto (sin duplicados) ===
function mountMatrix(page, html) {
    // Limpia duplicados
    const old = $("#sp-matrix", page);
    if (old) old.remove();

    const host =
        // Debajo de atributos (ideal)
        $('.o_wsale_product_configurator .js_attributes', page) ||
        // Encima de "Personalizar" / bloques extra
        $('.o_wsale_product_configurator .o_wsale_product_actions', page) ||
        // Fallback: al final de la columna derecha
        $('.o_wsale_product_configurator', page) ||
        page;

    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    const box = wrapper.firstElementChild;

    // Si encontramos atributos, insertamos DESPUÉS de ellos; si no, al comienzo de actions
    if ($('.o_wsale_product_configurator .js_attributes', page) && host.parentNode) {
        host.parentNode.insertBefore(box, host.nextSibling);
    } else {
        host.prepend(box);
    }
}

// === Rellena miniaturas y guarda mapeo combinación->product_id ===
async function hydrateMatrix(page, color, size, ids) {
    const rows = $$("#sp-matrix tbody tr", page);
    for (const row of rows) {
        const colorId = parseInt(row.getAttribute("data-color-id"), 10);
        // Elegimos UNA talla de referencia sólo para miniaturas (la 1ª)
        const refSizeId = size ? (size.options[0]?.id || 0) : 0;
        try {
            const info = await fetchCombinationInfo(ids, colorId, refSizeId);
            if (info.ok) {
                const img = $(".sp-color__img", row);
                if (img) img.src = info.imageUrl;
            }
        } catch {
            /* ignoramos: mostramos hueco */
        }
    }
}

// === Añadir selección al carrito (usa update_json nativo) ===
async function addSelectionToCart(page, color, size, ids) {
    const cells = $$("#sp-matrix .sp-cell", page);
    const lines = [];

    // Reunimos celdas con qty>0 y resolvemos product_id por combinación
    for (const cell of cells) {
        const qty = parseInt(($(".sp-qty", cell)?.value || "0"), 10) || 0;
        if (!qty) continue;
        const colorId = parseInt(cell.closest("tr").getAttribute("data-color-id"), 10);
        const sizeId  = parseInt(cell.getAttribute("data-size-id"), 10) || 0;

        const info = await fetchCombinationInfo(ids, colorId, sizeId);
        if (info.ok) lines.push({ product_id: info.productId, qty });
    }
    if (!lines.length) return;

    // Llamadas secuenciales (más seguras con sesiones)
    for (const l of lines) {
        await fetch("/shop/cart/update_json", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "same-origin",
            body: JSON.stringify({ product_id: l.product_id, add_qty: l.qty }),
        });
    }

    // Feedback sencillo y refresco mini del carrito (Odoo lo hace solo)
    $(".sp-add", page)?.classList.add("btn-success");
    setTimeout(() => $(".sp-add", page)?.classList.remove("btn-success"), 900);
}

// === Lógica principal ===
function ensureMatrix() {
    const page = $(".o_wsale_product_page") || document;
    if (!page) return;

    const { color, size } = getAttributeBlocks(page);
    if (!color) {
        $("#sp-matrix", page)?.remove();
        return;
    }

    // Construye y monta
    mountMatrix(page, renderGrid(color, size));

    // IDs base
    const ids = getPageIds(page);

    // Miniaturas por color
    hydrateMatrix(page, color, size, ids);

    // Click "Añadir selección"
    $(".sp-add", page)?.addEventListener("click", () =>
        addSelectionToCart(page, color, size, ids)
    );
}

// === Arranque (y evitar duplicados en re-render) ===
onReady(() => {
    const page = $(".o_wsale_product_page") || document;
    ensureMatrix();

    // Si el DOM de la ficha cambia (al cambiar radios), reconstruimos una sola vez
    const obs = new MutationObserver((muts) => {
        // Sólo si afectan al configurador (evita bucles)
        if (muts.some((m) => (m.target && (m.target.closest?.(".o_wsale_product_configurator"))))) {
            ensureMatrix();
        }
    });
    obs.observe(page, { childList: true, subtree: true });

    // Cambios directos en radios
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
});