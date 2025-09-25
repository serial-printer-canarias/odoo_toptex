/** SPW – Cart preview injector (multiples fotos + píldoras HEX, sin romper nada) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- ready sin dependencias ----------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else {
            cb();
        }
    }

    // ---------- selectores robustos ----------
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // ---------- helpers ----------
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

    // HEX en el texto (una píldora por coincidencia; orden = orden de aparición)
    function extractHexList(text) {
        if (!text) return [];
        const out = [];
        const rx = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        let m; while ((m = rx.exec(text))) out.push('#' + m[1]);
        return out;
    }

    // Construye la lista de URLs que vamos a probar para la N-ésima personalización
    // n = 1 => principal (la que ya existe hoy). n >= 2 => variantes comunes.
    function buildUrlCandidates(lineId, n) {
        const v = Date.now(); // buster de caché
        const base = `/spw/line_preview/${lineId}`;
        if (n === 1) {
            return [
                `${base}.webp?v=${v}`,
                `${base}.png?v=${v}`,
                `${base}.jpg?v=${v}`,
            ];
        }
        // ¡OJO! aquí nunca metemos comas sueltas; siempre número real.
        return [
            `${base}-${n}.webp?v=${v}`,
            `${base}-${n}.png?v=${v}`,
            `${base}_${n}.webp?v=${v}`,
            `${base}_${n}.png?v=${v}`,
            `${base}/${n}.png?v=${v}`,
            `${base}.${n}.png?v=${v}`,
            `${base}.png?i=${n}&v=${v}`,
            `${base}.png?idx=${n}&v=${v}`,
        ];
    }

    // Carga la primera URL que funcione; si ninguna carga, no pintamos nada (sin rotos)
    function loadFirstWorking(urls) {
        return new Promise((resolve, reject) => {
            if (!urls || !urls.length) return reject(new Error('no urls'));
            let i = 0;
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText =
                'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';

            const tryNext = () => {
                if (i >= urls.length) return reject(new Error('all failed'));
                const url = urls[i++];
                img.onload = () => resolve(Object.assign(img, { src: url }));
                img.onerror = tryNext;
                img.src = url;
            };
            tryNext();
        });
    }

    function ensureWrapper(info, lineId) {
        let wrap = info.querySelector('.spw-cart-preview');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.dataset.lineId = lineId;
            wrap.style.cssText = 'margin-top:8px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap';
            info.appendChild(wrap);
        }
        return wrap;
    }

    function makePill(hex) {
        const pill = document.createElement('span');
        pill.title = hex;
        pill.style.cssText = 'display:inline-block;width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;margin:4px 0';
        pill.style.background = hex;
        return pill;
    }

    // ---------- inyección ----------
    async function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        const lineId = getLineId(lineEl);
        if (!info || !lineId) return;

        // Evitamos duplicados: limpiamos sólo nuestro bloque, no el resto del DOM.
        const wrap = ensureWrapper(info, lineId);
        wrap.innerHTML = ''; // rehacer (resistente a cambios de qty/AJAX)

        // Lista de HEX (0..N-1). Si no hay HEX, seguimos mostrando al menos la 1ª imagen.
        const hexes = extractHexList(info.textContent || '');

        // Columna de píldoras (vertical)
        if (hexes.length) {
            const col = document.createElement('div');
            col.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px;margin-left:4px';
            hexes.forEach((h) => col.appendChild(makePill(h)));
            wrap.appendChild(col);
        }

        // Contenedor de imágenes (flujo)
        const imgBox = document.createElement('div');
        imgBox.style.cssText = 'display:flex;flex-wrap:wrap;gap:8px';
        wrap.appendChild(imgBox);

        // Queremos tantas imágenes como personalizaciones detectadas.
        // n = 1..N  (si N=0, igualmente probamos 1)
        const count = Math.max(1, hexes.length);

        for (let n = 1; n <= count; n++) {
            const urls = buildUrlCandidates(lineId, n);
            try {
                const okImg = await loadFirstWorking(urls);
                imgBox.appendChild(okImg);
            } catch {
                // Si ninguna URL funciona para esa posición, no añadimos nada (sin icono roto).
                // console.debug(`[SPW] line ${lineId} n=${n} sin imagen (404 en todas)`);
            }
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
        // Sólo actuamos en el carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (fotos + píldoras)');
    }

    onReady(boot);
});