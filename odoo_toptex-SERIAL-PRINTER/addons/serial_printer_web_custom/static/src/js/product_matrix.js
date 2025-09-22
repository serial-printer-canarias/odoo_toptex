/** @odoo-module **/

/* ---------------- DOM READY ---------------- */
function onReady(fn) {
  if (document.readyState !== "loading") fn();
  else document.addEventListener("DOMContentLoaded", fn);
}

/* ---------------- ESTADO GLOBAL ---------------- */
const SP = (window.__SP ||= {
  rendering: false,
  bound: false,
  comboCache: new Map(), // key: tmplId -> combos {items:[], index:{}}
});

/* ---------------- UTILES ---------------- */
const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c]));
const imgUrl = (pid) => `/web/image/product.product/${pid}/image_128`;
const money = (v) => (v == null ? "" : `${v}`);

/* --------- ids y anclajes --------- */
function getTemplateId(page) {
  const hid = page.querySelector('input[name="product_template_id"]');
  if (hid?.value) return Number(hid.value);
  const form = page.querySelector('form.o_wsale_product_configurator, form[action*="/shop"]');
  return Number(form?.dataset?.productTemplateId || 0);
}
function getAnchors(page) {
  const info  = page.querySelector(".o_wsale_product_information") || page;
  const attrs = info.querySelector(".js_attributes");
  const actions = info.querySelector(".o_wsale_product_actions")
    || info.querySelector('button[name="add_to_cart"]')?.closest(".o_wsale_product_actions")
    || info.querySelector('form[action*="/shop/cart"]')?.closest(".o_wsale_product_actions");
  return { info, attrs, actions };
}

/* --------- ATRIBUTOS (Color/Talla) --------- */
function getAttributeBlocks(scope) {
  const blocks = [];
  const containers = Array.from(
    scope.querySelectorAll('[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div')
  );
  containers.forEach((el) => {
    const name = (
      el.getAttribute("data-attribute_name") ||
      el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
      el.getAttribute("name") || ""
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

/* --------- RENDER HTML --------- */
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

/* --------- CARGA DE COMBINACIONES (controlador propio) --------- */
async function fetchCombos(tmplId) {
  if (SP.comboCache.has(tmplId)) return SP.comboCache.get(tmplId);
  const res = await fetch(`/sp/matrix/combos/${tmplId}`, {
    method: "POST",
    credentials: "same-origin",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify({}),
  });
  const data = await res.json();
  const out = { items: [], index: new Map() };
  if (data && data.ok && Array.isArray(data.items)) {
    out.items = data.items;
  }
  SP.comboCache.set(tmplId, out);
  return out;
}

/* --------- VINCULAR MINIATURAS + PRECIO/STOCK --------- */
async function hydrateMatrix(page, color, size) {
  const tmplId = getTemplateId(page);
  if (!tmplId) return;

  const combos = await fetchCombos(tmplId);
  if (!combos.items.length) return;

  // mapa rápido color-ptav y talla-ptav
  const colorSet = new Set(color.options.map(o => o.id));
  const sizeSet  = new Set(size.options.map(o => o.id));

  // indexar por "colorId-sizeId"
  const key = (c,s) => `${c}-${s}`;
  const index = new Map();
  for (const it of combos.items) {
    const cId = it.ptav_ids.find((v) => colorSet.has(v));
    const sId = it.ptav_ids.find((v) => sizeSet.has(v));
    if (cId && sId) index.set(key(cId,sId), it);
  }

  // miniatura por fila
  for (const c of color.options) {
    const row = page.querySelector(`tr[data-row-color="${c.id}"]`);
    const img = row?.querySelector(".sp-color__img");
    if (!img) continue;
    // usa cualquier talla disponible de ese color
    let found = null;
    for (const s of size.options) {
      const it = index.get(key(c.id, s.id));
      if (it) { found = it; break; }
    }
    if (found?.product_id) img.src = found.image || imgUrl(found.product_id);
  }

  // datos por celda
  const inputs = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"));
  for (const inp of inputs) {
    const cId = Number(inp.dataset.color);
    const sId = Number(inp.dataset.size);
    const it = index.get(key(cId, sId));
    const meta = inp.parentElement.querySelector(".sp-meta");
    if (it?.product_id) {
      inp.dataset.productId = String(it.product_id);
      meta.textContent = `Precio: ${money(it.price)} · Stock: ${it.stock ?? "-"}`;
    } else {
      delete inp.dataset.productId;
      meta.textContent = "No disponible";
    }
  }
}

/* --------- AÑADIR SELECCIÓN (batch) --------- */
async function addSelection(page) {
  const lines = Array.from(page.querySelectorAll("#sp-matrix .sp-qty"))
    .map((i) => ({ product_id: Number(i.dataset.productId || 0), qty: Number(i.value || 0) }))
    .filter((x) => x.product_id && x.qty > 0);

  if (!lines.length) return;

  const res = await fetch("/sp/cart/add_batch", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lines }),
  });
  const data = await res.json().catch(() => ({}));
  if (data && data.ok) {
    document.dispatchEvent(new Event("sp:cart-updated"));
    // opcional: refrescar minicart o recargar
    window.location.reload();
  }
}

/* --------- ENSURE (pintado sin duplicados) --------- */
async function ensureMatrix() {
  if (SP.rendering) return;
  SP.rendering = true;

  const page = document.querySelector(".o_wsale_product_page");
  if (!page) { SP.rendering = false; return; }

  // remove duplicados
  page.querySelectorAll("#sp-matrix").forEach((n) => n.remove());

  const { color, size } = getAttributeBlocks(page);
  if (!color || !size) {
    document.body.classList.remove("sp-matrix-active");
    SP.rendering = false;
    return;
  }

  const html = renderGrid(color, size);
  const { info, attrs, actions } = getAnchors(page);

  // Colocar SIEMPRE justo antes del bloque de acciones (Add to cart)
  if (actions && actions.parentNode) actions.insertAdjacentHTML("beforebegin", html);
  else if (attrs && attrs.parentNode) attrs.insertAdjacentHTML("afterend", html);
  else info.insertAdjacentHTML("beforeend", html);

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

/* --------- START --------- */
onReady(ensureMatrix);