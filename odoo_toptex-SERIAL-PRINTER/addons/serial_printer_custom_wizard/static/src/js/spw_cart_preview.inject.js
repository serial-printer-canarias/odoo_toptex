/** SPW – Cart preview injector (multi-imagen + píldoras HEX, layout limpio) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- ready sin dependencias ----------
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

    const MAX_GUESS = 8; // nº máx. de previews a probar si el backend no lo expone

    // ---------- helpers ----------
    function urlLineIdFallback() {
        const m = location.search && location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }
    function parseId(v) {
        if (!v) return null;
        const m = String(v).match(/\d+/);
        const n = m ? parseInt(m[0], 10) : NaN;
        return Number.isFinite(n) && n > 0 ? String(n) : null;
    }

    // Busca id dentro del nodo, SUS HIJOS y hasta 4 ANCESTROS (móvil cambia wrappers)
    function getLineId(lineEl) {
        if (!lineEl) return urlLineIdFallback();

        // 1) el propio contenedor
        let id = parseId(lineEl.getAttribute('data-line-id')) ||
                 parseId(lineEl.getAttribute('data-id'));
        if (id) return id;

        // 2) hijos típicos
        const inner = lineEl.querySelector([
            '[data-line-id]','[data-id]','[data-oe-id]',
            'input[name="line_id"][value]',
            'button[data-line-id]','a[data-line-id]'
        ].join(','));
        id = inner && (parseId(inner.getAttribute('data-line-id')) ||
                       parseId(inner.getAttribute('data-id')) ||
                       parseId(inner.getAttribute('data-oe-id')) ||
                       parseId(inner.value));
        if (id) return id;

        // 3) grupo de cantidad (desktop/móvil)
        const qty = lineEl.querySelector('.o_wsale_cart_quantity, .css_quantity, .input-group');
        if (qty) {
            const btn = qty.querySelector('button[data-line-id], a[data-line-id]');
            id = btn && parseId(btn.getAttribute('data-line-id'));
            if (id) return id;
            const hid = qty.querySelector('input[name="line_id"][value]');
            id = hid && parseId(hid.value);
            if (id) return id;
        }

        // 4) subir por ancestros (móvil suele envolver con tarjetas)
        let p = lineEl;
        for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
            id = parseId(p.getAttribute('data-line-id')) ||
                 parseId(p.getAttribute('data-id')) ||
                 (p.matches?.('[data-oe-id]') && parseId(p.getAttribute('data-oe-id')));
            if (id) return id;

            const any = p.querySelector?.('input[name="line_id"][value], [data-line-id], [data-id]');
            if (any) {
                id = parseId(any.getAttribute?.('data-line-id')) ||
                     parseId(any.getAttribute?.('data-id')) ||
                     parseId(any.value);
                if (id) return id;
            }
        }

        // 5) último recurso
        return urlLineIdFallback();
    }

    function uniq(arr) { const s = new Set(); return arr.filter(v => !s.has(v) && s.add(v)); }

    function candidateUrls(lineId, infoEl) {
        if (!lineId) return [];
        const base = `/spw/line_preview/${lineId}`;
        const urls = [`${base}.png`];
        const countAttr = parseInt(infoEl.getAttribute('data-spw-previews') || '0', 10) || 0;
        const max = countAttr > 0 ? countAttr : MAX_GUESS;
        for (let i = 1; i <= max; i++) urls.push(`${base}-${i}.png`);
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

    // ---------- inyección ----------
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        const urls   = candidateUrls(lineId, info);
        const hexes  = extractAllHex(info.textContent || '');

        // contenedor con dos zonas: fotos (izq) + píldoras (der)
        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:10px;display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap';

        const pics = document.createElement('div');
        pics.className = 'spw-cart-pics';
        pics.style.cssText =
            'display:flex;gap:8px;flex-wrap:wrap;min-height:90px;min-width:130px';

        const pills = document.createElement('div');
        pills.className = 'spw-cart-pills';
        pills.style.cssText =
            'display:flex;gap:8px;align-items:center;flex-wrap:wrap;min-height:20px';

        let hasAnything = false;

        // Píldoras (separadas del bloque de imágenes)
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
                'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            pills.appendChild(pill);
            hasAnything = true;
        });

        // Imágenes (cargan solo si existen)
        urls.forEach((u) => {
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText =
                'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
            img.onload  = () => { pics.appendChild(img); };
            img.onerror = () => {};
            img.src = u;
            // no marcamos hasAnything hasta onload (evita hueco si todas 404)
        });

        wrap.appendChild(pics);
        wrap.appendChild(pills);

        // Insertamos si hay algo visible (píldoras ya cuentan)
        if (hasAnything || urls.length) info.appendChild(wrap);
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
        console.log('[SPW] injector listo (multi-img + layout separado)');
    }

    onReady(boot);
});