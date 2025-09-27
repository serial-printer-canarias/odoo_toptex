/** SPW - Cart preview injector (simple y fiable) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';
    var DEBUG = true;

    function onReady(cb){
        if(document.readyState === 'loading'){
            document.addEventListener('DOMContentLoaded', function once(){
                document.removeEventListener('DOMContentLoaded', once);
                try{ cb(); }catch(e){ console.error('[SPW]', e); }
            });
        } else { try{ cb(); }catch(e){ console.error('[SPW]', e); } }
    }

    var LINE_SEL = 'tr.js_cart_line, .o_wsale_cart_item, .card.js_cart_item, .o_cart_line, .o_cart_product';
    var INFO_SEL = '.o_wsale_product_information, .o_cart_product_info, td.o_wsale_cart_description, .media-body, .oe_subdescription';

    function urlParam(name){ try{ return new URL(location.href).searchParams.get(name); }catch(_){ return null; } }
    function ts(){ return (new Date()).getTime(); }

    function getLineId(line){
        if(!line) return null;
        var c = line.getAttribute('data-line-id') ? line :
                (line.querySelector && (line.querySelector('[data-line-id]') ||
                                        line.querySelector('input[name="line_id"]') ||
                                        line.querySelector('button[data-line-id], a[data-line-id]')));
        var v = (c && (c.getAttribute && (c.getAttribute('data-line-id') || c.getAttribute('data-id')) || c.value)) || null;
        return v && String(v);
    }

    function infoContainer(line){
        return line.querySelector(INFO_SEL) || line;
    }

    function ensureWrap(info) {
        var wrap = info.querySelector('.spw-cart-preview');
        if (!wrap) {
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'display:flex;align-items:flex-start;gap:12px;margin-top:8px;flex-wrap:wrap';
            info.appendChild(wrap);
        }
        return wrap;
    }

    function putImg(wrap, src){
        var img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc';
        img.src = src;
        wrap.appendChild(img);
    }

    function renderLine(line){
        var id = getLineId(line);
        if(!id) return;

        var info = infoContainer(line);
        var wrap = ensureWrap(info);
        wrap.innerHTML = ''; // limpiar

        // 1) Servidor: /spw/line_preview/<line>.png
        var url = '/spw/line_preview/' + encodeURIComponent(id) + '.png?_=' + ts();
        var img = new Image();
        img.alt = 'Personalización';
        img.loading = 'lazy';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#f8fafc';
        img.onerror = function(){
            if(DEBUG) console.warn('[SPW][cart] preview 404 line', id, url);
            // 2) Fallback si venimos del customizer (sessionStorage)
            try{
                var wanted = urlParam('spw_line_id');
                var lastId = sessionStorage.getItem('spw_last_line_id');
                var lastPng = sessionStorage.getItem('spw_last_png');
                if(wanted && lastId === id && lastPng){
                    putImg(wrap, lastPng);
                    if(DEBUG) console.info('[SPW][cart] using sessionStorage PNG for line', id);
                }
            }catch(_){}
        };
        img.onload = function(){ if(DEBUG) console.debug('[SPW][cart] loaded', url); };
        img.src = url;
        wrap.appendChild(img);
    }

    function injectAll(){
        var lines = document.querySelectorAll(LINE_SEL);
        for(var i=0;i<lines.length;i++) renderLine(lines[i]);
    }

    function observe(){
        var root = document.querySelector('.js_cart_lines, .o_wsale_cart, main') || document.body;
        if(!('MutationObserver' in window)) return;
        new MutationObserver(function(){ injectAll(); }).observe(root, {childList:true, subtree:true});
    }

    function boot(){
        if(!/\/shop\/cart/.test(location.pathname)) return;
        if(DEBUG) console.info('[SPW][cart] injector boot');
        injectAll();
        observe();
        setTimeout(injectAll, 500);
        setTimeout(injectAll, 1200);
    }

    onReady(boot);
});