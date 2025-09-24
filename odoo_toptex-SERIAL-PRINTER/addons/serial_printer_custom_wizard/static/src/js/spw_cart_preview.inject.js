/** SPW – Cart preview injector (imagen + píldora HEX) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', ['web.dom_ready'], function (domReady) {
    'use strict';

    // ---- helpers -----------------------------------------------------------
    function getLineEl(from) {
        return (from.closest && (
            from.closest('[data-line-id]') ||
            from.closest('.o_cart_product') ||
            from.closest('.js_cart_lines tr'))) || null;
    }

    function urlLineId() {
        const m = location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }

    function getLineId(from) {
        const el = getLineEl(from || document.body);
        if (!el) return urlLineId() || null;
        return el.getAttribute('data-line-id') || el.getAttribute('data-id') || urlLineId() || null;
    }

    function buildPreviewUrl(lineId) {
        return lineId ? `/spw/line_preview/${lineId}.png` : null;
    }

    function extractHexFrom(text) {
        if (!text) return null;
        const m = text.match(/SVG\s*:\s*#([0-9a-fA-F]{3,8})/);
        return m ? ('#' + m[1]) : null;
    }

    function injected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    // ---- inyección ---------------------------------------------------------
    function injectInto(lineRoot) {
        const info = lineRoot.querySelector(
            '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name'
        ) || lineRoot;
        if (!info || injected(info)) return;

        const lineId = getLineId(info);
        const url = buildPreviewUrl(lineId);
        const hex = extractHexFrom(info.textContent || '');

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText = 'margin-top:8px;display:flex;align-items:center;gap:8px;flex-wrap:wrap';

        if (url) {
            const img = new Image();
            img.src = url;
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            wrap.appendChild(img);
        }
        if (hex) {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText = 'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        }

        if (wrap.children.length) info.appendChild(wrap);
    }

    function initialInject() {
        document.querySelectorAll('.o_cart_product, .js_cart_lines tr').forEach(injectInto);
    }

    function observeMutations() {
        const target = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary') || document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                (m.addedNodes || []).forEach((n) => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches('.o_cart_product, .js_cart_lines tr')) {
                        injectInto(n);
                    } else {
                        n.querySelectorAll && n.querySelectorAll('.o_cart_product, .js_cart_lines tr').forEach(injectInto);
                    }
                });
            }
        });
        mo.observe(target, { childList: true, subtree: true });
    }

    function boot() {
        // Solo en carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] cart preview injector listo');
    }

    // domReady de Odoo + fallback por si acaso
    if (typeof domReady === 'function') domReady(boot);
    else if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();

    return {}; // módulo AMD bien formado
});