/** SPW - Cart preview injector (imagenes + pildoras) - ES5 safe */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- READY (sin dependencias) ----------
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
    var LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    var INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    // ---------- UTILS ----------
    function ts() { return (new Date()).getTime(); }

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

    function urlLineId() {
        var m = window.location.search.match(/[?&]spw_line_id=(\d+)/);
        return m ? m[1] : null;
    }

    function getLineId(lineEl) {
        if (!lineEl) return urlLineId();
        var c = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return (c && (c.getAttribute && (c.getAttribute('data-line-id') || c.getAttribute('data-id')) || c.value)) || urlLineId() || null;
    }

    function parsePersonalizations(text) {
        if (!text) return [];
        var out = [];
        var re = /SVG\s*:\s*#([0-9a-fA-F]{3,8})/g;
        var m, i = 0;
        while ((m = re.exec(text))) {
            out.push({ idx: i++, hex: '#' + m[1] });
        }
        return out.length ? out : [{ idx: 0, hex: null }];
    }

    function buildUrlCandidates(lineId, idx) {
        var n = idx + 1;
        var base = '/spw/line_preview/' + lineId;
        var exts = ['png', 'webp', 'jpg', 'jpeg'];
        var indexedBases = [ base + '-' + n, base + '/' + n, base + '_' + n ];
        var urls = [];
        var i, j;

        // indexados con extension
        for (i = 0; i < indexedBases.length; i++) {
            for (j = 0; j < exts.length; j++) {
                urls.push(addQuery(indexedBases[i] + '.' + exts[j], { v: ts() }));
            }
        }
        // ?i=n con y sin extension
        for (j = 0; j < exts.length; j++) {
            urls.push(addQuery(base + '.' + exts[j], { i: n, v: ts() }));
        }
        urls.push(addQuery(base, { i: n, v: ts() }));

        // fallback unico por indice (no colisiona con otros indices)
        for (j = 0; j < exts.length; j++) {
            urls.push(addQuery(base + '.' + exts[j], { i: n, fb: 1, v: ts() }));
        }

        // dedup
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

    function renderLine(lineEl) {
        var info = lineEl.querySelector(INFO_SEL) || lineEl;
        if (!info) return;

        var lineId = getLineId(lineEl);
        if (!lineId) return;

        var wrap = ensureWrap(info);
        var imgsWrap = wrap.querySelector('.spw-imgs');
        var pillsWrap = wrap.querySelector('.spw-pills');

        // limpiar y volver a pintar (evita duplicados al cambiar cantidades/AJAX)
        imgsWrap.innerHTML = '';
        pillsWrap.innerHTML = '';

        var persos = parsePersonalizations(info.textContent || '');

        for (var p = 0; p < persos.length; p++) {
            var hex = persos[p].hex;
            var idx = persos[p].idx;

            // pildora vertical
            var pill = document.createElement('span');
            pill.title = hex || '-';
            pill.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block';
            if (hex) pill.style.background = hex;
            pillsWrap.appendChild(pill);

            // imagen por indice
            var img = new Image();
            img.alt = 'Personalizacion';
            img.loading = 'lazy';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            imgsWrap.appendChild(img);

            var candidates = buildUrlCandidates(lineId, idx);
            tryLoad(img, candidates);
        }
    }

    function initialInject() {
        var nodes = document.querySelectorAll(LINE_SEL);
        for (var i = 0; i < nodes.length; i++) renderLine(nodes[i]);
    }

    function observeMutations() {
        var root = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
        new MutationObserver(function (ms) {
            for (var i = 0; i < ms.length; i++) {
                var m = ms[i];
                if (!m.addedNodes) continue;
                for (var j = 0; j < m.addedNodes.length; j++) {
                    var n = m.addedNodes[j];
                    if (!(n && n.nodeType === 1)) continue;
                    if (n.matches && n.matches(LINE_SEL)) renderLine(n);
                    else if (n.querySelectorAll) {
                        var list = n.querySelectorAll(LINE_SEL);
                        for (var k = 0; k < list.length; k++) renderLine(list[k]);
                    }
                }
            }
        }).observe(root, { childList: true, subtree: true });
    }

    function boot() {
        // Solo en carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector listo (multi-foto por linea; ES5 safe)');
    }

    onReady(boot);
});