/** SPW – Envío de una personalización (crea/actualiza línea, guarda metadatos y sube PNG emparejado) */
(function () {
  'use strict';

  /**
   * Llama a esto UNA VEZ por personalización del mismo SKU.
   * - variantId: id de variante (product.product)
   * - qty: cantidad a añadir (default 1)
   * - tech: texto de técnica (p.ej. "Serigrafía")
   * - svgColor: color en formato "#RRGGBB" (o vacío)
   * - notes: observaciones (opcional)
   * - pngDataURL: dataURL "data:image/png;base64,..." de la previsualización (opcional)
   *
   * Devuelve { ok, lineId, i } y redirige al carrito si todo OK.
   */
  async function spwSubmitPersonalization({ variantId, qty = 1, tech = '', svgColor = '', notes = '', pngDataURL = '' }) {
    // 1) crear/actualizar línea y guardar metadatos -> devuelve line_id e índice i
    const metaResp = await fetch('/spw/add_to_cart_meta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        variant_id: Number(variantId) || 0,
        qty: Number(qty) || 1,
        tech: String(tech || '').trim(),
        svg_color: String(svgColor || '').trim(),
        notes: String(notes || '').trim(),
      }),
    });
    const meta = await metaResp.json().catch(() => ({}));
    if (!meta || !meta.ok) {
      throw new Error((meta && meta.message) || 'No se pudo crear/actualizar la línea');
    }

    const lineId = meta.line_id;
    const i = meta.i; // índice de esta personalización dentro de la línea (1,2,3,...)

    // 2) subir PNG emparejado con i (si lo tenemos)
    if (pngDataURL) {
      const b64 = String(pngDataURL).replace(/^data:image\/png;base64,/, '');
      const upResp = await fetch('/spw/attach_png', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          line_id: Number(lineId),
          png_b64: b64,
          i: Number(i), // MUY IMPORTANTE para que el carrito muestre la imagen correcta
        }),
      });
      const up = await upResp.json().catch(() => ({}));
      if (!up || !up.ok) {
        throw new Error((up && up.message) || 'No se pudo adjuntar el PNG');
      }
    }

    // 3) redirigir al carrito
    const url = (meta.cart_url || '/shop/cart') + '?spw_line_id=' + lineId;
    window.location.assign(url);

    return { ok: true, lineId, i };
  }

  // Exponer en global para poder llamarla desde cualquier parte (o con onclick)
  window.spwSubmitPersonalization = spwSubmitPersonalization;
})();