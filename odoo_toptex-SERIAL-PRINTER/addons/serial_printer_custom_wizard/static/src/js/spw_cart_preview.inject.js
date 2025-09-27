/**
 * Muestra miniaturas de TODAS las personalizaciones por línea de carrito
 * sin tocar QWeb. Robusto a recargas parciales del carrito de Odoo.
 * 
 * Busca las imágenes por este orden:
 *  1) window.spwPreviews[lineId] (si tu wizard ya lo deja en global)
 *  2) localStorage["spw_previews_" + lineId] (JSON array)
 *  3) GET /spw/cart/preview?line_id=... => { images: [url, ...] }  (opcional)
 *
 * No rompe el menú ni los filtros porque no toca website.layout ni products.
 */
(function () {
  "use strict";

  const isCart = () => location.pathname.indexOf("/shop/cart") !== -1;
  if (!isCart()) return;

  function getLineId(tr) {
    return (
      tr.getAttribute("data-line-id") ||
      tr.dataset.lineId ||
      (tr.querySelector('[name="line_id"]') || {}).value ||
      tr.getAttribute("data-id") ||
      ""
    );
  }

  async function fetchPreviews(lineId) {
    // 1) variable global (si tu customizer ya la rellena)
    if (window.spwPreviews && window.spwPreviews[lineId]) {
      const arr = window.spwPreviews[lineId];
      return Array.isArray(arr) ? arr : [];
    }

    // 2) localStorage por línea
    try {
      const raw = localStorage.getItem("spw_previews_" + lineId);
      if (raw) {
        const arr = JSON.parse(raw);
        if (Array.isArray(arr)) return arr;
      }
    } catch (e) {}

    // 3) endpoint opcional
    try {
      const res = await fetch(`/spw/cart/preview?line_id=${encodeURIComponent(lineId)}`, {
        credentials: "same-origin",
        headers: { "Accept": "application/json" },
      });
      if (res.ok) {
        const j = await res.json();
        if (j && Array.isArray(j.images)) return j.images;
      }
    } catch (e) {}

    return [];
  }

  function ensureContainer(tr) {
    let host = tr.querySelector(".spw-preview-wrap");
    if (host) {
      host.innerHTML = "";
      return host;
    }
    host = document.createElement("div");
    host.className = "spw-preview-wrap";

    // Colocar debajo del nombre del producto (fallback al <tr>)
    const nameCell = tr.querySelector(".td-product_name, .product_name, td:first-child");
    (nameCell || tr).appendChild(host);
    return host;
  }

  async function renderLine(tr) {
    const lineId = getLineId(tr);
    if (!lineId) return;
    const images = await fetchPreviews(lineId);
    const host = ensureContainer(tr);
    host.innerHTML = "";

    // Pintar TODAS las personalizaciones (múltiples)
    images.forEach((url, idx) => {
      if (!url) return;
      const img = document.createElement("img");
      img.className = "spw-preview-thumb";
      img.alt = `Personalización ${idx + 1}`;
      img.loading = "lazy";
      img.decoding = "async";
      img.referrerPolicy = "no-referrer-when-downgrade";
      img.src = url;
      host.appendChild(img);
    });
  }

  function renderAll() {
    const rows = document.querySelectorAll(".oe_website_sale .cart_line, .oe_cart table tbody tr");
    rows.forEach(renderLine);
  }

  // Observar cambios dinámicos del carrito
  const observer = new MutationObserver((muts) => {
    if (muts.some(m => m.type === "childList" && (m.addedNodes.length || m.removedNodes.length))) {
      renderAll();
    }
  });

  window.addEventListener("load", () => {
    if (!isCart()) return;
    const target = document.querySelector(".oe_website_sale, .oe_cart, body");
    if (target) observer.observe(target, { subtree: true, childList: true });
    renderAll();
  });

  // Hooks típicos de Odoo / propios del wizard
  window.addEventListener("cart_updated", renderAll);
  window.addEventListener("spw:customization:added", renderAll);
})();