/** SPW – Cart preview injector (multi-foto + píldoras) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    /* -------- ready sin dependencias -------- */
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else { cb(); }
    }

    /* -------- selectores robustos -------- */
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    /* -------- helpers -------- */
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return cand
            ? (cand.getAttribute?.('data-line-id') ||
               cand.getAttribute?.('data-id') ||
               cand.value || null)
            : null;
    }

    function basePreviewUrl(lineId) {
        return lineId ? `/spw/line_preview/${lineId}.png` : null;
    }

    function parsePreviewsFromAttr(el) {
        const raw = el.getAttribute('data-spw-previews') ||
                    el.closest(LINE_SEL)?.getAttribute('data-spw-previews') ||
                    '';
        if (!raw) return [];
        try {
            const arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr.filter(Boolean) : [];
        } catch {
            // también aceptamos CSV simple
            return raw.split(',').map(s => s.trim()).filter(Boolean);
        }
    }

    function parseColors(text) {
        if (!text) return [];
        const out = [];
        const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g;
        let m;
        while ((m = re.exec(text))) {
            const hex = m[1].toUpperCase();
            if (!out.includes(hex)) out.push(hex);
        }
        return out;
    }

    function alreadyInjected(root) {
        return !!root.querySelector('.spw-cart-preview');
    }

    /* -------- inyección -------- */
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info || alreadyInjected(info)) return;

        const lineId = getLineId(lineEl);
        // 1) si el backend nos dejó una lista, úsala
        let urls = parsePreviewsFromAttr(info);
        // 2) si no hay lista, usa la única segura (última guardada)
        if (!urls.length && lineId) urls = [basePreviewUrl(lineId)];

        const colors = parseColors(info.textContent || '');

        const wrap = document.createElement('div');
        wrap.className = 'spw-cart-preview';
        wrap.style.cssText = 'margin-top:8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap';

        // imágenes
        urls.forEach((u) => {
            if (!u) return;
            const img = new Image();
            img.loading = 'lazy';
            img.alt = 'Personalización';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            // cache-buster suave
            const sep = u.includes('?') ? '&' : '?';
            img.src = `${u}${sep}v=${Date.now()}`;
            img.onerror = () => img.remove();
            wrap.appendChild(img);
        });

        // píldoras (todas las que encuentre)
        colors.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText = 'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb;margin-left:2px';
            pill.style.background = hex;
            wrap.appendChild(pill);
        });

        if (wrap.children.length) info.appendChild(wrap);
    }

    function initialInject() {
        document.querySelectorAll(LINE_SEL).forEach(injectInto);
    }

    function observeMutations() {
        const target = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
        const mo = new MutationObserver((mutations) => {
            for (const m of mutations) {
                (m.addedNodes || []).forEach((n) => {
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
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (fotos + píldoras)');
    }

    onReady(boot);
});