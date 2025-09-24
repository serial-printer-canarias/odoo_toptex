/** SPW – Cart preview injector (fotos + píldoras HEX, varias por línea) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    /* ----------------------- utilidades de “ready” ----------------------- */
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else {
            cb();
        }
    }

    /* ----------------------- selectores robustos ------------------------- */
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    /* ----------------------- helpers ------------------------------------ */
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand =
            lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        const id = cand
            ? (cand.getAttribute?.('data-line-id') ||
               cand.getAttribute?.('data-id') ||
               cand.value ||
               '')
            : '';
        return id || null;
    }

    function extractHexesInOrder(text) {
        // Captura en orden las apariciones tipo: "SVG: #RRGGBB" (3–8 dígitos)
        if (!text) return [];
        const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g;
        const out = [];
        let m;
        while ((m = re.exec(text))) {
            out.push(m[1]);
        }
        return out;
    }

    function alreadyInjected(lineEl) {
        return !!lineEl.querySelector('.spw-cart-preview');
    }

    function buildUrl(lineId, idx, ext) {
        // idx = 0  -> /spw/line_preview/ID.ext
        // idx > 0  -> /spw/line_preview/ID-idx.ext
        const suffix = idx > 0 ? `-${idx}` : '';
        const v = Date.now(); // evitar caché
        return `/spw/line_preview/${lineId}${suffix}.${ext}?v=${v}`;
    }

    /* ---------- carga secuencial: varias imágenes por línea ------------- */
    function loadAllPreviews(lineId, imgWrap, max = 8, stopAfterMisses = 2) {
        let idx = 0;               // 0 = base, luego -1, -2, ...
        let misses = 0;            // cortes seguidos (para parar)
        let foundAny = 0;

        function tryOne() {
            if (idx > max) return;                     // límite sano
            // probar .webp y luego .png para este índice
            const attempts = [buildUrl(lineId, idx, 'webp'), buildUrl(lineId, idx, 'png')];
            let pos = 0;

            function tryExt() {
                if (pos >= attempts.length) {
                    // este índice no existe en ningún formato
                    misses += 1;
                    if (idx === 0 || (misses >= stopAfterMisses && foundAny > 0)) return;
                    idx += 1;
                    tryOne();
                    return;
                }
                const url = attempts[pos++];
                const img = new Image();
                img.decoding = 'async';
                img.loading = 'lazy';
                img.alt = 'Personalización';
                img.style.cssText =
                    'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';

                img.onload = () => {
                    misses = 0;
                    foundAny += 1;
                    imgWrap.appendChild(img);
                    // buscar siguiente posible índice (otra personalización)
                    idx += 1;
                    tryOne();
                };
                img.onerror = () => {
                    // probar el otro formato para este índice
                    tryExt();
                };

                img.src = url;
            }

            tryExt();
        }

        tryOne();
    }

    /* ----------------------- inyección por línea ------------------------ */
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(lineEl)) return;

        const lineId = getLineId(lineEl);
        const hexes = extractHexesInOrder(info.textContent || '');

        // contenedor principal
        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:10px;display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap';

        // columna de imágenes (puede haber varias)
        const imgCol = document.createElement('div');
        imgCol.style.cssText = 'display:flex;flex-direction:column;gap:10px';

        if (lineId) {
            loadAllPreviews(lineId, imgCol, 12, 2);
        }

        // columna de píldoras en vertical, en el mismo orden del texto
        const pillsCol = document.createElement('div');
        pillsCol.style.cssText = 'display:flex;flex-direction:column;gap:6px;min-width:18px';

        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
                'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            pillsCol.appendChild(pill);
        });

        // añadimos sólo si hay algo que mostrar
        if (imgCol.childElementCount || pillsCol.childElementCount) {
            wrap.appendChild(imgCol);
            wrap.appendChild(pillsCol);
            info.appendChild(wrap);
        }
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
        console.log('[SPW] injector listo (fotos + píldoras)');
    }

    onReady(boot);
});