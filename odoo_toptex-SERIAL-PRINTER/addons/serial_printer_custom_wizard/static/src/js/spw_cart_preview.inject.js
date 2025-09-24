odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', ['web.dom_ready'], function (require) {
    'use strict';

    const domReady = require('web.dom_ready');

    // ---- Config mínima
    const WRAP_CLASS = 'spw-cart-preview';
    const PREVIEW_BASE = '/spw/line_preview'; // Endpoint que ya tienes activo: /spw/line_preview/<line_id>.png

    // Selectores robustos (distintas plantillas usan clases algo diferentes)
    const INFO_SELECTORS = [
        '.o_wsale_product_information',
        '.media-body',
        '.o_cart_line_details',
        '.o_cart_item_info',
    ];

    // Utils
    function qAll(root, sel) { return Array.from(root.querySelectorAll(sel)); }
    function getLineRoot(el) {
        return el.closest('[data-line-id]') || el.closest('.o_cart_product') || el.closest('tr');
    }
    function getLineId(el) {
        const root = getLineRoot(el);
        return root && (root.getAttribute('data-line-id') || root.dataset.lineId || null);
    }
    function getInfoContainer(lineRoot) {
        for (let i = 0; i < INFO_SELECTORS.length; i++) {
            const node = lineRoot.querySelector(INFO_SELECTORS[i]);
            if (node) return node;
        }
        return null;
    }
    function extractHexFromText(txt) {
        if (!txt) return null;
        const m = txt.match(/SVG\s*:\s*(#[0-9a-fA-F]{3,6})/);
        return m ? m[1] : null;
    }

    function buildPreview(lineRoot) {
        const info = getInfoContainer(lineRoot);
        if (!info) return;

        // Evitar duplicados
        const old = info.querySelector('.' + WRAP_CLASS);
        if (old) old.remove();

        const lineId = getLineId(lineRoot);

        const wrap = document.createElement('div');
        wrap.className = `${WRAP_CLASS} d-flex align-items-center mt-2`;
        wrap.style.gap = '8px';
        wrap.style.flexWrap = 'wrap';

        // Miniatura
        if (lineId) {
            const img = document.createElement('img');
            img.src = `${PREVIEW_BASE}/${lineId}.png`;
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.maxWidth = '120px';
            img.style.height = 'auto';
            img.style.border = '1px solid #e5e7eb';
            img.style.borderRadius = '6px';
            wrap.appendChild(img);
        }

        // Píldora de color (lee del texto: "SVG: #RRGGBB")
        const hex = extractHexFromText(info.textContent || '');
        if (hex) {
            const pill = document.createElement('span');
            pill.title = `SVG ${hex}`;
            pill.setAttribute('aria-label', `Color ${hex}`);
            pill.style.display = 'inline-block';
            pill.style.width = '16px';
            pill.style.height = '16px';
            pill.style.borderRadius = '9999px';
            pill.style.border = '1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        }

        if (wrap.children.length) info.appendChild(wrap);
    }

    function injectAll(root) {
        root = root || document;
        const lines = qAll(root, '.o_cart_product, .o_wsale_cart_item, tr[data-line-id]');
        if (!lines.length) return;
        lines.forEach(buildPreview);
    }

    function boot() {
        // Solo en páginas de carrito
        if (!document.querySelector('.o_cart, .o_wsale_cart')) return;

        injectAll(document);

        // Reinyectar en cambios de DOM (qty +/- , ajax del carrito, etc.)
        const target = document.querySelector('#wrapwrap') || document.body;
        let timer = null;
        new MutationObserver((mutations) => {
            for (const m of mutations) {
                if (m.addedNodes && m.addedNodes.length) {
                    const t = m.target;
                    if (t && (t.matches?.('.o_cart, .o_wsale_cart') || t.closest?.('.o_cart, .o_wsale_cart'))) {
                        clearTimeout(timer);
                        timer = setTimeout(() => injectAll(document), 50);
                        break;
                    }
                }
            }
        }).observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview injector listo');
    }

    domReady(boot);
});