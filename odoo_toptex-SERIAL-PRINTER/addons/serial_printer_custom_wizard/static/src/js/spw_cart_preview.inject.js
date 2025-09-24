/** SPW – Cart preview injector (múltiples imágenes + varias píldoras HEX) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ------- ready sin dependencias -------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // ------- selectores robustos ----------
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // Si el backend aún no expone contador, probamos hasta N archivos.
    const MAX_GUESS = 8;

    // ------- helpers ----------------------
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand =
            lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return cand
            ? (cand.getAttribute?.('data-line-id') ||
               cand.getAttribute?.('data-id') ||
               cand.value ||
               null)
            : null;
    }

    function uniq(arr) {
        const s = new Set(); const out = [];
        arr.forEach(v => { if (!s.has(v)) { s.add(v); out.push(v); } });
        return out;
    }

    function buildCandidateUrls(lineId, count) {
        if (!lineId) return [];
        const base = `/spw/line_preview/${lineId}`;
        const urls = [];
        // Compatibilidad: siempre añadimos el "último"
        urls.push(`${base}.png`);
        // Preferente: si hay contador, -1..-count
        if (count > 0) {
            for (let i = 1; i <= count; i++) urls.push(`${base}-${i}.png`);
        } else {
            // Fallback inteligente: intentamos -1..-MAX_GUESS (si no existen, no se añaden)
            for (let i = 1; i <= MAX_GUESS; i++) urls.push(`${base}-${i}.png`);
        }
        return uniq(urls);
    }

    function extractAllHex(text) {
        const out = [];
        if (!text) return out;
        const re = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        let m; while ((m = re.exec(text))) out.push('#' + m[1]);
        return out;
    }

    function alreadyInjected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    // ------- inyección --------------------
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        const count = parseInt(info.getAttribute('data-spw-previews') || '0', 10) || 0;
        const candidates = buildCandidateUrls(lineId, count);
        const hexes = extractAllHex(info.textContent || '');

        if (!candidates.length && !hexes.length) return;

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText = 'margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap';

        // Cargamos solo las imágenes que EXISTEN (onload => append, onerror => nada)
        candidates.forEach((u) => {
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            img.onload = () => wrap.appendChild(img);
            img.onerror = () => {}; // ignorar inexistentes
            img.src = u;
        });

        // Píldoras de color (una por cada aparición de "SVG: #xxxxxx")
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
              'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        });

        // Solo insertamos si hay elementos hijos
        const observer = new MutationObserver(() => {
            if (wrap.children.length) {
                observer.disconnect();
                info.appendChild(wrap);
            }
        });
        observer.observe(wrap, { childList: true });
    }

    function initialInject() {
        document.querySelectorAll(LINE_SEL).forEach(injectInto);
    }

    function observeMutations() {
        const target =
            document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') ||
            document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                m.addedNodes && m.addedNodes.forEach((n) => {
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
        console.log('[SPW] cart preview injector listo (multi-imagen)');
    }

    onReady(boot);
});