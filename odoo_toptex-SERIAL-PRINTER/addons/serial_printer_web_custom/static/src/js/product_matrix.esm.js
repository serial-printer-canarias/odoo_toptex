// SP Matrix (robusto) – inserción segura + 1D/2D
console.log("[SP] product_matrix activo (1D/2D)");

/* ========== Utiles RPC ========== */
const rpc = async (route, params) => {
  const r = await fetch(route, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    credentials: "same-origin",
    body: JSON.stringify({jsonrpc:"2.0", method:"call", params, id: Date.now()}),
  });
  const j = await r.json();
  if (j && "result" in j) return j.result;
  throw new Error("RPC failed " + route);
};
const getCombination = (avIds, root) => {
  const tmplId = parseInt(
    root.querySelector("[data-product-template-id]")?.dataset.productTemplateId ||
    root.querySelector("input[name='product_id']")?.value || "0", 10
  ) || 0;
  const pricelistId = parseInt(
    root.querySelector("[data-pricelist-id]")?.dataset.pricelistId || "0", 10
  ) || 0;
  const params = {
    product_template_id: tmplId || undefined,
    product_id: 0,
    combination: avIds,
    add_qty: 1,
    parent_combination: [],
    pricelist_id: pricelistId || undefined,
  };
  return rpc("/shop/get_combination_info", params)
    .catch(() => rpc("/sale/get_combination_info", params));
};
const getStock = async (variantId) => {
  const res = await rpc("/web/dataset/call_kw", {
    model: "product.product", method: "read",
    args: [[variantId], ["qty_available"]], kwargs: {},
  });
  return (res && res[0] && typeof res[0].qty_available === "number") ? res[0].qty_available : null;
};
const addToCart = (productId, qty) =>
  rpc("/shop/cart/update_json", { product_id: productId, add_qty: qty, display: false });

const fmtPrice = (v) => {
  try {
    const lang = document.documentElement.lang || "es-ES";
    const curr = document.querySelector("[data-website-currency-code]")?.dataset.websiteCurrencyCode || "EUR";
    return new Intl.NumberFormat(lang, {style:"currency", currency: curr}).format(v);
  } catch { return (Math.round(v*100)/100).toFixed(2); }
};

/* ========== Estilos mínimos inyectados (no tocar SCSS) ========== */
const injectCSS = () => {
  if (document.getElementById("sp-matrix-css")) return;
  const css = `
    #sp-matrix{margin-top:1rem}
    .sp-matrix__table{width:100%;border-collapse:separate;border-spacing:8px}
    .sp-matrix__table th,.sp-matrix__table td{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:.75rem;vertical-align:middle}
    .sp-sticky-left{position:sticky;left:0;background:#fff;box-shadow:1px 0 0 #e5e7eb}
    .sp-color{display:flex;align-items:center;gap:.5rem}
    .sp-color__img{width:48px;height:48px;object-fit:cover;border-radius:8px;background:#f3f4f6}
    .sp-cell{display:flex;flex-direction:column;gap:.35rem}
    .sp-qty{width:100%;max-width:120px;border:1px solid #d1d5db;border-radius:10px;padding:.35rem .5rem;text-align:center}
    .sp-meta{display:flex;justify-content:space-between;gap:.5rem;font-size:.85rem;color:#374151}
    .sp-unavailable{opacity:.45}
  `;
  const s = document.createElement("style");
  s.id = "sp-matrix-css"; s.textContent = css; document.head.appendChild(s);
};

/* ========== Detección de atributos (muy tolerante) ========== */
const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n||"");
const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n||"");

const getText = (el, selArr) => {
  for (const sel of selArr) {
    const t = el.querySelector(sel)?.textContent?.trim();
    if (t) return t;
  }
  return "";
};
const num = (v) => { const n = parseInt(String(v||"").replace(/[^\d]/g,""),10); return Number.isFinite(n)?n:0; };

const collectOptions = (container) => {
  // inputs con múltiples data-*
  let opts = Array.from(container.querySelectorAll("input[type='radio'],input[type='checkbox']")).map(inp => {
    const id = num(
      inp.dataset.valueId ?? inp.dataset.attributeValueId ?? inp.dataset.attribute_value_id ??
      inp.dataset.productAttributeValueId ?? inp.value
    );
    if (!id) return null;
    const label = (inp.closest("label")?.textContent || inp.title || "").trim();
    return { id, name: label || String(id) };
  }).filter(Boolean);

  // nodos con data-value-id
  if (!opts.length) {
    opts = Array.from(container.querySelectorAll("[data-value-id]")).map(n => {
      const id = num(n.dataset.valueId);
      const label = getText(n, [".o_wsale_attribute_value_name",".name",".label","label"]) || n.textContent.trim();
      return id ? { id, name: label || String(id) } : null;
    }).filter(Boolean);
  }
  // dedupe
  const seen = new Set(); return opts.filter(o => !seen.has(o.id) && seen.add(o.id));
};

const parseBlocks = (root) => {
  const out = [];
  const containers = root.querySelectorAll(
    "[data-attribute_name], [data-attribute-id], [data-attribute_id], .o_wsale_product_attribute, .js_attribute, .variant_attribute"
  );
  containers.forEach(el => {
    const name =
      el.getAttribute("data-attribute_name") ||
      el.getAttribute("data-attribute-id") ||
      el.getAttribute("data-attribute_id") ||
      getText(el, [".o_wsale_attribute_name",".attribute_name",".attr_name",".label",".name"]) ||
      "";
    const options = collectOptions(el);
    if (options.length) out.push({ name: name.trim(), options, el });
  });
  console.log("[SP] atributos detectados:", out.map(b => ({name:b.name, n:b.options.length})));
  return out;
};

/* ========== Inserción segura (después si hay precio; si no, dentro del bloque info) ========== */
const placeMatrix = (page, wrap) => {
  const afterSel = [".product_price", ".o_wsale_product_information .product_price"];
  for (const s of afterSel) {
    const a = page.querySelector(s);
    if (a) { a.insertAdjacentElement("afterend", wrap); console.log("[SP] insertado AFTER", s); return; }
  }
  const insideSel = [".o_wsale_product_information", "#product_details", ".product_detail_main", ".o_wsale_product_page .container"];
  for (const s of insideSel) {
    const c = page.querySelector(s);
    if (c) { c.appendChild(wrap); console.log("[SP] insertado APPEND dentro de", s); return; }
  }
  page.appendChild(wrap); // último recurso (nunca usar .after sobre la página)
  console.log("[SP] insertado APPEND en page (fallback)");
};

/* ========== Construcción 1D/2D ========== */
const build = async (page) => {
  if (page.querySelector("#sp-matrix")) return;

  const blocks = parseBlocks(page);
  if (!blocks.length) {
    // aviso visual para saber que no encontró nada
    const b = document.createElement("div");
    b.style.cssText = "margin:.5rem 0;padding:.5rem .75rem;border:1px dashed #f59e0b;color:#92400e;background:#fffbeb;border-radius:8px";
    b.textContent = "SP Matrix: no se detectaron atributos en esta página.";
    (page.querySelector(".o_wsale_product_information")||page).prepend(b);
    return;
  }

  let rows = blocks.find(b => isColor(b.name)) || blocks[0];
  let cols = blocks.find(b => isSize(b.name))  || blocks[1];
  let oneD = false;
  if (!cols) { oneD = true; cols = { name: "One Size", options: [{ id: null, name: "One Size" }] }; }

  const wrap = document.createElement("div");
  wrap.id = "sp-matrix"; wrap.className = "sp-matrix o-pt-3";
  placeMatrix(page, wrap);

  const table = document.createElement("table"); table.className = "sp-matrix__table";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr><th class="sp-sticky-left">${rows.name || "Color"}</th>${
    cols.options.map(o=>`<th>${(o.name||"").replace(/</g,"&lt;")}</th>`).join("")
  }</tr>`;
  const tbody = document.createElement("tbody");

  for (const r of rows.options) {
    const tr = document.createElement("tr");
    tr.dataset.rowId = String(r.id);
    tr.innerHTML = `
      <th class="sp-sticky-left">
        <div class="sp-color">
          <img class="sp-color__img" alt="">
          <span class="sp-color__name">${(r.name||"").replace(/</g,"&lt;")}</span>
        </div>
      </th>`;
    for (const c of cols.options) {
      const td = document.createElement("td");
      if (c.id !== null) td.dataset.colId = String(c.id);
      td.innerHTML = `
        <div class="sp-cell">
          <input type="number" min="0" step="1" class="sp-qty"
                 data-row-id="${r.id}" ${c.id!==null ? `data-col-id="${c.id}"` : ""}>
          <div class="sp-meta"><span class="sp-price"></span><span class="sp-stock"></span></div>
        </div>`;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(thead); table.appendChild(tbody);
  wrap.appendChild(table);

  const btn = document.createElement("button");
  btn.type = "button"; btn.className = "btn btn-primary mt-2 sp-add";
  btn.textContent = "Añadir selección";
  wrap.appendChild(btn);

  // Hidratar celdas
  const cells = Array.from(wrap.querySelectorAll("td"));
  const queue = cells.slice();
  const workers = new Array(6).fill(0).map(async function run() {
    while (queue.length) {
      const td = queue.shift();
      const rowId = parseInt(td.closest("tr")?.dataset.rowId || "0", 10);
      const colId = td.dataset.colId ? parseInt(td.dataset.colId, 10) : null;
      const av = (colId===null) ? [rowId] : [rowId, colId];
      try {
        const info = await getCombination(av, page);
        if (!info || !info.product_id) { td.classList.add("sp-unavailable"); continue; }
        td.querySelector(".sp-qty").dataset.variantId = String(info.product_id);
        if (typeof info.price === "number") td.querySelector(".sp-price").textContent = fmtPrice(info.price);
        let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
        if (stock === null) stock = await getStock(info.product_id);
        if (stock !== null) td.querySelector(".sp-stock").textContent = `Stock: ${stock}`;
        const img = td.closest("tr").querySelector(".sp-color__img");
        if (img && !img.src) img.src = `/web/image/product.product/${info.product_id}/image_128`;
      } catch { td.classList.add("sp-unavailable"); }
    }
  });
  await Promise.all(workers);

  btn.addEventListener("click", async (ev) => {
    ev.preventDefault();
    const calls = [];
    wrap.querySelectorAll(".sp-qty").forEach(inp => {
      const q = parseFloat(inp.value || "0");
      const pid = parseInt(inp.dataset.variantId || "0", 10);
      if (q > 0 && pid) calls.push(addToCart(pid, q));
    });
    if (!calls.length) return;
    await Promise.all(calls);
    window.location.reload();
  });

  // herramientas de depuración
  window.__SP = window.__SP || {};
  window.__SP.debug = {
    blocks: () => parseBlocks(page),
    where: wrap.parentElement,
  };
  console.log("[SP] matriz construida ✔", wrap);
};

/* ========== Arranque + observador ========== */
const start = () => {
  injectCSS();
  const page = document.querySelector(".o_wsale_product_page") || document.body;
  build(page);
  const mo = new MutationObserver(() => build(page));
  mo.observe(page, {childList:true, subtree:true});
};
document.addEventListener("DOMContentLoaded", start);