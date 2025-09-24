/** SPW – Cart preview injector (multi-imagen + píldoras HEX) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // -------- ready sin dependencias --------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // -------- selectores robustos -----------
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    const MAX_GUESS = 8; // si el backend no nos dice cuántas previews hay

    // -------- helpers -----------------------
    function urlLineIdFallback() {
        const m = location.search && location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }

    // Intenta sacar un número “razonable” de un string
    function parseId(v) {
        if (!v) return null;
        const m = String(v).match(/\d+/);
        const n = m ? parseInt(m[0], 10) : NaN;
        return Number.isFinite(n) && n > 0 ? String(n) : null;
    }

    // Cazador de line_id ultra tolerante para desktop/móvil
    function getLineId(lineEl) {
        if (!lineEl) return urlLineIdFallback();

        // 1) Atributos directos
        const direct = parseId(lineEl.getAttribute('data-line-id')) ||
                       parseId(lineEl.getAttribute('data-id'));
        if (direct) return direct;

        // 2) Inputs/button/anchor dentro de la línea
        const cand = lineEl.querySelector([
            '[data-line-id]',
            '[data-id]',
            'input[name="line_id"]',
            'button[data-line-id]',
            'a[data-line-id]',
            // Odoo a veces guarda el id en data-oe-id o en name/value
            '[data-oe-id]',
            'input[name="line_id"][value]',
        ].join(','));

        const viaChild = cand &&
            (parseId(cand.getAttribute('data-line-id')) ||
             parseId(cand.getAttribute('data-id')) ||
             parseId(cand.getAttribute('data-oe-id')) ||
             parseId(cand.value));

        if (viaChild) return viaChild;

        // 3) Algunos +/- llevan atributos en botones distintos
        const qtyGroup = lineEl.querySelector('.css_quantity, .o_wsale_cart_quantity, .input-group');
        if (qtyGroup) {
            const btnId = qtyGroup.querySelector('button[data-line-id], a[data-line-id]');
            const viaBtn = btnId && parseId(btnId.getAttribute('data-line-id'));
            if (viaBtn) return viaBtn;
            const hidden = qtyGroup.querySelector('input[name="line_id"][value]');
            const viaHidden = hidden && parseId(hidden.value);
            if (viaHidden) return viaHidden;
        }

        // 4) Como último recurso, parámetro en URL (cuando se llega con ?spw_line_id=…)
        return urlLineIdFallback();
    }

    function uniq(arr) { const s = new Set(); return arr.filter(v => !s.has(v) && s.add(v)); }

    function candidateUrls(lineId, infoEl) {
        if (!lineId) return [];
        const base = `/spw/line_preview/${lineId}`;
        const urls = [`${base}.png`]; // compatibilidad con “la última”
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

    // -------- inyección ---------------------
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        const urls   = candidateUrls(lineId, info);
        const hexes  = extractAllHex(info.textContent || '');

        // contenedor visual
        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText = 'margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap';

        let appended = false;
        const ensureAppend = () => {
            if (!appended && wrap.children.length) {
                appended = true;
                info.appendChild(wrap);
            }
        };

        // Píldoras primero
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
                'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
            ensureAppend();
        });

        // Imágenes (sólo si existen)
        urls.forEach((u) => {
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText =
                'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            img.onload  = () => { wrap.appendChild(img); ensureAppend(); };
            img.onerror = () => {}; // ignorar 404
            img.src = u;
        });

        // Si no hay nada, no insertamos (mantener DOM limpio)
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
        // Sólo actuamos en carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] cart preview injector listo (line_id robusto)');
    }

    onReady(boot);
});