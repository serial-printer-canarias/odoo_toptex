/** SPW - Cart preview (simple, rápido, sin loops pesados) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';
    var DEBUG = false;

    function ready(cb){
        if (document.readyState === 'loading'){
            document.addEventListener('DOMContentLoaded', function once(){
                document.removeEventListener('DOMContentLoaded', once);
                try{ cb(); }catch(e){ console.error('[SPW]', e); }
            });
        } else {
            try{ cb(); }catch(e){ console.error('[SPW]', e); }
        }
    }

    var LINE_SEL = 'tr.js_cart_line, .o_wsale_cart_item, .card.js_cart_item, .o_cart_line, .o_cart_product';
    var INFO_SEL = '.o_wsale_product_information, .o_cart_product_info, td.o_wsale_cart_description, .media-body, .oe_subdescription';

    function getLineId(line){
        if(!line) return null;
        var el = line.getAttribute('data-line-id') ? line :
                 (line.querySelector && (line.querySelector('[data-line-id]') ||
                                         line.querySelector('input[name="line_id"]') ||
                                         line.querySelector('button[data-line-id], a[data-line-id]')));
        var v = (el && (el.getAttribute && (el.getAttribute('data-line-id') || el.getAttribute('data-id')) || el.value)) || null;
        return v && String(v);
    }

    function container(line){
        return line.querySelector(INFO_SEL) || line;
    }

    function ensureWrap(info){
        var wrap = info.querySelector('.spw-cart-preview');
        if(!wrap){
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;flex-wrap:wrap';
            var imgs = document.createElement('div');
            imgs.className = 'spw-imgs';
            imgs.style.cssText = 'display:flex;gap:8px;flex-wrap:wrap;align-items:flex-start';
            var pills = document.createElement('div');
            pills.className = 'spw-pills';
            pills.style.cssText = 'display:flex;gap:6px;align-items:center';
            wrap.appendChild(imgs);
            wrap.appendChild(pills);
            info.appendChild(wrap);
        }
        return wrap;
    }

    function parseHexes(text){
        if(!text) return [];
        var out=[], re=/#([0-9a-fA-F]{6})\b/g, m;
        while((m=re.exec(text))) out.push('#'+m[1].toUpperCase());
        return out;
    }

    function putImg(dst, src){
        var img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc';
        img.src = src;
        dst.appendChild(img);
    }

    function putPill(dst, hex){
        var s = document.createElement('span');
        s.className = 'spw-pill';
        s.title = hex || '';
        s.style.cssText = 'width:14px;height:14px;border-radius:9999px;border:1px solid #e5e7eb;display:inline-block;' + (hex ? ('background:'+hex) : '');
        dst.appendChild(s);
    }

    function renderLine(line){
        var id = getLineId(line);
        if(!id) return;

        var info = container(line);
        var wrap = ensureWrap(info);
        var imgsWrap = wrap.querySelector('.spw-imgs');
        var pillsWrap = wrap.querySelector('.spw-pills');

        // Limpia y pinta
        imgsWrap.innerHTML = '';
        pillsWrap.innerHTML = '';

        // Imagen de servidor
        var url = '/spw/line_preview/' + encodeURIComponent(id) + '.png?_=' + Date.now();
        putImg(imgsWrap, url);

        // Píldoras (del texto de la línea)
        var hexes = parseHexes((info.textContent || ''));
        if (hexes.length){
            for (var i=0;i<hexes.length;i++) putPill(pillsWrap, hexes[i]);
        }
        if(DEBUG) console.log('[SPW-cart] line', id, 'hexes', hexes);
    }

    function inject(){
        if (!/\/shop\/cart/.test(location.pathname)) return;
        var lines = document.querySelectorAll(LINE_SEL);
        for (var i=0;i<lines.length;i++) renderLine(lines[i]);
    }

    function boot(){
        inject();
        // Observador muy ligero (sin loops): solo si cambia el contenedor de líneas
        var root = document.querySelector('.js_cart_lines, .o_wsale_cart, main');
        if (root && 'MutationObserver' in window){
            var t;
            new MutationObserver(function(){
                clearTimeout(t);
                t = setTimeout(inject, 120);
            }).observe(root, {childList:true, subtree:true});
        }
    }

    ready(boot);
});