/** SPW – Cart preview injector (multiimagen + múltiples píldoras HEX) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // --- ready sin dependencias ---
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else {
            cb();
        }
    }

    // --- selectores robustos ---
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // --- helpers ---
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand =
            (lineEl.getAttribute && lineEl.getAttribute('data-line-id')) ? lineEl :
            lineEl.querySelector?.('[data-line-id]') ||
            lineEl.querySelector?.('input[name="line_id"]') ||
            lineEl.querySelector?.('button[data-line-id], a[data-line-id]');
        return cand
            ? (cand.getAttribute?.('data-line-id') ||
               cand.getAttribute?.('data-id') ||
               cand.value ||
               null)
            : null;
    }

    // Devuelve candidatos de URL para una misma posición i (1..N)
    function candidatesFor(lineId, i) {
        const suf = i === 1 ? '' : `-${i}`;
        const urls = [];
        // patrón base
        urls.push(`/spw/line_preview/${lineId}${i === 1 ? '' : suf}.png`);
        // alternativas frecuentes
        if (i > 1) {
            urls.push(`/spw/line_preview/${lineId}_${i}.png`);
            urls.push(`/spw/line_preview/${lineId}.png?i=${i}`);
            urls.push(`/spw/line_preview/${lineId}-${i}.png?i=${i}`);
        }
        return urls;
    }

    // Extrae TODOS los HEX "SVG: #XXXXXX" del texto
    function extractHexList(text) {
        const out = [];
        const re = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        let m;
        while ((m = re.exec(text || ''))) out.push('#' + m[1]);
        return out;
    }

    // Crea un <img> que prueba candidatos en cascada
    function makeSmartImg(urlCandidates) {
        const img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText =
            'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';

        let idx = 0;
        function tryNext() {
            if (idx >= urlCandidates.length) {
                // ninguno funcionó → quita el <img>
                img.remove();
                return;
            }
            img.src = urlCandidates[idx++];
        }
        img.onerror = tryNext;
        tryNext(); // primer intento
        return img;
    }

    // --- inyección ---
    function injectInto(lineEl) {
        const info = lineEl.querySelector?.(INFO_SEL) || lineEl;
        if (!info) return;

        // Idempotente por línea: limpia inyecciones previas
        info.querySelectorAll?.('.spw-cart-preview').forEach((n) => n.remove());

        const lineId = getLineId(lineEl);
        const hexes = extractHexList(info.textContent || []);
        const count = Math.max(1, hexes.length); // al menos 1 imagen

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap';

        // Imágenes: una por posición (1..count), con fallback de nombres
        if (lineId) {
            for (let i = 1; i <= count; i++) {
                const img = makeSmartImg(candidatesFor(lineId, i));
                // si todas fallan, onerror lo elimina
                wrap.appendChild(img);
            }
        }

        // Píldoras de color (una por HEX)
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
                'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        });

        if (wrap.children.length) info.appendChild(wrap);
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
        // Solo actuamos en el carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] cart preview injector MULTI listo');
    }

    onReady(boot);
});