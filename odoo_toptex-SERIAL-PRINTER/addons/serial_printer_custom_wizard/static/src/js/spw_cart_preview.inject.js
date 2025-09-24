odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function (require) {
    'use strict';

    /* ========= helpers ========= */
    const $$ = (root, sel) => Array.from(root.querySelectorAll(sel));
    const onceFlag = 'data-spw-cart-preview-done';

    function domReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    // Line root: funciona en plantillas clásicas y nuevas
    function getLineRoot(node) {
        return node.closest?.('[data-line-id], .o_cart_product, .o_wsale_cart_item, li.js_cart_line, tr[name="cart_line"]');
    }
    function getLineId(lineRoot) {
        if (!lineRoot) return null;
        return (
            lineRoot.getAttribute('data-line-id') ||
            lineRoot.dataset?.lineId ||
            lineRoot.querySelector('input[name="line_id"]')?.value ||
            null
        );
    }

    // Contenedor de información donde pegamos el preview (varios fallbacks)
    function getInfoContainer(lineRoot) {
        if (!lineRoot) return null;
        const sel = [
            '.o_wsale_product_information',
            '.o_cart_line_details',
            '.o_cart_item_info',
            '.media-body',
            '.product_name, .o_wsale_product_name',
        ].join(',');
        return lineRoot.querySelector(sel) || lineRoot; // último recurso
    }

    // Busca color tipo “SVG: #112233” en el texto de la línea
    function pickHex(lineRoot) {
        const txt = (lineRoot.textContent || '').replace(/\s+/g, ' ');
        const m = txt.match(/SVG\s*:\s*(#[0-9a-fA-F]{3,6})/);
        return m ? m[1] : null;
    }

    // Construye y añade miniatura + píldora (evita duplicados)
    function injectFor(lineRoot) {
        if (!lineRoot || lineRoot.hasAttribute(onceFlag)) return;
        const lineId = getLineId(lineRoot);
        const infoEl = getInfoContainer(lineRoot);
        if (!infoEl) return;

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview d-flex align-items-center mt-2';
        wrap.style.gap = '8px';
        wrap.style.flexWrap = 'wrap';

        // Miniatura PNG si tenemos lineId
        if (lineId) {
            const img = document.createElement('img');
            img.src = `/spw/line_preview/${lineId}.png`;
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.maxWidth = '120px';
            img.style.height = 'auto';
            img.style.border = '1px solid #e5e7eb';
            img.style.borderRadius = '6px';
            wrap.appendChild(img);
        }

        // Píldora de color (si existe HEX)
        const hex = pickHex(lineRoot);
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

        if (wrap.children.length) {
            infoEl.appendChild(wrap);
            lineRoot.setAttribute(onceFlag, '1');
        }
    }

    // Recorre todas las líneas del carrito y aplica
    function injectAll(root) {
        root = root || document;
        const lines = $$(
            root,
            '.o_cart_product, .o_wsale_cart_item, [data-line-id], li.js_cart_line, tr[name="cart_line"]'
        );
        lines.forEach(injectFor);
    }

    function boot() {
        // Ejecuta siempre (aunque el tema no marque el body), pero solo si hay líneas
        injectAll(document);

        // Reinyecta cuando Odoo toque el DOM (qty, ajax, etc.)
        const target = document.querySelector('#wrapwrap') || document.body;
        const mo = new MutationObserver(() => injectAll(document));
        mo.observe(target, { childList: true, subtree: true });

        console.log('[SPW] cart preview listo');
    }

    domReady(boot);
});