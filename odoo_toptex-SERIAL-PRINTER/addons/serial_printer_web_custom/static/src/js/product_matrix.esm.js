// Matriz ESM – soporte 1D (un solo atributo) y 2D (dos atributos)
console.log("[SP] product_matrix activo (1D/2D)");

// -------- RPC helpers --------
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

// -------- Detección de bloques --------
const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n||"");
const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n||"");

/** Devuelve [{name, options:[{id,name}], el}] */
const parseBlocks = (root) => {
  const out = [];

  // 1) Estándar con data-attribute_name
  root.querySelectorAll("[data-attribute_name]").forEach(el => {
    const name = (el.getAttribute("data-attribute_name") || "").trim();
    const options = Array.from(el.querySelectorAll("input[type='radio']")).map(inp => {
      const id = parseInt(
        inp.dataset.valueId || inp.dataset.attributeValueId ||
        inp.dataset.attribute_value_id || inp.value || "0", 10
      );
      if (!id) return null;
      const label = (inp.closest("label")?.textContent || inp.title || "").trim();
      return { id, name: label };
    }).filter(Boolean);
    if (options.length) out.push({ name, options, el });
  });

  // 2) Fallback genérico
  if (!out.length) {
    root.querySelectorAll(".js_attribute, .o_wsale_product_attribute, .variant_attribute")
      .forEach(el => {
        const name = (el.querySelector(".attribute_name,.o_wsale_attribute_name,.attr_name")?.textContent || "").trim();
        const options = Array.from(el.querySelectorAll("input[type='radio']")).map(inp => {
          const id = parseInt(inp.dataset.valueId || inp.value || "0", 10);
          if (!id) return null;
          const label = (inp.closest("label")?.textContent || inp.title || "").trim();
          return { id, name: label };
        }).filter(Boolean);
        if (name && options.length) out.push({ name, options, el });
      });
  }

  console.log("[SP] atributos:", out.map(b => ({name:b.name, n:b.options.length})));
  return out;
};

// -------- Ancla para insertar --------
const pickAnchor = (root) => {
  const selectors = [
    ".product_price",
    ".o_wsale_product_information .product_price",
    ".o_wsale_product_information",
    "#product_details",
    ".o_wsale_product_page .container"
  ];
  for (const s of selectors) { const el = root.querySelector(s); if (el) return el; }
  return root;
};

// -------- Construcción 1D/2D --------
const build = async (page) => {
  if (page.querySelector("#sp-matrix")) return;

  const blocks = parseBlocks(page);
  if (!blocks.length) return;

  // Elegir dimensiones
  let rows = blocks.find(b => isColor(b.name)) || blocks[0];
  let cols = blocks.find(b => isSize(b.name))  || blocks[1];

  // Si sólo hay 1 bloque, fabricamos columna "One Size"
  let oneD = false;
  if (!cols) {
    oneD = true;
    cols = { name: "One Size", options: [{ id: null, name: "One Size" }] };
  }

  const anchor = pickAnchor(page);
  const wrap = document.createElement("div");
  wrap.id = "sp-matrix";
  wrap.className = "sp-matrix o-pt-3";
  anchor.after(wrap);

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
          <span class="sp-color__name">${(r.name||"").replace(/<|>/g, m => m === "<" ? "&lt;" : "&gt;")}</span>
        </div>
      </th>`;
    for (const c of cols.options) {
      const td = document.createElement("td");
      if (c.id !== null) td.dataset.colId = String(c.id);
      td.innerHTML = `
        <div class="sp-cell">
          <input type="number" min="0" step="1" class="sp-qty"
                 data-row-id="${r.id}" ${c.id!==null ? `data-col-id="${c.id}"` : ""}>
          <div class="sp-meta">
            <span class="sp-price"></span>
            <span class="sp-stock"></span>
          </div>
        </div>`;
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(thead); table.appendChild(tbody);
  wrap.appendChild(table);

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "btn btn-primary mt-2 sp-add";
  btn.textContent = "Añadir selección";
  wrap.appendChild(btn);

  // Hidratar
  const cells = Array.from(wrap.querySelectorAll("td"));
  const queue = cells.slice();
  const workers = new Array(6).fill(0).map(async function run() {
    while (queue.length) {
      const td = queue.shift();
      const rowId = parseInt(td.closest("tr")?.dataset.rowId || "0", 10);
      const colId = td.dataset.colId ? parseInt(td.dataset.colId, 10) : null;
      const av = oneD ? [rowId] : [rowId, colId];
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
      } catch {
        td.classList.add("sp-unavailable");
      }
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

  // debug hooks
  window.__SP = window.__SP || {};
  window.__SP.debug = {
    blocks: () => parseBlocks(page),
    oneD
  };
  console.log("[SP] matriz construida ✔ (", oneD ? "1 atributo" : "2 atributos", ")");
};

// Arranque + observar cambios dinámicos
const start = () => {
  const page = document.querySelector(".o_wsale_product_page") || document.body;
  build(page);
  const mo = new MutationObserver(() => build(page));
  mo.observe(page, {childList:true, subtree:true});
};
document.addEventListener("DOMContentLoaded", start);