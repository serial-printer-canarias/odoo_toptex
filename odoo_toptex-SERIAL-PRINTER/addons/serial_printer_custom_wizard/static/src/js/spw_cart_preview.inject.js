/** SPW – Cart preview injector (imagen + píldora HEX) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function (require) {
    'use strict';

    // domReady opcional: si no existe en el bundle, usamos fallback
    let domReady;
    try {
        domReady = require('web.dom_ready');
    } catch (e) {
        domReady = (cb) => {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', cb, { once: true });
            } else {
                cb();
            }
        };
    }

    // ----------- selectores robustos ----------
    const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // ----------- helpers ----------
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand =
            lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return cand
            ? (cand.getAttribute?.('data-line-id') || cand.getAttribute?.('data-id') || cand.value || null)
            : null;
    }

    function buildPreviewUrl(lineId) {
        return lineId ? `/spw/line_preview/${lineId}.png` : null;
    }

    function extractHexFrom(text) {
        if (!text) return null;
        const m = text.match(/SVG\s*:\s*#([0-9a-fA-F]{3,8})/);
        return m ? `#${m[1]}` : null;
    }

    function alreadyInjected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    // ----------- inyección ----------
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
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
        // Solo actuamos en el carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] cart preview injector listo');
    }

    domReady(boot);
});