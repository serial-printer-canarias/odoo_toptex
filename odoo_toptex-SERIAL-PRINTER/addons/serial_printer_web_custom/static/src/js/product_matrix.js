/** @odoo-module **/

/* ===================== DOM READY ===================== */
function onReady(fn) {
  if (document.readyState !== "loading") fn();
  else document.addEventListener("DOMContentLoaded", fn);
}

/* ===================== ESTADO ===================== */
const SP = (window.__SP ||= {
  rendering: false,
  bound: false,
  comboCache: new Map(), // key: tmplId|ptav-ptav -> info
});

/* ===================== UTILES ===================== */
const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const imgUrl = (pid) => `/web/image/product.product/${pid}/image_128`;

function getTemplateId(page) {
  const hid = page.querySelector('input[name="product_template_id"]');
  if (hid?.value) return Number(hid.value);
  const form = page.querySelector('form.o_wsale_product_configurator, form[action*="/shop"]');
  return Number(form?.dataset?.productTemplateId || 0);
}

/* ===================== JSON-RPC NATIVO ===================== */
async function jsonRpc(model, method, args = [], kwargs = {}) {
  const res = await fetch(`/web/dataset/call_kw/${model}/${method}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "call",
      params: { model, method, args, kwargs },
    }),
  });
  if (!res.ok) throw new Error(`${method}: ${res.status}`);
  const data = await res.json();
  if (data.error) throw new Error(data.error.data?.message || method + " error");
  return data.result;
}

/* === Info real de combinación (product_id, precio, stock, imagen) === */
async function getCombinationInfo(tmplId, ptavIds, qty = 1) {
  const key = `${tmplId}|${ptavIds.slice().sort((a,b)=>a-b).join("-")}`;
  if (SP.comboCache.has(key)) return SP.comboCache.get(key);

  let out;
  try {
    const payload = {
      product_template_id: tmplId,
      combination: ptavIds,
      add_qty: qty,
      parent_combination: [],
      only_template: false,
      is_custom: false,
    };
    const res = await jsonRpc("product.template", "get_combination_info_website", [[tmplId], payload]);
    out = {
      ok: true,
      product_id: res.product_id || 0,
      price: res.price ?? res.list_price ?? null,
      stock: res.stock_qty ?? res.availability ?? null,
      image: res.image_url || (res.product_id ? imgUrl(res.product_id) : null),
    };
  } catch (e) {
    out = { ok: false, error: e.message };
  }
  SP.comboCache.set(key, out);
  return out;
}

/* ===================== ATRIBUTOS ===================== */
function getAttributeBlocks(scope) {
  const blocks = [];
  const containers = Array.from(
    scope.querySelectorAll('[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div')
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
      const id = Number(inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || 0);
      if (!id) return null;
      const text = (inp.closest("label")?.textContent || inp.getAttribute("title") || "")
        .replace(/\s+/g, " ").trim();
      return { id, text, _radio: inp };
    }).filter(Boolean);

    if (options.length) blocks.push({ name, el, options });
  });

  const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
  const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));
  if (size) size.options = sortSizes(size.options);
  return { color, size };
}

function sortSizes(opts) {
  const std = ["2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL"];
  return [...opts].sort((a,b)=>{
    const na = parseFloat(a.text), nb = parseFloat(b.text);
    if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
    const ia = std.indexOf(a.text.toUpperCase()), ib = std.indexOf(b.text.toUpperCase());
    if (ia>=0 && ib>=0) return ia - ib;
    return a.text.localeCompare(b.text, undefined, { numeric: true });
  });
}

/* ===================== RENDER HTML ===================== */
function renderGrid(color, size) {
  let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
  size.options.forEach((s) => (thead += `<th>${esc(s.text)}</th>`));
  thead += "</tr></thead>";

  let tbody = "<tbody>";
  color.options.forEach((c) => {
    tbody += `<tr data-row-color="${c.id}">
      <th class="sp-sticky-left">
        <div class="sp-color">
          <img class="sp-color__img" alt="">
          <span>${esc(c.text)}</span>
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

  return `
    <div id="sp-matrix" class="sp-matrix-box">
      <table class="sp-matrix__table">${thead}${tbody}</table>
      <div class="sp-actions">
        <button id="sp-add-selection" type="button" class="btn btn-primary">Añadir selección</button>
      </div>
      <p class="sp-help">Indica cantidades por color y talla.</p>
    </div>
  `;
}

/* ===================== ANCLAS (POSICIÓN) ===================== */
function getAnchors(page) {
  const info  = page.querySelector(".o_wsale_product_information") || page;
  const attrs = info.querySelector(".js_attributes");
  let actions =
    info.querySelector(".o_wsale_product_actions") ||
    info.querySelector('button[name="add_to_cart"]')?.closest(".o_wsale_product_actions") ||
    info.querySelector('form[action*="/shop/cart"]')?.closest(".o_wsale_product_actions");
  return { info, attrs, actions };
}

/* ===================== HIDRATAR (IMG / PRECIO / STOCK) ===================== */
async function hydrateMatrix(page, color, size) {
  const tmplId = getTemplateId(page);
  if (!tmplId) return;

  const firstSize = size.options[0]?.id;

  // Miniatura por fila (color)
  for (const c of color.options) {
    const row = page.querySelector(`tr[data-row-color="${c.id}"]`);
    const img = row?.querySelector(".sp-color__img");
    if (!img) continue;
    const combo = [c.id].concat(firstSize ? [firstSize] : []);
    const info = await getCombinationInfo(tmplId, combo, 1);
    if (info?.product_id) img.src = info.image || imgUrl(info.product_id);
  }

  // Datos por celda
  const cells = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
  for (const input of cells) {
    const cId = Number(input.dataset.color);
    const sId = Number(input.dataset.size);
    const info = await getCombinationInfo(tmplId, [cId, sId], 1);
    if (info?.product_id) input.dataset.productId = String(info.product_id);

    const meta = input.parentElement.querySelector(".sp-meta");
    const bits = [];
    if (info?.price != null) bits.push(`Precio: ${info.price}`);
    if (info?.stock != null) bits.push(`Stock: ${info.stock}`);
    meta.textContent = bits.join(" · ");
  }
}

/* ===================== AÑADIR SELECCIÓN ===================== */
async function addSelection(page) {
  const items = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"))
    .map((i) => ({ pid: Number(i.dataset.productId || 0), qty: Number(i.value || 0) }))
    .filter((x) => x.pid && x.qty > 0);

  if (!items.length) return;

  // JSON primero
  for (const it of items) {
    try {
      await fetch("/shop/cart/update_json", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ product_id: it.pid, add_qty: it.qty }),
      });
    } catch (_) {}
    await sleep(60);
  }
  // Fallback clásico
  for (const it of items) {
    try {
      const fd = new FormData();
      fd.append("product_id", String(it.pid));
      fd.append("add_qty", String(it.qty));
      await fetch("/shop/cart/update", { method: "POST", body: fd, credentials: "same-origin" });
    } catch (_) {}
    await sleep(60);
  }

  document.dispatchEvent(new Event("sp:cart-updated"));
}

/* ===================== ENSURE / RENDER ===================== */
async function ensureMatrix() {
  if (SP.rendering) return;
  SP.rendering = true;

  const page = document.querySelector(".o_wsale_product_page");
  if (!page) { SP.rendering = false; return; }

  // elimina duplicados
  page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

  const { color, size } = getAttributeBlocks(page);
  if (!color || !size) {
    document.body.classList.remove("sp-matrix-active");
    SP.rendering = false;
    return;
  }

  const html = renderGrid(color, size);
  const { info, attrs, actions } = getAnchors(page);

  if (actions && actions.parentNode)      actions.insertAdjacentHTML("beforebegin", html);
  else if (attrs && attrs.parentNode)     attrs.insertAdjacentHTML("afterend", html);
  else                                    info.insertAdjacentHTML("beforeend", html);

  document.body.classList.add("sp-matrix-active");

  await hydrateMatrix(page, color, size);

  const btn = page.querySelector("#sp-add-selection");
  if (btn) btn.addEventListener("click", () => addSelection(page));

  if (!SP.bound) {
    SP.bound = true;
    page.addEventListener("change", (ev) => {
      if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
  }
  SP.rendering = false;
}

/* ===================== START ===================== */
onReady(ensureMatrix);