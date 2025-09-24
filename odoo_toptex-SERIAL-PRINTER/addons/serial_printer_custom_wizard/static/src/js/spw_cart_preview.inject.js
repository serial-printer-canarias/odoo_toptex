/** spw_cart_preview.inject.js
 * Inyecta miniatura PNG + píldora de color en las líneas del carrito.
 * Patrón seguro Odoo: odoo.define(nombre, [deps], function(require){...})
 * 👉 Dependemos SOLO de 'web.dom_ready' (nada de web.public.widget).
 */
odoo.define('@serial_printer_custom_wizard/js/spw_cart_preview.inject', ['web.dom_ready'], function (require) {
    'use strict';
    const domReady = require('web.dom_ready');

    /* ----------------- helpers ----------------- */
    const $ = (root, sel) => (root || document).querySelector(sel);
    const $all = (root, sel) => (root || document).querySelectorAll(sel);
    const safeJSON = (s) => { try { return JSON.parse(s); } catch { return null; } };

    // Detecta line_id de forma robusta
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const ATTRS = ['data-line-id', 'data-id', 'data-orderline-id', 'data-order-line-id'];
        for (const a of ATTRS) {
            const v = lineEl.getAttribute(a);
            if (v && /^\d+$/.test(v)) return v;
        }
        let n = lineEl.closest('[data-line-id],[data-orderline-id],[data-order-line-id],[data-id]');
        if (n) {
            for (const a of ATTRS) {
                const v = n.getAttribute(a);
                if (v && /^\d+$/.test(v)) return v;
            }
        }
        const hid = lineEl.querySelector('input[name="line_id"], input[name="line-id"], input[data-line-id]');
        if (hid) {
            const v = hid.value || hid.getAttribute('data-line-id');
            if (v && /^\d+$/.test(v)) return v;
        }
        const a = lineEl.querySelector('a[href*="line_id="], button[data-params*="line_id="]');
        if (a) {
            const m = (a.getAttribute('href') || a.getAttribute('data-params') || '').match(/line_id=(\d+)/);
            if (m) return m[1];
        }
        n = lineEl.closest('tr');
        if (n) {
            for (const a2 of ATTRS) {
                const v = n.getAttribute(a2);
                if (v && /^\d+$/.test(v)) return v;
            }
        }
        return null;
    }

    const buildPreviewUrl = (lineId) => (lineId ? `/spw/line_preview/${lineId}.png` : null);

    function pickHex(lineEl, infoEl) {
        const meta = safeJSON(lineEl.getAttribute('data-spw-meta-json')) || {};
        const cand = lineEl.getAttribute('data-spw-svg-color') || meta.svg_color || meta.color;
        if (cand && /^#[0-9a-fA-F]{3,8}$/.test(cand)) return cand;
        const m = String(infoEl?.textContent || '').match(/#[0-9a-fA-F]{3,8}\b/);
        return m ? m[0] : null;
    }

    function findCartLines(root) {
        const selectors = [
            '.o_wsale_cart_item', '.o_cart_item', '.o_cart_product',
            'tr.js_cart_lines', 'tr.o_wsale_cart_item',
        ];
        const set = new Set();
        selectors.forEach(sel => $all(root, sel).forEach(el => set.add(el.closest(sel))));
        return Array.from(set).filter(Boolean);
    }

    function injectOnce(lineEl) {
        if (lineEl.dataset.spwInjected === '1') return;
        lineEl.dataset.spwInjected = '1';

        const infoEl =
            lineEl.querySelector('.o_wsale_product_information') ||
            lineEl.querySelector('.o_wsale_cart_description') ||
            lineEl.querySelector('.media-body') ||
            lineEl.querySelector('.o_cart_product') ||
            lineEl;

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview mt-2 d-flex align-items-center';
        Object.assign(wrap.style, { gap: '8px', flexWrap: 'wrap' });

        // Miniatura PNG
        const lid = getLineId(lineEl);
        const url = buildPreviewUrl(lid);
        if (url) {
            const img = document.createElement('img');
            img.src = url;
            img.alt = 'Personalización';
            img.loading = 'lazy';
            Object.assign(img.style, {
                maxWidth: '120px',
                height: 'auto',
                border: '1px solid #e5e7eb',
                borderRadius: '6px',
            });
            wrap.appendChild(img);
        }

        // Píldora de color
        const hex = pickHex(lineEl, infoEl);
        if (hex) {
            const pill = document.createElement('span');
            pill.title = `Color ${hex}`;
            Object.assign(pill.style, {
                display: 'inline-block',
                width: '16px',
                height: '16px',
                borderRadius: '9999px',
                border: '1px solid #e5e7eb',
                background: hex,
            });
            wrap.appendChild(pill);
        }

        if (wrap.children.length) infoEl.appendChild(wrap);
    }

    function injectAll(root) {
        const lines = findCartLines(root || document);
        lines.forEach(injectOnce);
        console.log(`[SPW] inyectadas ${lines.length} líneas`);
    }

    function boot() {
        // Solo si estamos en la página de carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart, .oe_website_sale')) return;

        injectAll(document);

        // Reinyectar tras cambios dinámicos (qty/AJAX)
        const target = $('#wrapwrap') || document.body;
        const mo = new MutationObserver(muts => {
            let hit = false;
            for (const m of muts) {
                for (const n of m.addedNodes) {
                    if (n.nodeType === 1 && (findCartLines(n).length ||
                        n.querySelector?.('.o_wsale_product_information, .o_wsale_cart_description, .o_cart_product'))) {
                        injectAll(n);
                        hit = true;
                    }
                }
            }
            if (hit) console.log('[SPW] reinyección tras mutación');
        });
        mo.observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview injector listo (dom_ready)');
    }

    domReady(boot);
    console.log('[SPW] injector cargado');
});