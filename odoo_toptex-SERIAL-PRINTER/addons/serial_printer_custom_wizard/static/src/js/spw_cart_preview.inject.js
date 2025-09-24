/** spw_cart_preview.inject.js
 * Inyecta miniatura de personalización + píldora de color en las líneas del carrito.
 * Seguro en Odoo (AMD): odoo.define('…', [], function (require) { … })
 */

odoo.define('@serial_printer_custom_wizard/js/spw_cart_preview.inject', [], function (require) {
    'use strict';

    /* ----------------- helpers ----------------- */

    function domReady(cb) {
        if (document.readyState !== 'loading') cb();
        else document.addEventListener('DOMContentLoaded', cb, { once: true });
    }

    function getLineId(container) {
        // Busca un data-line-id en la jerarquía de la línea
        const el =
            container.closest?.('[data-line-id]') ||
            container.querySelector?.('[data-line-id]') ||
            container.closest?.('.o_wsale_cart_item') ||
            container.closest?.('.o_cart_item') ||
            container.closest?.('tr');
        return el && el.getAttribute('data-line-id');
    }

    function buildPreviewUrl(lineId) {
        // Ajusta la ruta si en tu server es otra
        return lineId ? `/spw/line_preview/${lineId}.png` : null;
    }

    function extractHexFromText(text) {
        if (!text) return null;
        const m = String(text).match(/#[0-9a-fA-F]{3,8}\b/);
        return m ? m[0] : null;
    }

    function safeParseJSON(s) {
        try { return JSON.parse(s); } catch (_) { return null; }
    }

    /* --------- inyector por línea de carrito --------- */

    function injectOnce(lineEl) {
        if (!lineEl || lineEl.dataset.spwInjected === '1') return;
        lineEl.dataset.spwInjected = '1';

        // Contenedor de info (debajo de la descripción)
        const infoEl =
            lineEl.querySelector('.o_wsale_product_information') ||
            lineEl.querySelector('.o_wsale_cart_description') ||
            lineEl.querySelector('.media-body') ||
            lineEl.querySelector('.o_cart_product') ||
            lineEl;

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview mt-2 d-flex align-items-center';
        wrap.style.gap = '8px';
        wrap.style.flexWrap = 'wrap';

        // --- Miniatura ---
        const lineId = getLineId(lineEl);
        const url = buildPreviewUrl(lineId);
        if (url) {
            const img = document.createElement('img');
            img.src = url;
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.maxWidth = '120px';
            img.style.height = 'auto';
            img.style.border = '1px solid #e5e7eb';
            img.style.borderRadius = '6px';
            wrap.appendChild(img);
        }

        // --- Píldora de color ---
        // 1) probar attributes data-*
        let hex =
            lineEl.getAttribute('data-spw-svg-color') ||
            (safeParseJSON(lineEl.getAttribute('data-spw-meta-json'))?.svg_color) ||
            (safeParseJSON(lineEl.getAttribute('data-spw-meta-json'))?.color) ||
            null;

        // 2) si no hay, intentar extraer del texto de la descripción
        if (!hex) hex = extractHexFromText(infoEl.textContent);

        if (hex && /^#[0-9a-fA-F]{3,8}$/.test(hex)) {
            const pill = document.createElement('span');
            pill.title = 'Color';
            pill.style.display = 'inline-block';
            pill.style.width = '16px';
            pill.style.height = '16px';
            pill.style.borderRadius = '9999px';
            pill.style.border = '1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        }

        if (wrap.children.length) infoEl.appendChild(wrap);
    }

    /* ----------------- boot ----------------- */

    function injectAll(root) {
        (root || document).querySelectorAll(
            '.o_wsale_cart .o_cart_product, .o_cart_item, tr.js_cart_lines, .o_wsale_cart_item'
        ).forEach(injectOnce);
    }

    domReady(function () {
        // Solo si estamos en carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart')) return;

        // Inyección inicial
        injectAll(document);

        // Re-inyectar si Odoo cambia el DOM (qty, AJAX, etc.)
        const target = document.querySelector('#wrapwrap') || document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (!(node instanceof HTMLElement)) continue;
                    if (node.matches?.('.o_cart_product, .o_cart_item, tr.js_cart_lines, .o_wsale_cart_item')) {
                        injectOnce(node);
                    } else if (node.querySelectorAll) {
                        node.querySelectorAll('.o_cart_product, .o_cart_item, tr.js_cart_lines, .o_wsale_cart_item')
                            .forEach(injectOnce);
                    }
                }
            }
        });
        mo.observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview injector listo');
    });
});