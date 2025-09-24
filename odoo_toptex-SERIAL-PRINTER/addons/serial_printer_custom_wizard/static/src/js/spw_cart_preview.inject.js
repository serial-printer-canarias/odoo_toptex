/** @odoo-module **/

/**
 * Inyector de vista previa y píldora de color en el carrito.
 * - Wrapper correcto con odoo.define('@module/path', function (require) { ... })
 * - Sin dependencias raras: solo 'web.dom_ready'
 * - Idempotente: no duplica el bloque si ya existe
 * - Resistente a actualizaciones AJAX: usa MutationObserver
 */

odoo.define('@serial_printer_custom_wizard/js/spw_cart_preview.inject', function (require) {
    'use strict';

    const domReady = require('web.dom_ready');

    // ---- Utilidades ---------------------------------------------------------

    function getLineId(container) {
        // Busca data-line-id en la línea del carrito (Odoo 16/17/18)
        const el =
            container.closest('[data-line-id]') ||
            container.querySelector?.('[data-line-id]') ||
            container.closest('.o_wsale_cart_item') ||
            container.closest('tr') ||
            null;
        return el && el.getAttribute('data-line-id');
    }

    function buildPreviewUrl(lineId) {
        // Ajusta si tu route es distinta
        // Ej: '/spw/line_preview/<id>.png'
        return lineId ? `/spw/line_preview/${lineId}.png` : null;
    }

    function extractHexFromText(text) {
        // Busca "Color SVG: #RRGGBB" o "#RGB"
        const m = (text || '').match(/Color\s*SVG[:\s]*#?([0-9a-fA-F]{3,8})/);
        if (!m) return null;
        const hex = m[1];
        return hex ? `#${hex.replace(/^#/, '')}` : null;
    }

    function injectOnce(infoEl) {
        if (!infoEl || infoEl.querySelector('.spw-cart-preview')) return;

        const lineId = getLineId(infoEl);
        const url = buildPreviewUrl(lineId);

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview mt-2 d-flex align-items-center';
        wrap.style.gap = '8px';
        wrap.style.flexWrap = 'wrap';

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

        const hex = extractHexFromText(infoEl.textContent);
        if (hex && /^#[0-9a-fA-F]{3,8}$/.test(hex)) {
            const pill = document.createElement('span');
            pill.className = 'spw-color-pill';
            pill.title = hex;
            pill.style.display = 'inline-block';
            pill.style.width = '16px';
            pill.style.height = '16px';
            pill.style.borderRadius = '9999px';
            pill.style.border = '1px solid #e5e7eb';
            pill.style.background = hex;
            wrap.appendChild(pill);
        }

        if (wrap.children.length) {
            infoEl.appendChild(wrap);
        }
    }

    function injectAll(root) {
        (root || document)
            .querySelectorAll('.o_wsale_product_information')
            .forEach(injectOnce);
    }

    // ---- Inicio -------------------------------------------------------------

    function boot() {
        // Solo en páginas del website (carrito)
        if (!document.querySelector('.o_cart, .o_wsale_cart')) return;

        // Inyección inicial
        injectAll(document);

        // Reinyectar si Odoo actualiza el DOM (cambios de cantidad, etc.)
        const target = document.querySelector('#wrapwrap') || document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                if (m.addedNodes && m.addedNodes.length) {
                    injectAll(document);
                    break;
                }
            }
        });
        mo.observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview injector listo');
    }

    domReady(boot);
});