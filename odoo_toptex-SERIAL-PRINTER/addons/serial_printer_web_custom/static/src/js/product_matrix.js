/** @odoo-module **/

(() => {
  "use strict";

  // ---------- Utilidades ----------
  const SLOT_ID = "sp-matrix-slot";

  function onReady(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }
  const $ = (sel, root = document) => root.querySelector(sel);
  const $all = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const esc = (s) =>
    String(s || "").replace(/[&<>"']/g, (m) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[m]);

  function sortSizes(opts) {
    const std = [
      "2XS","XXS","XS","S","M","L","XL","2XL","XXL","3XL","4XL","5XL","6XL","7XL","8XL",
    ];
    return [...opts].sort((a, b) => {
      const na = parseFloat(a.text), nb = parseFloat(b.text);
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
      const ia = std.indexOf(a.text.toUpperCase());
      const ib = std.indexOf(b.text.toUpperCase());
      if (ia > -1 && ib > -1) return ia - ib;
      return a.text.localeCompare(b.text, undefined, { numeric: true });
    });
  }

  // Busca bloques de atributos (color/talla) y recoge radios + text + img de label si existe
  function getAttributeBlocks(scope) {
    const blocks = [];
    const containers = $all(
      '[data-attribute_name], .js_attribute, .o_product_configurator [name], .js_attributes > div',
      scope
    );

    containers.forEach((el) => {
      const name = (
        el.getAttribute("data-attribute_name") ||
        el.querySelector(".attribute_name, legend, .o_attr_title")?.textContent ||
        el.getAttribute("name") ||
        ""
      ).trim().toLowerCase();

      const radios = $all('input[type="radio"]', el);
      if (!radios.length) return;

      const options = radios
        .map((inp) => {
          const id = parseInt(
            inp.dataset.valueId || inp.dataset.attributeValueId || inp.value || "0",
            10
          ) || 0;
          if (!id) return null;
          const label = inp.closest("label") || el.querySelector(`label[for="${inp.id}"]`);
          const text = (label?.textContent || inp.getAttribute("title") || "")
            .replace(/\s+/g, " ")
            .trim();
          const img = label?.querySelector("img")?.getAttribute("src") || null;
          return { id, text, _radio: inp, _label: label, _img: img };
        })
        .filter(Boolean);

      if (options.length) blocks.push({ name, options });
    });

    const color = blocks.find((b) => /(color|colour|colou?r|c[oó]lor)/i.test(b.name));
    const size  = blocks.find((b) => /(size|talla|talle|taille|größe|maat)/i.test(b.name));
    if (size) size.options = sortSizes(size.options);

    return { color, size };
  }

  // Render de la tabla
  function buildGrid(color, size, previousValues) {
    let thead = '<thead><tr><th class="sp-sticky-left">Color</th>';
    size.options.forEach((s) => (thead += `<th>${esc(s.text)}</th>`));
    thead += "</tr></thead>";

    let tbody = "<tbody>";
    color.options.forEach((c) => {
      tbody += `<tr data-color-id="${c.id}">
        <th class="sp-sticky-left">
          <div class="sp-color">
            <img class="sp-color__img" alt="" data-fallback="${esc(c._img || "")}">
            <span>${esc(c.text)}</span>
          </div>
        </th>`;
      size.options.forEach((s) => {
        const key = `${c.id}:${s.id}`;
        const val = previousValues?.[key] ?? "";
        tbody += `<td>
          <div class="sp-cell">
            <input class="sp-qty" type="number" min="0" step="1" inputmode="numeric"
                   placeholder="0" value="${esc(val)}"
                   data-color="${c.id}" data-size="${s.id}">
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
          <button type="button" id="sp-add-selection" class="btn btn-primary o_add_to_cart">Añadir selección</button>
        </div>
        <p class="sp-help">Indica cantidades por color y talla.</p>
      </div>
    `;
  }

  // Guarda cantidades ya escritas para no perderlas en re-render
  function collectCurrentValues(root) {
    const out = {};
    $all("input.sp-qty", root).forEach((inp) => {
      const q = inp.value;
      if (q && Number(q) > 0) out[`${inp.dataset.color}:${inp.dataset.size}`] = q;
    });
    return out;
  }

  // Crea (solo una vez) un slot fijo bajo .js_attributes y re-pinta dentro
  function ensureSlot(page) {
    let slot = $("#" + SLOT_ID, page);
    if (slot) return slot;
    slot = document.createElement("div");
    slot.id = SLOT_ID;
    const attrs = page.querySelector(".js_attributes");
    if (attrs && attrs.parentNode) {
      attrs.parentNode.insertBefore(slot, attrs.nextSibling);
    } else {
      // fallback
      (page.querySelector(".o_wsale_product_information")?.parentNode || page).appendChild(slot);
    }
    return slot;
  }

  let suppressRebuild = false;

  function ensureMatrix() {
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;

    const slot = ensureSlot(page);

    const { color, size } = getAttributeBlocks(page);
    if (!color || !size) {
      slot.innerHTML = "";
      document.body.classList.remove("sp-matrix-active");
      return;
    }

    const prev = collectCurrentValues(slot);
    slot.innerHTML = buildGrid(color, size, prev);
    document.body.classList.add("sp-matrix-active");

    // Miniaturas: usa <img> del label si existe; si no, usa la imagen principal actual.
    $all('tr[data-color-id]', slot).forEach((tr) => {
      const cid = tr.getAttribute("data-color-id");
      const opt = color.options.find((o) => String(o.id) === cid);
      const imgEl = tr.querySelector(".sp-color__img");
      const src = opt ? opt._img : null;
      if (src) {
        imgEl.src = src;
        imgEl.removeAttribute("data-fallback");
      } else {
        const main =
          page.querySelector(".product_detail_img img, .o_website_sale_product_image img, .carousel-item.active img");
        if (main?.src) imgEl.src = main.src;
      }
    });

    // Botón añadir selección
    $("#sp-add-selection", slot)?.addEventListener("click", () =>
      addSelection(page, color, size, slot)
    );
  }

  // Añade cada celda (>0) al carrito usando el formulario nativo de Odoo
  async function addSelection(page, color, size, slot) {
    const rows = $all("input.sp-qty", slot)
      .map((inp) => ({
        qty: parseInt(inp.value, 10) || 0,
        colorId: parseInt(inp.dataset.color, 10),
        sizeId: parseInt(inp.dataset.size, 10),
      }))
      .filter((r) => r.qty > 0);

    if (!rows.length) return;

    const form = page.querySelector('form[action*="/shop/cart"]') || page.querySelector("form");
    if (!form) return;

    const qtyField = form.querySelector('input[name="add_qty"], input[name="quantity"]');

    for (const r of rows) {
      const colorRadio = color.options.find((o) => o.id === r.colorId)?._radio;
      const sizeRadio  = size.options.find((o) => o.id === r.sizeId)?._radio;
      if (!colorRadio || !sizeRadio) continue;

      suppressRebuild = true;
      if (!colorRadio.checked) {
        colorRadio.checked = true;
        colorRadio.dispatchEvent(new Event("change", { bubbles: true }));
      }
      if (!sizeRadio.checked) {
        sizeRadio.checked = true;
        sizeRadio.dispatchEvent(new Event("change", { bubbles: true }));
      }
      suppressRebuild = false;

      const pidInput = form.querySelector('input[name="product_id"]');
      await waitFor(() => pidInput && pidInput.value && pidInput.value !== "0", 1200);

      if (qtyField) {
        qtyField.value = String(r.qty);
        qtyField.dispatchEvent(new Event("change", { bubbles: true }));
      }

      const addBtn =
        form.querySelector(".o_add_to_cart, button[name='add_to_cart'], a.js_add_cart_json");
      if (addBtn) {
        addBtn.click();
        await delay(500); // da tiempo a Odoo a cerrar popup/actualizar
      }
    }

    // limpia entradas
    $all("input.sp-qty", slot).forEach((i) => (i.value = ""));
  }

  const delay = (ms) => new Promise((r) => setTimeout(r, ms));
  async function waitFor(testFn, timeout = 1000, step = 50) {
    const t0 = performance.now();
    while (performance.now() - t0 < timeout) {
      if (testFn()) return true;
      await delay(step);
    }
    return false;
  }

  // ---------- Arranque ----------
  onReady(() => {
    ensureMatrix();
    const page = document.querySelector(".o_wsale_product_page");
    if (!page) return;
    page.addEventListener("change", (ev) => {
      if (suppressRebuild) return;
      if (ev.target.matches('input[type="radio"]')) ensureMatrix();
    });
  });
})();