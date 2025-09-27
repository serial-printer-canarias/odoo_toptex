/** SPW - Cart preview injector (foto + píldoras en vertical, ES5 seguro) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    // ---------- READY ----------
    function onReady(cb){
        if(document.readyState === 'loading'){
            document.addEventListener('DOMContentLoaded', function once(){
                document.removeEventListener('DOMContentLoaded', once);
                try{ cb(); }catch(e){ console.error('[SPW]', e); }
            });
        } else {
            try{ cb(); }catch(e){ console.error('[SPW]', e); }
        }
    }

    // ---------- SELECTORES ----------
    var LINE_SEL = 'tr.js_cart_line, .o_wsale_cart_item, .card.js_cart_item, .o_cart_line, .o_cart_product';
    var INFO_SEL = '.o_wsale_product_information, .o_cart_product_info, td.o_wsale_cart_description, .media-body, .oe_subdescription';

    // ---------- UTILS ----------
    function ts(){ return (new Date()).getTime(); }
    function urlParam(name){ try{ return new URL(location.href).searchParams.get(name); }catch(_){ return null; } }

    function getLineId(lineEl){
        if(!lineEl) return null;
        var c = lineEl.getAttribute('data-line-id') ? lineEl :
            (lineEl.querySelector && (lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]')));
        var v = (c && (c.getAttribute && (c.getAttribute('data-line-id') || c.getAttribute('data-id')) || c.value)) || null;
        return v && String(v);
    }

    function parseHexes(text){
        if(!text) return [];
        var out = [], re = /#([0-9a-fA-F]{6})\b/g, m;
        while((m = re.exec(text))) out.push('#' + m[1].toUpperCase());
        return out;
    }

    function ensureWrap(info, lineId){
        var wrap = info.querySelector('.spw-cart-preview[data-line="'+ lineId +'"]');
        if(!wrap){
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.setAttribute('data-line', lineId);
            wrap.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;flex-wrap:wrap';

            var imgs = document.createElement('div');
            imgs.className = 'spw-imgs';
            imgs.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start';

            var pills = document.createElement('div');
            pills.className = 'spw-pills';
            // <<< PÍLDORAS EN VERTICAL >>>
            pills.style.cssText = 'display:flex;flex-direction:column;gap:8px;align-items:center';

            wrap.appendChild(imgs);
            wrap.appendChild(pills);
            info.appendChild(wrap);
        }
        return wrap;
    }

    function pill(hex){
        var s = document.createElement('span');
        s.title = hex || '';
        s.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block;' + (hex ? ('background:'+hex) : '');
        return s;
    }

    function imgEl(src){
        var img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc';
        img.src = src;
        return img;
    }

    function renderLine(lineEl){
        var id = getLineId(lineEl);
        if(!id) return;

        var info = lineEl.querySelector(INFO_SEL) || lineEl;
        var wrap = ensureWrap(info, id);
        var imgs = wrap.querySelector('.spw-imgs');
        var pills = wrap.querySelector('.spw-pills');

        // limpiar (evita duplicados)
        imgs.innerHTML = '';
        pills.innerHTML = '';

        // 1) FOTO por línea (servida por el backend)
        var url = '/spw/line_preview/' + encodeURIComponent(id) + '.png?_=' + ts();
        var test = new Image();
        test.onload  = function(){ imgs.appendChild(imgEl(url)); };
        test.onerror = function(){
            // Fallback: si venimos del customizer y aún no se adjuntó en servidor
            try{
                var wanted  = urlParam('spw_line_id');
                var lastId  = sessionStorage.getItem('spw_last_line_id');
                var lastPng = sessionStorage.getItem('spw_last_png');
                if ((wanted && wanted === id) || (lastId && lastId === id)) {
                    if (lastPng) imgs.appendChild(imgEl(lastPng));
                }
            }catch(_){}
        };
        test.src = url;

        // 2) PÍLDORAS (todas las que aparezcan en el texto)
        var hexes = parseHexes(info.textContent || '');
        if (hexes.length === 0) { pills.appendChild(pill(null)); }
        for(var i=0;i<hexes.length;i++) pills.appendChild(pill(hexes[i]));
    }

    function inject(){
        if (!/\/shop\/cart/.test(location.pathname)) return;
        var lines = document.querySelectorAll(LINE_SEL);
        for(var i=0;i<lines.length;i++) renderLine(lines[i]);
    }

    function boot(){
        inject();
        var root = document.querySelector('.js_cart_lines, .o_wsale_cart, main') || document.body;
        if('MutationObserver' in window){
            var t;
            new MutationObserver(function(){ clearTimeout(t); t = setTimeout(inject, 120); })
                .observe(root, {childList:true, subtree:true});
        }
        setTimeout(inject, 400);
        setTimeout(inject, 1200);
    }

    onReady(boot);
});