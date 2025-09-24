/** SPW – Cart preview injector (multiimagen + sin duplicados) */
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

    // Candidatos de URL para una posición i (1..N) — SIEMPRE distintas
    function candidatesFor(lineId, i) {
        const urls = [];
        if (i === 1) {
            // priorizamos nombres explícitos de la 1ª posición
            urls.push(`/spw/line_preview/${lineId}-1.png`);
            urls.push(`/spw/line_preview/${lineId}_1.png`);
            urls.push(`/spw/line_preview/${lineId}.png?i=1`);
            // por compatibilidad, como último recurso la base
            urls.push(`/spw/line_preview/${lineId}.png`);
        } else {
            // para i>1 NUNCA usamos la base <id>.png para evitar repetir
            urls.push(`/spw/line_preview/${lineId}-${i}.png`);
            urls.push(`/spw/line_preview/${lineId}_${i}.png`);
            urls.push(`/spw/line_preview/${lineId}.png?i=${i}`);
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

    // Crea un <img> que prueba candidatos y evita repetir misma ruta base
    function makeSmartImg(urlCandidates, usedPaths) {
        const img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText =
            'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';

        let idx = 0;

        function normalize(u) {
            return (u || '').split('?')[0]; // comparamos sin query
        }

        function tryNext() {
            while (idx < urlCandidates.length) {
                const u = urlCandidates[idx++];
                const key = normalize(u);
                if (usedPaths.has(key)) continue; // evita duplicados
                usedPaths.add(key);
                img.src = u;
                return;
            }
            // no hay candidato válido distinto → elimina el <img>
            img.remove();
        }

        img.onerror = tryNext; // si falla, probamos el siguiente
        tryNext();             // primer intento
        return img;
    }

    // --- inyección ---
    function injectInto(lineEl) {
        const info = lineEl.querySelector?.(INFO_SEL) || lineEl;
        if (!info) return;

        // Idempotente por línea
        info.querySelectorAll?.('.spw-cart-preview').forEach((n) => n.remove());

        const lineId = getLineId(lineEl);
        const hexes = extractHexList(info.textContent || '');
        const count = Math.max(1, hexes.length); // nº de posiciones visibles

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap';

        // Imágenes: una por posición (1..count), evitando repetir fichero
        if (lineId) {
            const usedPaths = new Set();
            for (let i = 1; i <= count; i++) {
                const img = makeSmartImg(candidatesFor(lineId, i), usedPaths);
                wrap.appendChild(img); // si no carga, el propio img se auto-elimina
            }
        }

        // Píldoras HEX (una por color detectado)
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
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] cart preview injector MULTI sin duplicados listo');
    }

    onReady(boot);
});