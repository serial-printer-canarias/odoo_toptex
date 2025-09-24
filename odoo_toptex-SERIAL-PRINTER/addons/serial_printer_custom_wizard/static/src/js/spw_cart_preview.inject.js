/** SPW – Cart preview injector (foto por línea + píldoras estilo original) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------------- ready ----------------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // ---------------- selectores ----------------
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // Intentaremos hasta este nº de índices si el backend guarda varias previews por línea
    const MAX_GUESS = 6;

    // ---------------- helpers ----------------
    const cacheBust = () => `v=${Date.now()}`;

    function urlLineIdFallback() {
        const m = location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }
    function num(v) {
        const m = String(v || '').match(/\d+/);
        const n = m ? parseInt(m[0], 10) : NaN;
        return Number.isFinite(n) && n > 0 ? String(n) : null;
    }

    // Caza el line_id en el nodo, hijos típicos y ancestros (móvil/desktop/tema)
    function getLineId(lineEl) {
        if (!lineEl) return urlLineIdFallback();

        let id = num(lineEl.getAttribute('data-line-id')) ||
                 num(lineEl.getAttribute('data-id'));
        if (id) return id;

        const cand = lineEl.querySelector([
            'input[name="line_id"][value]',
            'input[name="move_id"][value]',
            '[data-line-id]','[data-id]',
            'button[data-line-id]','a[data-line-id]'
        ].join(','));
        id = cand && (num(cand.value) ||
                      num(cand.getAttribute('data-line-id')) ||
                      num(cand.getAttribute('data-id')));
        if (id) return id;

        const qty = lineEl.querySelector('.o_wsale_cart_quantity, .css_quantity, .input-group');
        if (qty) {
            const b = qty.querySelector('button[data-line-id], a[data-line-id]');
            id = b && num(b.getAttribute('data-line-id'));
            if (id) return id;
            const h = qty.querySelector('input[name="line_id"][value], input[name="move_id"][value]');
            id = h && num(h.value);
            if (id) return id;
        }

        let p = lineEl.parentElement;
        for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
            id = num(p.getAttribute?.('data-line-id')) || num(p.getAttribute?.('data-id'));
            if (id) return id;
            const any = p.querySelector?.('input[name="line_id"][value], [data-line-id], [data-id]');
            if (any) {
                id = num(any.value) || num(any.getAttribute?.('data-line-id')) || num(any.getAttribute?.('data-id'));
                if (id) return id;
            }
        }
        return urlLineIdFallback();
    }

    function extractAllHex(text) {
        const out = [];
        if (!text) return out;
        const re = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        let m; while ((m = re.exec(text))) out.push('#' + m[1]);
        return out;
    }

    // Genera una lista de posibles rutas donde podría estar la(s) preview(s)
    function candidateUrls(lineId, infoEl) {
        if (!lineId) return [];
        const base = `/spw/line_preview/${lineId}`;
        const c = parseInt(infoEl.getAttribute('data-spw-previews') || '0', 10) || 0;
        const max = c > 0 ? c : MAX_GUESS;
        const qs = cacheBust();

        const urls = [
            `${base}.png?${qs}`,         // /spw/line_preview/123.png
            `${base}.webp?${qs}`,        // por si el backend sirve webp
        ];
        for (let i = 1; i <= max; i++) {
            urls.push(
                `${base}-${i}.png?${qs}`,  // /spw/line_preview/123-1.png
                `${base}_${i}.png?${qs}`,  // /spw/line_preview/123_1.png
                `${base}/${i}.png?${qs}`,  // /spw/line_preview/123/1.png
                `${base}.png?n=${i}&${qs}` // /spw/line_preview/123.png?n=1
            );
        }
        return urls;
    }

    function alreadyInjected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    // ---------------- inyección ----------------
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        const urls   = candidateUrls(lineId, info);
        const hexes  = extractAllHex(info.textContent || '');

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap';

        // Fotos: añadimos TODAS las que realmente existan (onload). Las que no, se ignoran.
        let anyImg = false;
        urls.forEach((u) => {
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.crossOrigin = 'anonymous';
            img.style.cssText =
                'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
            img.onload  = () => { anyImg = true; wrap.insertBefore(img, wrap.firstChild); };
            img.onerror = () => {};
            img.src = u;
        });

        // Píldoras (todas)
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
                'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        });

        if (urls.length || hexes.length) info.appendChild(wrap);
    }

    function initialInject() {
        document.querySelectorAll(LINE_SEL).forEach(injectInto);
    }

    function observeMutations() {
        const target =
            document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines')
            || document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                m.addedNodes && m.addedNodes.forEach((n) => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches?.(LINE_SEL)) injectInto(n);
                    else n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
                });
            }
        });
        mo.observe(target, { childList: true, subtree: true });
    }

    function boot() {
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (foto + píldoras)');
    }

    onReady(boot);
});