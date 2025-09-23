// Matriz simple; ESM puro; sin odoo.define ni dependencias AMD
console.log("[SP] product_matrix activo");

const rpc = async (route, params) => {
  const r = await fetch(route, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    credentials: "same-origin",
    body: JSON.stringify({jsonrpc:"2.0", method:"call", params, id: Date.now()}),
  });
  const j = await r.json();
  if (j && "result" in j) return j.result;
  throw new Error("RPC failed: " + route);
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
    model: "product.product",
    method: "read",
    args: [[variantId], ["qty_available"]],
    kwargs: {},
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

const isColor = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n||"");
const isSize  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n||"");

const parseBlocks = (root) => {
  const out = [];
  root.querySelectorAll(".js_product .js_attributes [data-attribute_name]").forEach(el => {
    const name = (el.getAttribute("data-attribute_name")||"").trim();
    const options = Array.from(el.querySelectorAll("input[type='radio']")).map(inp => {
      const id = parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0", 10);
      if (!id) return null;
      const label = (inp.closest("label")?.textContent || inp.title || "").trim();
      return {id, name: label};
    }).filter(Boolean);
    if (options.length) out.push({name, options, el});
  });
  return out;
};

const build = async (page) => {
  if (page.querySelector("#sp-matrix")) return;
  const blocks = parseBlocks(page);
  if (blocks.length < 2) return;

  const col = blocks.find(b => isColor(b.name)) || blocks[0];
  const siz = blocks.find(b => isSize(b.name))  || blocks[1];

  const anchor = page.querySelector(".product_price") || page;
  const wrap = document.createElement("div");
  wrap.id = "sp-matrix";
  wrap.className = "sp-matrix o-pt-3";
  anchor.after(wrap);

  const table = document.createElement("table"); table.className = "sp-matrix__table";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr><th class="sp-sticky-left">Color</th>${siz.options.map(o=>`<th>${(o.name||"").replace(/</g,"&lt;")}</th>`).join("")}</tr>`;
  const tbody = document.createElement("tbody");

  for (const c of col.options) {
    const tr = document.createElement("tr");
    tr.dataset.colorId = String(c.id);
    tr.innerHTML = `
      <th class="sp-sticky-left">
        <div class="sp-color">
          <img class="sp-color__img" alt="">
          <span class="sp-color__name">${(c.name||"").replace(/</g,"&lt;")}</span>
        </div>
      </th>`;
    for (const s of siz.options) {
      const td = document.createElement("td");
      td.dataset.sizeId = String(s.id);
      td.innerHTML = `
        <div class="sp-cell">
          <input type="number" min="0" step="1" class="sp-qty" data-color-id="${c.id}" data-size-id="${s.id}">
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

  // Hidratar celdas: variant_id, precio, stock e imagen por color
  const cells = Array.from(wrap.querySelectorAll("td"));
  const queue = cells.slice();
  const workers = new Array(6).fill(0).map(async function run() {
    while (queue.length) {
      const td = queue.shift();
      const colorId = parseInt(td.closest("tr")?.dataset.colorId || "0", 10);
      const sizeId  = parseInt(td.dataset.sizeId || "0", 10);
      if (!colorId || !sizeId) continue;

      try {
        const info = await getCombination([colorId, sizeId], page);
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
};

document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector(".o_wsale_product_page");
  if (page) build(page);
});