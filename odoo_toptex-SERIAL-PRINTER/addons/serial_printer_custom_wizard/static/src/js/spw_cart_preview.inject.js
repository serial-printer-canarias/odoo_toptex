/** SPW – Cart preview injector (múltiples fotos persistentes + píldoras HEX) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    /* -------------------- ready sin dependencias -------------------- */
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else cb();
    }

    /* -------------------- selectores robustos ----------------------- */
    const LINE_SEL =
        '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL =
        '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    /* --------------------------- helpers ---------------------------- */
    function getLineId(lineEl) {
        if (!lineEl) return null;
        const cand =
            lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        const id = cand
            ? (cand.getAttribute?.('data-line-id') ||
               cand.getAttribute?.('data-id') ||
               cand.value || '')
            : '';
        return id || null;
    }

    // Extrae TODOS los HEX en orden
    function extractHexes(text) {
        if (!text) return [];
        const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g;
        const out = [];
        let m; while ((m = re.exec(text))) out.push(m[1]);
        return out;
    }

    function buildUrl(lineId, idx, ext) {
        const sfx = idx > 0 ? `-${idx}` : '';
        return `/spw/line_preview/${lineId}${sfx}.${ext}?v=${Date.now()}`;
    }

    // Crea o devuelve nuestro bloque persistente
    function ensureWrap(info) {
        let wrap = info.querySelector('.spw-cart-preview');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'margin-top:10px;display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap';
            const imgs = document.createElement('div');
            imgs.className = 'spw-cart-preview__imgs';
            imgs.style.cssText = 'display:flex;flex-direction:column;gap:10px';
            const pills = document.createElement('div');
            pills.className = 'spw-cart-preview__pills';
            pills.style.cssText = 'display:flex;flex-direction:column;gap:6px;min-width:18px';
            wrap.append(imgs, pills);
            info.appendChild(wrap);
        }
        return {
            wrap,
            imgCol: wrap.querySelector('.spw-cart-preview__imgs'),
            pillsCol: wrap.querySelector('.spw-cart-preview__pills'),
        };
    }

    // Añade imagen si no existe ya (clave por URL sin query)
    function addImgOnce(imgCol, url) {
        const key = url.replace(/\?.*$/, '');
        if (imgCol.querySelector(`img[data-spw-src="${key}"]`)) return false;
        const img = new Image();
        img.decoding = 'async';
        img.loading = 'lazy';
        img.alt = 'Personalización';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
        img.dataset.spwSrc = key;
        img.src = url;
        imgCol.appendChild(img);
        return true;
    }

    // Intenta /id.webp|png y /id-1, -2, … (no limpia, sólo añade nuevas)
    function loadAllPreviews(lineId, imgCol, maxIdx = 12) {
        for (let idx = 0; idx <= maxIdx; idx++) {
            // webp luego png; si ya existe alguna, se omite
            const urls = [buildUrl(lineId, idx, 'webp'), buildUrl(lineId, idx, 'png')];
            // si ya existe cualquiera de las dos, saltamos
            const key0 = urls[0].replace(/\?.*$/, '');
            const key1 = urls[1].replace(/\?.*$/, '');
            if (imgCol.querySelector(`img[data-spw-src="${key0}"], img[data-spw-src="${key1}"]`)) continue;

            // probar webp y si falla no quitamos nada; probamos png
            const img = new Image();
            img.decoding = 'async';
            img.loading = 'lazy';
            img.alt = 'Personalización';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
            img.dataset.spwSrc = key0;
            img.onerror = () => {
                img.onerror = null;
                img.dataset.spwSrc = key1;
                img.src = urls[1];
            };
            img.src = urls[0];
            imgCol.appendChild(img);
        }
    }

    /* ---------------------- inyección por línea ---------------------- */
    function injectInto(lineEl) {
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info) return;

        const { wrap, imgCol, pillsCol } = ensureWrap(info);

        const lineId = getLineId(lineEl);
        const hexes  = extractHexes(info.textContent || '');

        // Actualiza píldoras (vertical) — las fotos NO se tocan
        pillsCol.innerHTML = '';
        hexes.forEach((hex) => {
            const pill = document.createElement('span');
            pill.title = hex;
            pill.style.cssText = 'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
            pill.style.background = hex;
            pillsCol.appendChild(pill);
        });

        // Carga/añade imágenes sin borrar las existentes
        if (lineId) {
            wrap.dataset.lineId = lineId;
            loadAllPreviews(lineId, imgCol, 12);
        }
    }

    function initialInject() {
        document.querySelectorAll(LINE_SEL).forEach(injectInto);
    }

    function observeMutations() {
        const target =
            document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') ||
            document.body;
        const mo = new MutationObserver((muts) => {
            muts.forEach((m) => {
                m.addedNodes && m.addedNodes.forEach((n) => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches?.(LINE_SEL)) injectInto(n);
                    else n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
                });
            });
        });
        mo.observe(target, { childList: true, subtree: true });
    }

    function boot() {
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] persistente: fotos + píldoras listo');
    }

    onReady(boot);
});