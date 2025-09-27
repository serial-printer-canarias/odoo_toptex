/** SPW - Cart preview injector (multi-foto por línea; ES5 safe) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- READY ----------
    function onReady(cb) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function once() {
                document.removeEventListener('DOMContentLoaded', once);
                try { cb(); } catch (e) { console.error('[SPW]', e); }
            });
        } else {
            try { cb(); } catch (e) { console.error('[SPW]', e); }
        }
    }

    // ---------- SELECTORES ----------
    var LINE_SEL = 'tr.js_cart_line, .o_wsale_cart_item, .card.js_cart_item, .o_cart_line, .o_cart_product';
    var INFO_SEL = '.o_wsale_product_information, .o_cart_product_info, td.o_wsale_cart_description, .media-body, .oe_subdescription';

    // ---------- UTILS ----------
    function ts() { return (new Date()).getTime(); }

    function urlParam(name) {
        try { return new URL(window.location.href).searchParams.get(name); } catch (_) { return null; }
    }

    function addQuery(url, params) {
        var hasQ = url.indexOf('?') !== -1;
        var out = url;
        for (var k in params) {
            if (!params.hasOwnProperty(k)) continue;
            out += (hasQ ? '&' : '?') + encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
            hasQ = true;
        }
        return out;
    }

    function parseLineIdFromHref(node) {
        try {
            var a = (node.closest && node.closest('a[href*="line_id="]')) || (node.querySelector && node.querySelector('a[href*="line_id="]'));
            if (!a) return null;
            var u = new URL(a.getAttribute('href'), window.location.origin);
            return u.searchParams.get('line_id');
        } catch (_) { return null; }
    }

    function getLineId(lineEl) {
        if (!lineEl) return null;
        var c = lineEl.getAttribute('data-line-id') ? lineEl :
            (lineEl.querySelector && (
                lineEl.querySelector('[data-line-id]') ||
                lineEl.querySelector('input[name="line_id"]') ||
                lineEl.querySelector('button[data-line-id], a[data-line-id]')
            ));
        var val = (c && (c.getAttribute && (c.getAttribute('data-line-id') || c.getAttribute('data-id')) || c.value)) || parseLineIdFromHref(lineEl) || null;
        return val && String(val);
    }

    // Detecta el número de personalizaciones a partir de colores "#RRGGBB" en el texto
    function parsePersonalizations(text) {
        if (!text) return [];
        var out = [];
        var re = /#([0-9a-fA-F]{6})\b/g;
        var m, i = 0;
        while ((m = re.exec(text))) {
            out.push({ idx: i++, hex: ('#' + m[1]).toUpperCase() });
        }
        // Si no hay colores, intentamos al menos 1 preview
        return out.length ? out : [{ idx: 0, hex: null }];
    }

    // Genera rutas candidatas para /spw/line_preview/<line_id> con índice 1..n
    function buildUrlCandidates(lineId, idx) {
        var n = idx + 1;
        var base = '/spw/line_preview/' + encodeURIComponent(lineId);
        var exts = ['png', 'webp', 'jpg', 'jpeg'];
        var bases = [
            base + '-' + n,   // /spw/line_preview/123-1.png
            base + '/' + n,   // /spw/line_preview/123/1.png
            base + '_' + n    // /spw/line_preview/123_1.png
        ];
        var urls = [];
        var i, j;

        for (i = 0; i < bases.length; i++) {
            for (j = 0; j < exts.length; j++) {
                urls.push(addQuery(bases[i] + '.' + exts[j], { v: ts() }));
            }
        }
        // ?i=n con y sin extensión
        for (j = 0; j < exts.length; j++) {
            urls.push(addQuery(base + '.' + exts[j], { i: n, v: ts() }));
        }
        urls.push(addQuery(base, { i: n, v: ts() }));

        // Fallback único por índice
        for (j = 0; j < exts.length; j++) {
            urls.push(addQuery(base + '.' + exts[j], { i: n, fb: 1, v: ts() }));
        }

        // Dedup
        var seen = {};
        var dedup = [];
        for (i = 0; i < urls.length; i++) {
            if (!seen[urls[i]]) { seen[urls[i]] = 1; dedup.push(urls[i]); }
        }
        return dedup;
    }

    function ensureWrap(info) {
        var wrap = info.querySelector('.spw-cart-preview');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;flex-wrap:wrap';

            var imgs = document.createElement('div');
            imgs.className = 'spw-imgs';
            imgs.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start';

            var pills = document.createElement('div');
            pills.className = 'spw-pills';
            pills.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-items:center';

            wrap.appendChild(imgs);
            wrap.appendChild(pills);
            info.appendChild(wrap);
        }
        return wrap;
    }

    function tryLoad(img, candidates) {
        var k = 0;
        function next() {
            if (k >= candidates.length) { if (img.parentNode) img.parentNode.removeChild(img); return; }
            var url = candidates[k++];
            img.onerror = next;
            img.onload = null;
            img.src = url;
        }
        next();
    }

    function infoContainer(line) {
        return line.querySelector(INFO_SEL) || line;
    }

    function renderLine(lineEl) {
        var info = infoContainer(lineEl);
        if (!info) return;

        var lineId = getLineId(lineEl);
        if (!lineId) return;

        var wrap = ensureWrap(info);
        var imgsWrap = wrap.querySelector('.spw-imgs');
        var pillsWrap = wrap.querySelector('.spw-pills');

        // limpiar y volver a pintar (evita duplicados)
        imgsWrap.innerHTML = '';
        pillsWrap.innerHTML = '';

        var text = info.textContent || '';
        var persos = parsePersonalizations(text);

        for (var p = 0; p < persos.length; p++) {
            var hex = persos[p].hex;
            var idx = persos[p].idx;

            // píldora color
            var pill = document.createElement('span');
            pill.title = hex || '-';
            pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
            if (hex) pill.style.background = hex;
            pillsWrap.appendChild(pill);

            // imagen por índice
            var img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc';
            imgsWrap.appendChild(img);

            var candidates = buildUrlCandidates(lineId, idx);
            tryLoad(img, candidates);
        }
    }

    function initialInject() {
        var nodes = document.querySelectorAll(LINE_SEL);
        for (var i = 0; i < nodes.length; i++) renderLine(nodes[i]);

        // Fallback inmediato si venimos del customizer
        var wanted = urlParam('spw_line_id');
        if (wanted) {
            try {
                var lastId = sessionStorage.getItem('spw_last_line_id');
                var lastPng = sessionStorage.getItem('spw_last_png');
                var lastColor = sessionStorage.getItem('spw_last_color');
                if (lastId && lastPng && lastId === wanted) {
                    for (var j = 0; j < nodes.length; j++) {
                        var lid = getLineId(nodes[j]);
                        if (lid === wanted) {
                            var info = infoContainer(nodes[j]);
                            if (!info) continue;
                            var wrap = ensureWrap(info);
                            var imgsWrap = wrap.querySelector('.spw-imgs');
                            var pillsWrap = wrap.querySelector('.spw-pills');

                            var img = new Image();
                            img.alt = 'Personalización';
                            img.loading = 'lazy';
                            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc';
                            img.src = lastPng;
                            imgsWrap.insertBefore(img, imgsWrap.firstChild);

                            if (lastColor) {
                                var pill = document.createElement('span');
                                pill.title = lastColor;
                                pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block;background:' + lastColor;
                                pillsWrap.insertBefore(pill, pillsWrap.firstChild);
                            }
                            break;
                        }
                    }
                }
            } catch (_) {}
            try {
                sessionStorage.removeItem('spw_last_line_id');
                sessionStorage.removeItem('spw_last_png');
                sessionStorage.removeItem('spw_last_color');
            } catch (_) {}
        }
    }

    function observeMutations() {
        var root = document.querySelector('.js_cart_lines, .o_wsale_cart, main') || document.body;
        if (!('MutationObserver' in window)) return;
        new MutationObserver(function () {
            try { initialInject(); } catch (e) { console.error('[SPW]', e); }
        }).observe(root, { childList: true, subtree: true });
    }

    function boot() {
        // Solo en carrito
        if (!/\/shop\/cart/.test(window.location.pathname)) return;
        initialInject();
        observeMutations();
        // Nav guard rápido (no intrusivo)
        try {
            document.body.classList.remove('o_header_overlay', 'o_header_fade_out', 'o_header_fadeout');
        } catch (_) {}
        console.log('[SPW] injector listo');
    }

    onReady(boot);
});