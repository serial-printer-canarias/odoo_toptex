/** SPW – Cart preview injector (fotos múltiples + píldoras HEX en vertical) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    /* ----------------------- ready sin dependencias ---------------------- */
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

    /* ----------------------------- helpers ------------------------------- */
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
               cand.value || '')
            : '';
        return id || null;
    }

    // Devuelve los HEX en el orden que aparecen en el texto
    function extractHexesInOrder(text) {
        if (!text) return [];
        const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g;
        const out = [];
        let m;
        while ((m = re.exec(text))) out.push(m[1]);
        return out;
    }

    function alreadyInjected(lineEl) {
        return !!lineEl.querySelector('.spw-cart-preview');
    }

    function buildUrl(lineId, idx, ext) {
        // idx=0 => /spw/line_preview/ID.ext
        // idx>0 => /spw/line_preview/ID-idx.ext
        const sfx = idx > 0 ? `-${idx}` : '';
        return `/spw/line_preview/${lineId}${sfx}.${ext}?v=${Date.now()}`;
    }

    // Carga secuencial: base y luego -1, -2, ...; prueba webp y png
    function loadAllPreviews(lineId, imgCol, max = 12, stopAfterMisses = 2) {
        let idx = 0;          // 0 = base
        let misses = 0;
        let found = 0;

        function tryIndex() {
            if (idx > max) return;
            const urls = [buildUrl(lineId, idx, 'webp'), buildUrl(lineId, idx, 'png')];
            let p = 0;

            function tryNextUrl() {
                if (p >= urls.length) {
                    misses += 1;
                    if (idx === 0 || (found > 0 && misses >= stopAfterMisses)) return;
                    idx += 1;
                    tryIndex();
                    return;
                }
                const url = urls[p++];
                const img = new Image();
                img.decoding = 'async';
                img.loading = 'lazy';
                img.alt = 'Personalización';
                img.style.cssText =
                    'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
                img.onload = () => {
                    found += 1;
                    misses = 0;
                    imgCol.appendChild(img);
                    idx += 1;
                    tryIndex();
                };
                img.onerror = tryNextUrl;
                img.src = url;             // <- ESTO DISPARA LA PETICIÓN
            }
            tryNextUrl();
        }
        tryIndex();
    }

    /* ------------------------- inyección por línea ----------------------- */
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

        // columna de imágenes (multiples personalizaciones)
        const imgCol = document.createElement('div');
        imgCol.style.cssText = 'display:flex;flex-direction:column;gap:10px';

        if (lineId) {
            loadAllPreviews(lineId, imgCol, 12, 2);
        }

        // columna de píldoras (vertical, mismo orden que el texto)
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
        const mo = new MutationObserver((muts) => {
            muts.forEach((m) => {
                m.addedNodes && m.addedNodes.forEach((n) => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches?.(LINE_SEL)) injectInto(n);
                    else n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
                });
            });
        });
        mo.observe(target, { childList: true, subtree: true });
    }

    function boot() {
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (fotos múltiples + píldoras)');
    }

    onReady(boot);
});