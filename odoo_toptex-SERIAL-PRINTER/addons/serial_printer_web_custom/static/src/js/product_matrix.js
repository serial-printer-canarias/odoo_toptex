/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Evitar duplicados globales ===
if (!window.__SP_MATRIX__) window.__SP_MATRIX__ = { built: false, data: null };

function qs(sel, root = document) { return root.querySelector(sel); }
function qsa(sel, root = document) { return Array.from(root.querySelectorAll(sel)); }

function getTemplateId() {
    const cand = [
        'form.o_wsale_product_configurator [name="product_template_id"]',
        '[name="product_template_id"]',
        '.o_wsale_product_page [data-product-template-id]',
    ];
    for (const s of cand) {
        const el = qs(s);
        if (el) return parseInt(el.value || el.dataset.productTemplateId, 10) || 0;
    }
    return 0;
}

function anchorHost() {
    // Insertamos debajo del configurador de atributos
    return qs('.o_wsale_product_page form.o_wsale_product_configurator') ||
           qs('.o_wsale_product_page .js_attributes') ||
           qs('.o_wsale_product_page #product_details') ||
           qs('.o_wsale_product_page');
}

function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

function renderGrid(data) {
    const { colors, sizes, matrix } = data;

    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    sizes.forEach((s) => { thead += `<th>${escapeHtml(s.name)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    colors.forEach((c) => {
        tbody += `<tr>
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" src="${c.image || ""}" alt="${escapeHtml(c.name)}"/>
                    <span>${escapeHtml(c.name)}</span>
                </div>
            </th>`;
        sizes.forEach((s) => {
            const key = `${c.id}-${s.id}`;
            const meta = matrix[key] || {};
            const price = (meta.price != null) ? `€${(+meta.price).toFixed(2)}` : "";
            const stock = (meta.stock != null) ? `${meta.stock}` : "";
            tbody += `<td>
                <div class="sp-cell">
                    <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric"
                        placeholder="0" data-key="${key}" data-product="${meta.product_id || ""}">
                    <div class="sp-meta">
                        ${price ? `<span class="sp-price">${price}</span>` : ""}
                        ${stock !== "" ? `<span class="sp-stock">Stock: ${stock}</span>` : ""}
                    </div>
                </div>
            </td>`;
        });
        tbody += "</tr>";
    });
    tbody += "</tbody>";

    return `
      <div id="sp-matrix" class="sp-matrix-box">
        <table class="sp-matrix__table">${thead}${tbody}</table>
        <button type="button" class="sp-add btn btn-primary">Añadir selección</button>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

async function fetchMap(ptId) {
    try {
        const resp = await fetch("/sp_matrix/map", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pt_id: ptId }),
            credentials: "same-origin",
        });
        const json = await resp.json();
        if (!json || !json.ok) throw new Error(json && json.error || "map_failed");
        return json;
    } catch (e) {
        console.error("[SP] /sp_matrix/map error:", e);
        return null;
    }
}

function removeMatrix() {
    const ex = qs("#sp-matrix");
    if (ex) ex.remove();
}

function placeMatrix(html) {
    const host = anchorHost();
    if (!host) return;
    // Insertamos justo DESPUÉS del configurador, para que quede en su sitio
    host.insertAdjacentHTML("afterend", html);
    document.body.classList.add("sp-matrix-active");
}

async function ensureMatrix() {
    if (!qs(".o_wsale_product_page")) return;

    // Siempre borramos antes de pintar para evitar duplicados
    removeMatrix();

    const ptId = getTemplateId();
    if (!ptId) {
        console.info("[SP] Sin product_template_id. No se pinta matriz.");
        return;
    }

    // Cache simple para misma ficha
    if (!window.__SP_MATRIX__.data || window.__SP_MATRIX__.data.template_id !== ptId) {
        window.__SP_MATRIX__.data = await fetchMap(ptId);
    }
    const data = window.__SP_MATRIX__.data;
    if (!data) return;

    placeMatrix(renderGrid(data));
    bindActions();
    window.__SP_MATRIX__.built = true;

    console.log("[SP] Matriz lista.");
}

function bindActions() {
    const root = qs("#sp-matrix");
    if (!root) return;

    // Añadir selección al carrito
    const btn = qs(".sp-add", root);
    if (btn) {
        btn.addEventListener("click", async () => {
            const items = qsa('input.sp-qty', root)
                .map((el) => ({ qty: parseInt(el.value || "0", 10) || 0, product: parseInt(el.dataset.product || "0", 10) || 0 }))
                .filter((r) => r.qty > 0 && r.product > 0);

            if (!items.length) {
                alert("No hay cantidades para añadir.");
                return;
            }

            // Añadimos en serie para evitar conflictos
            for (const it of items) {
                const fd = new FormData();
                fd.append("product_id", it.product);
                fd.append("add_qty", String(it.qty));
                fd.append("force_create", "1");
                try {
                    await fetch("/shop/cart/update_json", {
                        method: "POST",
                        body: fd,
                        credentials: "same-origin",
                        headers: { "X-Requested-With": "XMLHttpRequest" },
                    }).then((r) => r.json());
                } catch (e) {
                    console.error("[SP] add_to_cart error", e);
                }
            }
            // Refrescamos minicart si existe
            document.dispatchEvent(new CustomEvent("cart-updated"));
        });
    }
}

// === Arranque METÓDICO ===
onReady(() => {
    // 1) Pinta una sola vez
    ensureMatrix();

    // 2) Si cambian radios del configurador, RECONSTRUIR SIN DUPLICAR
    const page = qs(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
        if (ev.target && ev.target.matches('input[type="radio"], select')) {
            ensureMatrix();
        }
    });

    // 3) Como refuerzo, si el DOM del configurador muta, reinsertar (sin duplicar).
    const host = anchorHost();
    if (host) {
        const mo = new MutationObserver(() => ensureMatrix());
        mo.observe(host, { childList: true, subtree: true });
    }
});