odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function (require) {
    'use strict';

    // ---- utilidades sin dependencias externas ----
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else {
            cb();
        }
    }

    const WRAP_CLASS = 'spw-cart-preview';
    const PREVIEW_BASE = '/spw/line_preview'; // /spw/line_preview/<line_id>.png

    const INFO_SELECTORS = [
        '.o_wsale_product_information',
        '.media-body',
        '.o_cart_line_details',
        '.o_cart_item_info',
    ];

    const $$ = (root, sel) => Array.from(root.querySelectorAll(sel));
    const getLineRoot = (el) =>
        el.closest('[data-line-id]') || el.closest('.o_cart_product') || el.closest('tr');
    const getLineId = (el) => {
        const r = getLineRoot(el);
        return (r && (r.getAttribute('data-line-id') || r.dataset.lineId)) || null;
    };
    const getInfoContainer = (lineRoot) => {
        for (const s of INFO_SELECTORS) {
            const n = lineRoot.querySelector(s);
            if (n) return n;
        }
        return null;
    };
    const extractHexFromText = (txt) => {
        if (!txt) return null;
        const m = txt.match(/SVG\s*:\s*(#[0-9a-fA-F]{3,6})/);
        return m ? m[1] : null;
    };

    function buildPreview(lineRoot) {
        const info = getInfoContainer(lineRoot);
        if (!info) return;

        // evita duplicados
        const old = info.querySelector('.' + WRAP_CLASS);
        if (old) old.remove();

        const lineId = getLineId(lineRoot);

        const wrap = document.createElement('div');
        wrap.className = `${WRAP_CLASS} d-flex align-items-center mt-2`;
        wrap.style.gap = '8px';
        wrap.style.flexWrap = 'wrap';

        // miniatura PNG
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

        // píldora color (lee “SVG: #RRGGBB” del texto)
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
        const lines = $$(root, '.o_cart_product, .o_wsale_cart_item, tr[data-line-id]');
        if (!lines.length) return;
        lines.forEach(buildPreview);
    }

    function boot() {
        // solo en carrito
        if (!document.querySelector('.o_cart, .o_wsale_cart')) return;

        injectAll(document);

        // reinyectar en cambios del DOM
        const target = document.querySelector('#wrapwrap') || document.body;
        let timer = null;
        new MutationObserver((mutations) => {
            for (const m of mutations) {
                if (m.addedNodes && m.addedNodes.length) {
                    const t = m.target;
                    if (t && (t.matches?.('.o_cart, .o_wsale_cart') || t.closest?.('.o_cart, .o_wsale_cart'))) {
                        clearTimeout(timer);
                        timer = setTimeout(() => injectAll(document), 60);
                        break;
                    }
                }
            }
        }).observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview injector listo');
    }

    onReady(boot);
});