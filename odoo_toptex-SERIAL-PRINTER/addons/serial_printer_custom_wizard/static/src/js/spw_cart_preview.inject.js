odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', ['web.public.widget'], function (publicWidget) {
  'use strict';

  function getLineId(line) {
    return line.getAttribute('data-line-id')
      || (line.querySelector('input[name="line_id"]') || {}).value
      || (function () {
            const a = line.querySelector('a[href*="line_id="]');
            if (!a) return null;
            try { return new URL(a.href, location.origin).searchParams.get('line_id'); }
            catch (_e) { return null; }
         })()
      || null;
  }

  function findLines() {
    const sel = '.o_wsale_cart_item, tr.js_cart_line, .card.js_cart_item, .row.js_cart_item';
    return Array.from(document.querySelectorAll(sel));
  }

  function infoBlock(line) {
    return line.querySelector('.o_wsale_cart_description')
        || line.querySelector('.o_wsale_product_information')
        || line.querySelector('.media-body')
        || line;
  }

  function findHexInText(line) {
    const blk = infoBlock(line);
    if (!blk) return null;
    const m = (blk.textContent || '').match(/#([0-9a-fA-F]{6})/);
    return m ? ('#' + m[1]) : null;
  }

  function insertPreview(line) {
    const id = getLineId(line);
    if (!id) return;

    const prevId = 'spw-prev-' + id;
    if (document.getElementById(prevId)) return;           // evita duplicados
    line.querySelectorAll('.spw-preview').forEach(n => n.remove()); // limpia restos

    const blk = infoBlock(line);
    if (!blk) return;

    const wrap = document.createElement('div');
    wrap.className = 'spw-preview d-flex align-items-center gap-2 mt-1';
    wrap.id = prevId;

    // píldora de color (si hay #RRGGBB en el texto de la línea)
    const hex = findHexInText(line);
    if (hex) {
      const pill = document.createElement('span');
      pill.title = hex;
      pill.style.cssText = 'display:inline-block;width:14px;height:14px;border-radius:999px;border:1px solid #e5e7eb;background:' + hex;
      wrap.appendChild(pill);
    }

    // miniatura servida por backend
    const img = new Image();
    img.alt = 'Personalización';
    img.loading = 'lazy';
    img.src = '/spw/line_preview/' + encodeURIComponent(id) + '.png?_=' + Date.now();
    img.style.maxWidth = '110px';
    img.style.height = 'auto';
    img.style.border = '1px solid #e5e7eb';
    img.style.borderRadius = '6px';
    wrap.appendChild(img);

    blk.appendChild(wrap);
  }

  function injectAll() {
    if (!/\/shop\/cart/.test(location.pathname)) return;
    findLines().forEach(insertPreview);
  }

  publicWidget.registry.spwCartPreviewInject = publicWidget.Widget.extend({
    selector: 'body',
    start() {
      if (!/\/shop\/cart/.test(window.location.pathname)) {
        return this._super.apply(this, arguments);
      }
      injectAll();

      const root = document.querySelector('.js_cart_lines') || document.querySelector('.o_wsale_cart') || document.body;
      if (window.MutationObserver && root) {
        const mo = new MutationObserver(() => requestAnimationFrame(injectAll));
        mo.observe(root, { childList: true, subtree: true });
        this._mo = mo;
      }
      setTimeout(injectAll, 400);
      setTimeout(injectAll, 1200);
      return this._super.apply(this, arguments);
    },
  });

  return publicWidget.registry.spwCartPreviewInject;
});