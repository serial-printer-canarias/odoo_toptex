/** SPW – Cart preview injector (fotos + píldoras) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // -------- ready sin dependencias --------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // -------- selectores --------
    const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // -------- utils --------
    const ts = () => Date.now();

    function addQuery(url, params) {
        const u = new URL(url, window.location.origin);
        Object.entries(params || {}).forEach(([k, v]) => u.searchParams.set(k, v));
        return u.pathname + (u.search ? u.search : '');
    }

    function urlLineId() {
        const m = location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }

    function getLineId(lineEl) {
        if (!lineEl) return urlLineId();
        const c = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || urlLineId() || null;
    }

    function parsePersonalizations(text) {
        if (!text) return [];
        const out = [];
        const re = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        let m, i = 0;
        while ((m = re.exec(text))) out.push({ idx: i++, hex: '#' + m[1] });
        return out.length ? out : [{ idx: 0, hex: null }];
    }

    // candidatos por índice; probamos patrones indexados y, si todo falla,
    // un fallback "clásico" pero ÚNICO por índice para que no se quite el resto.
    function buildUrlCandidates(lineId, idx) {
        const n = idx + 1;
        const base = `/spw/line_preview/${lineId}`;
        const exts = ['png', 'webp', 'jpg', 'jpeg'];

        const indexedBases = [
            `${base}-${n}`,
            `${base}/${n}`,
            `${base}_${n}`,
        ];

        const urls = [];

        // 1) patrones indexados con extensión
        for (const b of indexedBases) for (const ext of exts) {
            urls.push(addQuery(`${b}.${ext}`, { v: ts() }));
        }

        // 2) patrón indexado por query (?i=n) con y sin extensión
        for (const ext of exts) {
            urls.push(addQuery(`${base}.${ext}`, { i: n, v: ts() }));
        }
        urls.push(addQuery(base, { i: n, v: ts() }));

        // 3) último recurso: la clásica sin índice PERO distinta por índice
        // (añadimos marker para no colisionar entre sí)
        for (const ext of exts) {
            urls.push(addQuery(`${base}.${ext}`, { i: n, fb: 1, v: ts() }));
        }

        // dedup por string
        return [...new Set(urls)];
    }

    function ensureWrap(info) {
        let wrap = info.querySelector('.spw-cart-preview');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;flex-wrap:wrap';

            const imgs = document.createElement('div');
            imgs.className = 'spw-imgs';
            imgs.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start';

            const pills = document.createElement('div');
            pills.className = 'spw-pills';
            pills.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-items:center';

            wrap.appendChild(imgs);
            wrap.appendChild(pills);
            info.appendChild(wrap);
        }
        return wrap;
    }

    // carga el primer candidato que responda 200; si ninguno carga, elimina el <img>
    function tryLoad(img, candidates) {
        let k = 0;
        function next() {
            if (k >= candidates.length) { img.remove(); return; }
            const url = candidates[k++];
            img.onerror = next;
            img.onload  = null; // no necesitamos marcar nada
            img.src = url;
        }
        next();
    }

    function renderLine(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info) return;

        const lineId = getLineId(lineEl);
        if (!lineId) return;

        const wrap = ensureWrap(info);
        const imgsWrap = wrap.querySelector('.spw-imgs');
        const pillsWrap = wrap.querySelector('.spw-pills');

        imgsWrap.innerHTML = '';
        pillsWrap.innerHTML = '';

        const persos = parsePersonalizations(info.textContent || '');

        persos.forEach(({ idx, hex }) => {
            // píldora (vertical)
            const pill = document.createElement('span');
            pill.title = hex || '—';
            pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
            if (hex) pill.style.background = hex;
            pillsWrap.appendChild(pill);

            // imagen
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            imgsWrap.appendChild(img);

            const candidates = buildUrlCandidates(lineId, idx);
            tryLoad(img, candidates);
        });
    }

    function initialInject() { document.querySelectorAll(LINE_SEL).forEach(renderLine); }

    function observeMutations() {
        const root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
        new MutationObserver(ms => {
            for (const m of ms) {
                m.addedNodes && m.addedNodes.forEach(n => {
                    if (n instanceof HTMLElement) {
                        if (n.matches?.(LINE_SEL)) renderLine(n);
                        else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
                    }
                });
            }
        }).observe(root, { childList: true, subtree: true });
    }

    function boot() {
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (multi-foto por línea; fallback por índice)');
    }

    onReady(boot);
});