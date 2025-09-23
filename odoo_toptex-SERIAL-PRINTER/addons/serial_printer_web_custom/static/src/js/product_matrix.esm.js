// No AMD, no imports: ESM puro y DOM + fetch JSON-RPC
console.log("[SP] product_matrix activo");

const rpc = async (route, params) => {
  const res = await fetch(route, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({jsonrpc: "2.0", method: "call", params, id: Date.now()}),
    credentials: "same-origin",
  });
  const j = await res.json();
  if (j && j.result !== undefined) return j.result;
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

const getStock = async (productId) => {
  const r = await rpc("/web/dataset/call_kw", {
    model: "product.product",
    method: "read",
    args: [[productId], ["qty_available"]],
    kwargs: {},
  });
  return (r && r[0] && typeof r[0].qty_available === "number") ? r[0].qty_available : null;
};

const addToCart = (productId, qty) =>
  rpc("/shop/cart/update_json", {product_id: productId, add_qty: qty, display: false});

const fmtPrice = (v) => {
  try {
    const lang = document.documentElement.lang || "es-ES";
    const curr = document.querySelector("[data-website-currency-code]")?.dataset.websiteCurrencyCode || "EUR";
    return new Intl.NumberFormat(lang, {style: "currency", currency: curr}).format(v);
  } catch {
    return (Math.round(v * 100) / 100).toFixed(2);
  }
};

const isColorName = n => /color|couleur|farbe|colou?r|colore|kleur/i.test(n || "");
const isSizeName  = n => /size|talla|taille|größe|grosse|taglia|maat/i.test(n || "");

const parseAttributeBlocks = (root) => {
  const blocks = [];
  root.querySelectorAll(".js_product .js_attributes [data-attribute_name]").forEach(block => {
    const name = (block.getAttribute("data-attribute_name") || "").trim();
    const options = Array.from(block.querySelectorAll("input[type='radio']")).map(inp => {
      const id = parseInt(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0", 10);
      if (!id) return null;
      const label = (inp.closest("label")?.textContent || inp.title || "").trim();
      return {id, name: label};
    }).filter(Boolean);
    if (options.length) blocks.push({name, options, el: block});
  });
  return blocks;
};

const buildMatrix = async (root) => {
  const page = root.closest(".o_wsale_product_page") || root;
  if (!page || page.querySelector("#sp-matrix")) return;

  const blocks = parseAttributeBlocks(page);
  if (blocks.length < 2) return;

  const color = blocks.find(b => isColorName(b.name)) || blocks[0];
  const size  = blocks.find(b => isSizeName(b.name))  || blocks[1];
  if (!color || !size) return;

  const anchor = page.querySelector(".product_price") || page;
  const wrap   = document.createElement("div");
  wrap.id = "sp-matrix";
  wrap.className = "sp-matrix o-pt-3";
  anchor.after(wrap);

  const table = document.createElement("table"); table.className = "sp-matrix__table";
  const thead = document.createElement("thead");
  thead.innerHTML = `<tr><th class="sp-sticky-left">Color</th>${size.options.map(o=>`<th>${(o.name||"").replace(/</g,"&lt;")}</th>`).join("")}</tr>`;
  const tbody = document.createElement("tbody");

  for (const c of color.options) {
    const tr = document.createElement("tr");
    tr.dataset.colorId = String(c.id);
    tr.innerHTML = `
      <th class="sp-sticky-left">
        <div class="sp-color">
          <img class="sp-color__img" alt="">
          <span class="sp-color__name">${(c.name||"").replace(/</g,"&lt;")}</span>
        </div>
      </th>
    `;
    for (const s of size.options) {
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
  btn.className = "btn btn-primary mt-2 sp-add-to-cart";
  btn.textContent = "Añadir selección";
  wrap.appendChild(btn);

  // Hidratar precio/stock/imagen
  const cells = [...wrap.querySelectorAll("td")];
  const queue = cells.slice();
  const workers = new Array(6).fill(0).map(async function run() {
    while (queue.length) {
      const td = queue.shift();
      const colorId = parseInt(td.dataset.colorId || td.closest("tr")?.dataset.colorId || "0", 10);
      const sizeId  = parseInt(td.dataset.sizeId || "0", 10);
      if (!colorId || !sizeId) continue;

      try {
        const info = await getCombination([colorId, sizeId], page);
        if (!info || !info.product_id) { td.classList.add("sp-unavailable"); continue; }

        const input = td.querySelector(".sp-qty");
        input.dataset.variantId = String(info.product_id);

        if (typeof info.price === "number") {
          td.querySelector(".sp-price").textContent = fmtPrice(info.price);
        }

        let stock = (info.stock_quantity !== undefined) ? info.stock_quantity : null;
        if (stock === null) stock = await getStock(info.product_id);
        if (stock !== null) td.querySelector(".sp-stock").textContent = `Stock: ${stock}`;

        const rowImg = td.closest("tr").querySelector(".sp-color__img");
        if (rowImg && !rowImg.src) {
          rowImg.src = `/web/image/product.product/${info.product_id}/image_128`;
        }
      } catch (e) {
        td.classList.add("sp-unavailable");
      }
    }
  });
  await Promise.all(workers);

  // Añadir al carrito
  btn.addEventListener("click", async (ev) => {
    ev.preventDefault();
    const calls = [];
    wrap.querySelectorAll(".sp-qty").forEach(inp => {
      const qty = parseFloat(inp.value || "0");
      const pid = parseInt(inp.dataset.variantId || "0", 10);
      if (qty > 0 && pid) calls.push(addToCart(pid, qty));
    });
    if (!calls.length) return;
    await Promise.all(calls);
    window.location.reload();
  });
};

document.addEventListener("DOMContentLoaded", () => {
  const page = document.querySelector(".o_wsale_product_page");
  if (page) buildMatrix(page);
});