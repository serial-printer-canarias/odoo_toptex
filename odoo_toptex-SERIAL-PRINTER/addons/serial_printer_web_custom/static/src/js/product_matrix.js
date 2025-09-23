/** @odoo-module **/

// === Utilidad: ejecutar cuando el DOM está listo ===
function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
}

// === Utilidad simple para escapar HTML ===
function esc(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
}

// === Detecta contenedor de atributos (Color / Talla) y opciones ===
function getAttributeBlocks(scope) {
    const blocks = [];
    // Candidatos típicos en Odoo 17/18 + temas
    const containers = Array.from(
        scope.querySelectorAll('[data-attribute_name], .js_attributes > div, .js_attribute')
    );

    containers.forEach((el) => {
        const name =
            (el.getAttribute("data-attribute_name") ||
                el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
                el.getAttribute("name") ||
                "")
                .trim()
                .toLowerCase();

        const radios = Array.from(el.querySelectorAll('input[type="radio"]'));
        if (!radios.length) return;

        const options = radios.map((inp) => {
            // Preferimos PTAV id si está (data-value-id). Si no, caemos a attribute_value_id o value.
            const ptav = parseInt(
                inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
                10
            ) || 0;

            const label = (inp.closest("label")?.textContent || inp.title || "")
                .replace(/\s+/g, " ")
                .trim();

            return ptav ? { id: ptav, text: label } : null;
        }).filter(Boolean);

        if (options.length) blocks.push({ name, options, el });
    });

    // Heurística para localizar color/talla por nombre
    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));

    // Ordena tallas con lógica estándar
    if (size) size.options = sortSizes(size.options);

    return { color, size, blocks };
}

// === Orden de tallas (numéricas o XS..XXL) ===
function sortSizes(opts) {
    const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
    return [...opts].sort((a, b) => {
        const na = parseFloat(a.text), nb = parseFloat(b.text);
        if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
        const ia = std.indexOf(a.text.toUpperCase());
        const ib = std.indexOf(b.text.toUpperCase());
        if (ia >= 0 && ib >= 0) return ia - ib;
        return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
}

// === Render del grid (UI) ===
function renderGrid(color, size) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => { thead += `<th>${esc(s.text)}</th>`; });
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
        tbody += `<tr data-color-ptav="${c.id}">
            <th class="sp-sticky-left">
                <div class="sp-color">
                    <img class="sp-color__img" alt="" />
                    <span>${esc(c.text)}</span>
                </div>
            </th>`;
        size.options.forEach((s) => {
            tbody += `<td data-size-ptav="${s.id}">
                <div class="sp-cell">
                    <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric"
                           placeholder="0" data-color-ptav="${c.id}" data-size-ptav="${s.id}">
                    <div class="sp-meta">
                        <span class="sp-price"></span>
                        <span class="sp-stock"></span>
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
        <button type="button" class="btn btn-primary sp-add-all">Añadir selección</button>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
}

// === Busca un buen “ancla” y coloca el grid (una sola vez) ===
function mountGrid() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    // Evita duplicados: si existe y está justo después del ancla, no hacemos nada
    const existing = page.querySelector("#sp-matrix");
    if (existing) existing.remove();

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
        document.body.classList.remove("sp-matrix-active");
        return;
    }

    // 1º preferimos ponerlo justo debajo del bloque de atributos
    const attrs = page.querySelector(".js_attributes") || page.querySelector(".o_product_configurator");
    // 2º si no, debajo del precio
    const price = page.querySelector(".product_price, .oe_currency_value")?.closest("div");
    const anchor = attrs || price || page;

    anchor.insertAdjacentHTML("afterend", renderGrid(color, size));
    document.body.classList.add("sp-matrix-active");

    // En este paso: botón “Añadir selección” -> carrito
    wireCartButton(page);

    // (Opcional) En un paso siguiente hidratamos fotos/precio/stock por variante.
}

// === Botón añadir selección -> /shop/cart/update_json ===
function wireCartButton(page) {
    const btn = page.querySelector("#sp-matrix .sp-add-all");
    if (!btn) return;
    btn.addEventListener("click", async (ev) => {
        ev.preventDefault();
        const inputs = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
        // De momento no dependemos de variant_id para que no falle nada;
        // añadimos el producto “padre” con las combinaciones actuales.
        // Próximo paso: hidratar variant_id por celda y hacer las llamadas correctas.
        const calls = [];
        inputs.forEach((inp) => {
            const qty = parseFloat(inp.value || "0");
            if (qty > 0) {
                // Fallback mínimo: añade el producto seleccionado (padre) “qty” veces.
                calls.push(fetch("/shop/cart/update_json", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ add_qty: qty }),
                    credentials: "include",
                }));
            }
        });
        if (!calls.length) return;
        try {
            await Promise.all(calls);
            window.location.reload();
        } catch (_) {
            // Silencioso: si falla, no bloqueamos la página
        }
    });
}

// === Observa cambios en atributos (cuando el tema re-renderiza) y rehace el grid sin duplicar ===
function observeAndRemount() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    // Re-montar cuando cambien radios
    page.addEventListener("change", (ev) => {
        if (ev.target.matches('input[type="radio"]')) mountGrid();
    });

    // Extra: si el tema re-dibuja atributos, lo detectamos
    const target = page.querySelector(".js_attributes") || page;
    const obs = new MutationObserver(() => mountGrid());
    obs.observe(target, { childList: true, subtree: true });
}

// === Arranque (solo website product) ===
onReady(() => {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    mountGrid();
    observeAndRemount();
    // Marca en consola para comprobar carga del asset
    console.log("[SP] product_matrix.js cargado (frontend único, sin duplicados).");
});