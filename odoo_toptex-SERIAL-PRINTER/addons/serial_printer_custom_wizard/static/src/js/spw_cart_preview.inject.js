/** spw_cart_preview.inject.js
 * Inyecta miniatura de personalización + píldora de color en las líneas del carrito.
 * Seguro en Odoo (AMD): nombre + array de deps vacío.
 */
odoo.define('@serial_printer_custom_wizard/js/spw_cart_preview.inject', [], function (require) {
    'use strict';

    console.log('[SPW] injector cargado');

    /* ----------------- helpers ----------------- */

    function domReady(cb) {
        if (document.readyState !== 'loading') cb();
        else document.addEventListener('DOMContentLoaded', cb, { once: true });
    }

    function $(root, sel) {
        return (root || document).querySelector(sel);
    }
    function $all(root, sel) {
        return (root || document).querySelectorAll(sel);
    }

    // Intenta encontrar el ID de la línea de carrito en múltiples formas
    function getLineId(lineEl) {
        if (!lineEl) return null;

        // 1) Atributos data-* más comunes
        const attrs = ['data-line-id', 'data-id', 'data-orderline-id', 'data-order-line-id'];
        for (const a of attrs) {
            const v = lineEl.getAttribute(a);
            if (v && /^\d+$/.test(v)) return v;
        }

        // 2) Buscar en ancestros/hermanos cercanos
        let el = lineEl.closest('[data-line-id],[data-orderline-id],[data-order-line-id],[data-id]');
        if (el) {
            for (const a of attrs) {
                const v = el.getAttribute(a);
                if (v && /^\d+$/.test(v)) return v;
            }
        }

        // 3) Inputs ocultos típicos
        const hidden = lineEl.querySelector('input[name="line_id"], input[name="line-id"], input[data-line-id]');
        if (hidden) {
            const v = hidden.value || hidden.getAttribute('data-line-id');
            if (v && /^\d+$/.test(v)) return v;
        }

        // 4) Filas de tabla
        el = lineEl.closest('tr');
        if (el) {
            for (const a of attrs) {
                const v = el.getAttribute(a);
                if (v && /^\d+$/.test(v)) return v;
            }
        }

        return null;
    }

    function buildPreviewUrl(lineId) {
        // Ajusta si tu endpoint es otro
        return lineId ? `/spw/line_preview/${lineId}.png` : null;
    }

    function safeJSON(s) { try { return JSON.parse(s); } catch { return null; } }

    function pickHex(lineEl, infoEl) {
        // Prioriza data-attrs / JSON; si no, intenta extraer del texto ("SVG: #RRGGBB")
        const meta = safeJSON(lineEl.getAttribute('data-spw-meta-json')) || {};
        const cand = lineEl.getAttribute('data-spw-svg-color') || meta.svg_color || meta.color;
        if (cand && /^#[0-9a-fA-F]{3,8}$/.test(cand)) return cand;

        const m = String(infoEl?.textContent || '').match(/#[0-9a-fA-F]{3,8}\b/);
        return m ? m[0] : null;
    }

    /* --------- inyección por línea --------- */

    function injectOnce(lineEl) {
        if (!lineEl || lineEl.dataset.spwInjected === '1') return;
        lineEl.dataset.spwInjected = '1';

        // Contenedor de info donde pegaremos el bloque
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

        // --- Miniatura (si tenemos line_id) ---
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
        const hex = pickHex(lineEl, infoEl);
        if (hex) {
            const pill = document.createElement('span');
            pill.title = `Color ${hex}`;
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

    function findCartLines(root) {
        const selectors = [
            // tarjetas
            '.o_wsale_cart_item',
            '.o_cart_item',
            '.o_cart_product',
            // tabla
            'tr.js_cart_lines',
            'tr.o_wsale_cart_item',
        ];
        const set = new Set();
        for (const sel of selectors) {
            $all(root, sel).forEach((el) => set.add(el.closest(sel)));
        }
        return Array.from(set).filter(Boolean);
    }

    function injectAll(root) {
        const lines = findCartLines(root || document);
        lines.forEach(injectOnce);
        console.log(`[SPW] inyectadas ${lines.length} líneas`);
    }

    /* ----------------- boot ----------------- */

    domReady(function () {
        // Inyectar siempre; si no estamos en carrito simplemente no encontrará líneas y no hará nada.
        injectAll(document);

        // Re-inyectar con cambios de DOM (qty/AJAX)
        const target = $('#wrapwrap') || document.body;
        const mo = new MutationObserver((mutations) => {
            let touched = false;
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (!(node instanceof HTMLElement)) continue;
                    if (findCartLines(node).length) {
                        injectAll(node);
                        touched = true;
                    }
                }
            }
            if (touched) console.log('[SPW] reinyección tras mutación');
        });
        mo.observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview injector listo');
    });
});