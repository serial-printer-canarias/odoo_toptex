/** SPW – Cart preview injector (fotos + píldoras) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- helpers de ready (sin dependencias) ----------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // ---------- selectores robustos ----------
    const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // ---------- util ----------
    function urlLineId() {
        const m = location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }
    function getLineId(lineEl) {
        if (!lineEl) return urlLineId(); // Fallback crítico
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
        while ((m = re.exec(text))) { out.push({ idx: i++, hex: '#' + m[1] }); }
        return out.length ? out : [{ idx: 0, hex: null }];
    }

    // Genera varios patrones de URL por índice (para poder mostrar >1 imagen)
    function buildUrlCandidates(lineId, i) {
        const n = i + 1;                // 1-based
        const v = Date.now();           // cache-buster
        const bases = [
            `/spw/line_preview/${lineId}`,
            `/spw/line_preview/${lineId}-${n}`,
            `/spw/line_preview/${lineId}/${n}`,
            `/spw/line_preview/${lineId}_${n}`,
            `/spw/line_preview/${lineId}?i=${n}`
        ];
        const exts = ['png', 'webp', 'jpg', 'jpeg'];
        const urls = [];

        // con extensión
        for (const b of bases) for (const ext of exts) urls.push(`${b}.${ext}?v=${v}`);
        // sin extensión
        urls.push(`/spw/line_preview/${lineId}?i=${n}&v=${v}`);

        // además: patrón “único” clásico por compatibilidad (el que ya te funcionó)
        urls.unshift(`/spw/line_preview/${lineId}.png?v=${v}`);

        return [...new Set(urls)];
    }

    function tryLoad(img, candidates) {
        let k = 0;
        function next() {
            if (k >= candidates.length) { img.remove(); return; } // nada válido → retiramos
            img.src = candidates[k++];
        }
        img.addEventListener('error', next);
        next();
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

    function renderLine(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info) return;

        const lineId = getLineId(lineEl);
        if (!lineId) return; // sin id no podemos pedir imágenes

        const wrap = ensureWrap(info);
        const imgsWrap = wrap.querySelector('.spw-imgs');
        const pillsWrap = wrap.querySelector('.spw-pills');

        // Limpieza controlada
        imgsWrap.innerHTML = '';
        pillsWrap.innerHTML = '';

        const persos = parsePersonalizations(info.textContent || '');

        persos.forEach(({ idx, hex }) => {
            // píldora (vertical y en orden)
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
        const mo = new MutationObserver(ms => {
            for (const m of ms) {
                m.addedNodes && m.addedNodes.forEach(n => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches?.(LINE_SEL)) renderLine(n);
                    else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
                });
            }
        });
        mo.observe(root, { childList: true, subtree: true });
    }

    function boot() {
        // Solo actuamos en páginas de carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (fotos + píldoras)');
    }

    onReady(boot);
});