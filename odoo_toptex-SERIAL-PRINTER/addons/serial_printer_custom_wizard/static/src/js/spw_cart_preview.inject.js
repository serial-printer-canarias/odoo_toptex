/** SPW – Cart preview injector (fotos + píldoras) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- ready ----------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // ---------- selectores ----------
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    const MAX_GUESS = 6; // intentos si hubiese varias previews por línea

    // ---------- helpers ----------
    const cacheBust = () => `v=${Date.now()}`;

    function urlLineIdFallback() {
        const m = location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }
    function onlyNum(v) {
        const m = String(v || '').match(/\d+/);
        const n = m ? parseInt(m[0], 10) : NaN;
        return Number.isFinite(n) && n > 0 ? String(n) : null;
    }

    function getLineId(lineEl) {
        if (!lineEl) return urlLineIdFallback();

        let id = onlyNum(lineEl.getAttribute('data-line-id')) ||
                 onlyNum(lineEl.getAttribute('data-id'));
        if (id) return id;

        const cand = lineEl.querySelector([
            'input[name="line_id"][value]',
            'input[name="move_id"][value]',
            '[data-line-id]','[data-id]',
            'button[data-line-id]','a[data-line-id]'
        ].join(','));
        id = cand && (onlyNum(cand.value) ||
                      onlyNum(cand.getAttribute('data-line-id')) ||
                      onlyNum(cand.getAttribute('data-id')));
        if (id) return id;

        const qty = lineEl.querySelector('.o_wsale_cart_quantity, .css_quantity, .input-group');
        if (qty) {
            const b = qty.querySelector('button[data-line-id], a[data-line-id]');
            id = b && onlyNum(b.getAttribute('data-line-id'));
            if (id) return id;
            const h = qty.querySelector('input[name="line_id"][value], input[name="move_id"][value]');
            id = h && onlyNum(h.value);
            if (id) return id;
        }

        let p = lineEl.parentElement;
        for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
            id = onlyNum(p.getAttribute?.('data-line-id')) || onlyNum(p.getAttribute?.('data-id'));
            if (id) return id;
            const any = p.querySelector?.('input[name="line_id"][value], [data-line-id], [data-id]');
            if (any) {
                id = onlyNum(any.value) || onlyNum(any.getAttribute?.('data-line-id')) || onlyNum(any.getAttribute?.('data-id'));
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

    // Lee URLs si el backend las deja en atributos/inputs/script JSON
    function readMetaUrls(infoEl) {
        const urls = [];

        // 1) atributo directo
        const a1 = infoEl.getAttribute('data-spw-preview-url');
        if (a1) urls.push(a1);
        const a2 = infoEl.getAttribute('data-spw-preview-urls');
        if (a2) {
            try { JSON.parse(a2).forEach(u => urls.push(u)); } catch (_) {}
        }

        // 2) inputs ocultos
        infoEl.querySelectorAll('input[name="spw_preview_url"][value], input[name="spw_preview_urls"][value]').forEach(i => {
            try {
                if (i.name.endsWith('_urls')) JSON.parse(i.value).forEach(u => urls.push(u));
                else urls.push(i.value);
            } catch (_) {}
        });

        // 3) script/json
        const metaEl = infoEl.querySelector('#spw_meta_json, script[data-spw-meta-json]') ||
                        document.querySelector('#spw_meta_json, script[data-spw-meta-json]');
        if (metaEl) {
            try {
                const raw = metaEl.getAttribute('data-spw-meta-json') || metaEl.textContent || '{}';
                const meta = JSON.parse(raw);
                if (Array.isArray(meta.preview_urls)) urls.push(...meta.preview_urls);
                if (meta.preview_url) urls.push(meta.preview_url);
            } catch (_) {}
        }

        // añade cache-buster
        return urls.map(u => u.includes('?') ? `${u}&${cacheBust()}` : `${u}?${cacheBust()}`);
    }

    // Genera candidatos conocidos a partir del line_id
    function candidateUrls(lineId, infoEl) {
        const urls = readMetaUrls(infoEl);
        if (lineId) {
            const base = `/spw/line_preview/${lineId}`;
            const max = parseInt(infoEl.getAttribute('data-spw-previews') || '0', 10) || MAX_GUESS;
            const qs = cacheBust();
            urls.push(
                `${base}.png?${qs}`,
                `${base}.webp?${qs}`
            );
            for (let i = 1; i <= max; i++) {
                urls.push(
                    `${base}-${i}.png?${qs}`,
                    `${base}_${i}.png?${qs}`,
                    `${base}/${i}.png?${qs}`,
                    `${base}.png?n=${i}&${qs}`
                );
            }
        }
        // de-dup
        return [...new Set(urls)];
    }

    function alreadyInjected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    // ---------- inyección ----------
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        const urls   = candidateUrls(lineId, info);
        const hexes  = extractAllHex(info.textContent || '');

        console.log('[SPW] cart line', { lineId, urlsTried: urls });

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap';

        // Fotos: añadimos las que realmente carguen
        urls.forEach((u) => {
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText =
                'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
            img.onload  = () => wrap.insertBefore(img, wrap.firstChild);
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
        console.log('[SPW] injector listo (fotos + píldoras)');
    }

    onReady(boot);
});