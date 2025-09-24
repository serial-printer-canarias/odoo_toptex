/** SPW – Cart preview injector (foto por línea + píldoras estilo original) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------------- ready sin dependencias ----------------
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

    // Si el backend expone varias previews, las probamos: <id>.png, <id>-1.png, ...
    const MAX_GUESS = 6;

    // ---------------- helpers ----------------
    function urlLineIdFallback() {
        const m = location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }
    function parseNum(v) {
        const m = String(v || '').match(/\d+/);
        const n = m ? parseInt(m[0], 10) : NaN;
        return Number.isFinite(n) && n > 0 ? String(n) : null;
    }

    // encuentra el line_id en el propio nodo, hijos típicos y ancestros (móvil/desktop)
    function getLineId(lineEl) {
        if (!lineEl) return urlLineIdFallback();

        // 1) directamente en el contenedor
        let id = parseNum(lineEl.getAttribute('data-line-id')) ||
                 parseNum(lineEl.getAttribute('data-id'));
        if (id) return id;

        // 2) elementos hijos comunes de Odoo
        const cand = lineEl.querySelector([
            'input[name="line_id"][value]',
            'input[name="move_id"][value]',
            '[data-line-id]','[data-id]',
            'button[data-line-id]','a[data-line-id]'
        ].join(','));
        id = cand && (parseNum(cand.value) ||
                      parseNum(cand.getAttribute('data-line-id')) ||
                      parseNum(cand.getAttribute('data-id')));
        if (id) return id;

        // 3) grupo de cantidad (móvil/desktop)
        const qty = lineEl.querySelector('.o_wsale_cart_quantity, .css_quantity, .input-group');
        if (qty) {
            const b = qty.querySelector('button[data-line-id], a[data-line-id]');
            id = b && parseNum(b.getAttribute('data-line-id'));
            if (id) return id;
            const h = qty.querySelector('input[name="line_id"][value], input[name="move_id"][value]');
            id = h && parseNum(h.value);
            if (id) return id;
        }

        // 4) subir por ancestros (algunos temas envuelven el item)
        let p = lineEl.parentElement;
        for (let i = 0; i < 4 && p; i++, p = p.parentElement) {
            id = parseNum(p.getAttribute?.('data-line-id')) ||
                 parseNum(p.getAttribute?.('data-id'));
            if (id) return id;
            const any = p.querySelector?.('input[name="line_id"][value], [data-line-id], [data-id]');
            if (any) {
                id = parseNum(any.value) ||
                     parseNum(any.getAttribute?.('data-line-id')) ||
                     parseNum(any.getAttribute?.('data-id'));
                if (id) return id;
            }
        }

        // 5) último recurso (cuando entras con ?spw_line_id=…)
        return urlLineIdFallback();
    }

    function extractAllHex(text) {
        const out = [];
        if (!text) return out;
        const re = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        let m; while ((m = re.exec(text))) out.push('#' + m[1]);
        return out;
    }

    function candidateUrls(lineId, infoEl) {
        if (!lineId) return [];
        const base = `/spw/line_preview/${lineId}`;
        const urls = [`${base}.png`];
        const countAttr = parseInt(infoEl.getAttribute('data-spw-previews') || '0', 10) || 0;
        const max = countAttr > 0 ? countAttr : MAX_GUESS;
        for (let i = 1; i <= max; i++) urls.push(`${base}-${i}.png`);
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

        // layout como el que te gustaba: todo en una fila, con buen espaciado
        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText =
            'margin-top:8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap';

        // fotos (aparecen solo si existen)
        let anyImg = false;
        urls.forEach((u) => {
            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText =
                'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
            img.onload  = () => { wrap.insertBefore(img, wrap.firstChild); anyImg = true; };
            img.onerror = () => {};
            img.src = u;
        });

        // píldoras (todas las que encuentre)
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText =
                'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        });

        // si habrá algo (píldoras o fotos), insertamos
        if (hexes.length || urls.length) info.appendChild(wrap);
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
        // solo en carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (foto + píldoras estilo original)');
    }

    onReady(boot);
});