/** SPW – Cart preview injector (fotos múltiples + píldoras, robusto) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
  'use strict';

  /* ---------- util ---------- */
  function onReady(cb){
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', cb, { once:true });
    } else cb();
  }
  function safe(fn){ try { fn(); } catch(e){ console.warn('[SPW]', e); } }

  /* ---------- selectores ---------- */
  const LINE_SEL =
    '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
  const INFO_SEL =
    '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

  /* ---------- helpers ---------- */
  function getLineId(lineEl){
    if (!lineEl) return null;
    const n = lineEl.getAttribute('data-line-id') ? lineEl :
      lineEl.querySelector('[data-line-id]') ||
      lineEl.querySelector('input[name="line_id"]') ||
      lineEl.querySelector('button[data-line-id], a[data-line-id]');
    return n ? (n.getAttribute?.('data-line-id') || n.getAttribute?.('data-id') || n.value || null) : null;
  }

  function parseColors(text){
    const out = []; if (!text) return out;
    const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g; let m;
    while ((m = re.exec(text))) out.push(m[1].toUpperCase());
    return out; // en el mismo orden, sin deduplicar
  }

  function previewsFromAttr(infoEl, lineEl){
    const raw = infoEl.getAttribute('data-spw-previews') ||
                lineEl?.getAttribute('data-spw-previews') || '';
    if (!raw) return [];
    try { const arr = JSON.parse(raw); return Array.isArray(arr) ? arr.filter(Boolean) : []; }
    catch { return raw.split(',').map(s=>s.trim()).filter(Boolean); }
  }

  function candidatesFor(lineId, idx){ // idx: 0 => base
    const base = `/spw/line_preview/${lineId}`;
    const exts = ['png','webp'];
    const suf = idx ? [`-${idx}`, `_${idx}`, `.${idx}`] : [''];
    const urls = [];
    suf.forEach(s => exts.forEach(e => urls.push(`${base}${s}.${e}`)));
    return urls;
  }

  function loadFirst(urls, cb){
    let i=0;
    (function next(){
      if (i>=urls.length) return;
      const u = urls[i++], img = new Image();
      img.decoding = 'async'; img.loading = 'lazy';
      img.alt = 'Personalización';
      img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
      img.onload = () => cb(img);
      img.onerror = next;
      img.src = `${u}${u.includes('?') ? '&' : '?'}v=${Date.now()}`;
    })();
  }

  function ensureWrap(info){
    let wrap = info.querySelector('.spw-cart-preview');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'spw-cart-preview';
      wrap.style.cssText = 'margin-top:8px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap';
      info.appendChild(wrap);
    } else {
      // si existe, lo limpiamos para reinyectar contenido actualizado
      wrap.innerHTML = '';
    }
    const photos = document.createElement('div');
    photos.className = 'spw-photos';
    photos.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;align-items:center';
    const pills = document.createElement('div');
    pills.className = 'spw-pills';
    pills.style.cssText = 'display:flex;flex-direction:column;gap:6px;align-items:flex-start';
    wrap.appendChild(photos);
    wrap.appendChild(pills);
    return { wrap, photos, pills };
  }

  /* ---------- inyección ---------- */
  function injectInto(lineEl){
    safe(() => {
      const info = lineEl.querySelector(INFO_SEL) || lineEl;
      if (!info) return;

      const { photos, pills } = ensureWrap(info);
      const lineId = getLineId(lineEl);
      const colors = parseColors(info.textContent || '');

      // Fotos: 1) de atributo, 2) por índice N, 3) fallback base
      previewsFromAttr(info, lineEl).forEach(u => loadFirst([u], img => photos.appendChild(img)));

      if (lineId) {
        colors.forEach((_, idx) => {
          loadFirst(candidatesFor(lineId, idx+1), img => photos.appendChild(img));
        });
        loadFirst(candidatesFor(lineId, 0), img => { if (!photos.children.length) photos.appendChild(img); });
      }

      // Píldoras (verticales, orden original)
      colors.forEach(hex => {
        const s = document.createElement('span');
        s.title = hex;
        s.style.cssText = 'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
        s.style.background = hex;
        pills.appendChild(s);
      });
    });
  }

  function initialInject(){ safe(() => document.querySelectorAll(LINE_SEL).forEach(injectInto)); }

  function observeMutations(){
    safe(() => {
      const target = document.body; // siempre observamos
      const mo = new MutationObserver(muts => {
        muts.forEach(m => (m.addedNodes || []).forEach(n => {
          if (!(n instanceof HTMLElement)) return;
          if (n.matches?.(LINE_SEL)) injectInto(n);
          else n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
        }));
      });
      mo.observe(target, { childList:true, subtree:true });
    });
  }

  function boot(){
    initialInject();
    observeMutations();
    console.log('[SPW] injector activo (fotos + píldoras)');
  }

  onReady(boot);
});