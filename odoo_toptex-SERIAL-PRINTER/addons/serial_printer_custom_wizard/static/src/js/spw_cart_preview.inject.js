/** SPW – Cart preview injector (1 imagen + 1 píldora por línea, sin romper update) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------------- ready ----------------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else {
            cb();
        }
    }

    // ---------------- selectores robustos ----------------
    // Contenedores de línea típicos en website_sale / temas
    const LINE_SEL =
        [
            '.o_cart_product',              // core
            '.o_wsale_cart_item',           // core (cards)
            '.js_cart_lines tr',            // tabla clásica
            '.cart_line'                    // temas
        ].join(',');

    // Sitio donde inyectar (descripción/info del producto por línea)
    const INFO_SEL =
        [
            '.o_wsale_product_information',
            '.o_wsale_cart_description',
            '.o_wsale_cart_item_description',
            '.product-name',
            '.oe_subdescription'
        ].join(',');

    // ---------------- utils ----------------
    const exts = ['png', 'webp', 'jpg', 'jpeg'];

    function ts() { return Date.now(); }

    function addQuery(url, params) {
        const u = new URL(url, window.location.origin);
        Object.entries(params || {}).forEach(([k, v]) => u.searchParams.set(k, v));
        return u.pathname + (u.search ? u.search : '');
    }

    // ⚠️ Sólo se usará cuando renderizamos “sin” un nodo de línea (caso muy raro)
    function urlLineId() {
        try {
            const m = location.search.match(/[?&]spw_line_id=(\d+)/);
            return m ? m[1] : null;
        } catch (_) {
            return null;
        }
    }

    // Obtener el ID real de la línea en DOM (sin fallback a URL si tengo nodo)
    function getLineId(lineEl) {
        if (!lineEl) return urlLineId(); // solo si no hay nodo
        const c = lineEl.hasAttribute && lineEl.hasAttribute('data-line-id') ? lineEl :
            lineEl.querySelector?.('[data-line-id]') ||
            lineEl.querySelector?.('input[name="line_id"]') ||
            lineEl.querySelector?.('button[data-line-id], a[data-line-id]');
        const val = (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || null;
        return (val && /^\d+$/.test(String(val))) ? String(val) : null;
    }

    // Primera coincidencia de color tipo #RRGGBB/#RGB en el texto visible de la línea
    function firstColor(text) {
        const m = /#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b/.exec(text || '');
        return m ? m[0] : null;
    }

    // Crear contenedor idempotente para la preview en la línea
    function ensureWrap(info) {
        let wrap = info.querySelector('.spw-cart-preview');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;flex-wrap:wrap';

            const imgs = document.createElement('div');
            imgs.className = 'spw-imgs';
            imgs.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start';

            const pills = document.createElement('div');
            pills.className = 'spw-pills';
            pills.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-items:center';

            wrap.appendChild(imgs);
            wrap.appendChild(pills);
            info.appendChild(wrap);
        }
        return wrap;
    }

    // Cargar la primera URL válida; si fallan todas, quitar la imagen
    function tryLoad(img, lineId) {
        const candidates = exts.map(ext => addQuery(`/spw/line_preview/${lineId}.${ext}`, { v: ts() }));
        let i = 0;
        function next() {
            if (i >= candidates.length) { img.remove(); return; }
            const url = candidates[i++];
            img.onerror = next;
            img.onload = null;
            img.src = url;
        }
        next();
    }

    // Render de UNA línea (1 imagen + 1 píldora)
    function renderLine(lineEl) {
        const info = lineEl.querySelector?.(INFO_SEL) || lineEl;
        if (!info) return;

        const lineId = getLineId(lineEl);
        if (!lineId) return; // sin id real, no pintamos (evita mezclar entre filas)

        // idempotencia: no re-renderizar si ya está hecho para ese id
        if (lineEl.dataset.spwRenderedFor === lineId) return;

        const wrap = ensureWrap(info);
        const imgsWrap = wrap.querySelector('.spw-imgs');
        const pillsWrap = wrap.querySelector('.spw-pills');

        imgsWrap.innerHTML = '';
        pillsWrap.innerHTML = '';

        // Píldora
        const hex = firstColor(info.textContent || '');
        const pill = document.createElement('span');
        pill.title = hex || '—';
        pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
        if (hex) pill.style.background = hex;
        pillsWrap.appendChild(pill);

        // Imagen
        const img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
        imgsWrap.appendChild(img);
        tryLoad(img, lineId);

        lineEl.dataset.spwRenderedFor = lineId;
    }

    function initialInject() {
        document.querySelectorAll(LINE_SEL).forEach(renderLine);
    }

    function observeMutations() {
        const root =
            document.querySelector('#o_cart') ||
            document.querySelector('.o_wsale_cart_summary') ||
            document.querySelector('.js_cart_lines') ||
            document.body;

        const mo = new MutationObserver(ms => {
            for (const m of ms) {
                m.addedNodes && m.addedNodes.forEach(n => {
                    if (n instanceof HTMLElement) {
                        if (n.matches?.(LINE_SEL)) {
                            renderLine(n);
                        } else {
                            n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
                        }
                    }
                });
            }
        });
        mo.observe(root, { childList: true, subtree: true });
    }

    function boot() {
        // Sólo en páginas de carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector activo: 1 imagen + 1 píldora por línea, sin fallback URL.');
    }

    onReady(boot);
});