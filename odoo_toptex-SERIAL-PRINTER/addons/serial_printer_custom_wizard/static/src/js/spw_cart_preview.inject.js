/** SPW – Cart preview injector (multi-foto + píldoras en columna) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    /* ---------- ready sin dependencias ---------- */
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else { cb(); }
    }

    /* ---------- selectores robustos ---------- */
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    /* ---------- helpers ---------- */
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return cand
            ? (cand.getAttribute?.('data-line-id') ||
               cand.getAttribute?.('data-id') ||
               cand.value || null)
            : null;
    }

    function parseColors(text) {
        if (!text) return [];
        const out = [];
        const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g;
        let m;
        while ((m = re.exec(text))) {
            const hex = m[1].toUpperCase();
            if (!out.includes(hex)) out.push(hex);
        }
        return out;
    }

    function parsePreviewsFromAttr(el) {
        // opcional: si desde QWeb añades data-spw-previews="[...]"
        const raw = el.getAttribute('data-spw-previews') ||
                    el.closest(LINE_SEL)?.getAttribute('data-spw-previews') ||
                    '';
        if (!raw) return [];
        try {
            const arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr.filter(Boolean) : [];
        } catch {
            return raw.split(',').map(s => s.trim()).filter(Boolean);
        }
    }

    function alreadyInjected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    // Candidatas de rutas que PROBAMOS sin tocar backend.
    function candidateUrls(lineId) {
        if (!lineId) return [];
        const b = `/spw/line_preview/${lineId}`;
        const exts = ['png', 'webp'];
        const parts = ['','-1','-2','-3','-4','-5','-6','_1','_2','_3','_4','_5','_6','.1','.2','.3','.4','.5','.6'];
        const urls = [];
        // La “segura” (última guardada)
        exts.forEach(ext => urls.push(`${b}.${ext}`));
        // Variantes numeradas que ya probaste en consola
        parts.forEach(p => exts.forEach(ext => urls.push(`${b}${p}.${ext}`)));
        return urls;
    }

    function addImageWhenExists(url, holder, seen) {
        if (!url || seen.has(url)) return;
        const img = new Image();
        img.loading = 'lazy';
        img.alt = 'Personalización';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
        img.onload = () => { seen.add(url); holder.appendChild(img); };
        img.onerror = () => {}; // si 404, no añadimos
        // cache-buster suave
        const sep = url.includes('?') ? '&' : '?';
        img.src = `${url}${sep}v=${Date.now()}`;
    }

    /* ---------- inyección ---------- */
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        const colors = parseColors(info.textContent || '');

        // contenedor principal: fotos + columna de píldoras
        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText = 'margin-top:8px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap';

        // bloque fotos (horizontal, varias)
        const photos = document.createElement('div');
        photos.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;align-items:center';

        // bloque colores (columna vertical)
        const pills = document.createElement('div');
        pills.style.cssText = 'display:flex;flex-direction:column;gap:6px;align-items:flex-start';

        // 1) intentar lista desde atributo (si la hubiese)
        let urls = parsePreviewsFromAttr(info);

        // 2) si no hay lista, probamos todas las variantes conocidas
        if (!urls.length) urls = candidateUrls(lineId);

        // añadir imágenes que realmente existan
        const seen = new Set();
        urls.forEach(u => addImageWhenExists(u, photos, seen));

        // píldoras (todas las que encuentre)
        colors.forEach(hex => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText = 'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            pills.appendChild(pill);
        });

        if (photos.children.length || pills.children.length) {
            wrap.appendChild(photos);
            wrap.appendChild(pills);
            info.appendChild(wrap);
        }
    }

    function initialInject() {
        document.querySelectorAll(LINE_SEL).forEach(injectInto);
    }

    function observeMutations() {
        const target = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                (m.addedNodes || []).forEach((n) => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches?.(LINE_SEL)) {
                        injectInto(n);
                    } else {
                        n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
                    }
                });
            }
        });
        mo.observe(target, { childList: true, subtree: true });
    }

    function boot() {
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (multi-foto + píldoras en columna)');
    }

    onReady(boot);
});