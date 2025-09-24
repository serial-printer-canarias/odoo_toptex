/** SPW – Cart preview injector (blindado) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    function safe(fn) { try { fn(); } catch (e) { console.warn('[SPW] silenciado:', e); } }
    function onReady(cb){ if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',cb,{once:true});} else {cb();} }

    const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    function getLineId(lineEl){
        if(!lineEl) return null;
        const n = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return n ? (n.getAttribute?.('data-line-id') || n.getAttribute?.('data-id') || n.value || null) : null;
    }

    function parseColors(text){
        if(!text) return [];
        const out=[], re=/SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g; let m;
        while((m=re.exec(text))) { const hex=m[1].toUpperCase(); if(!out.includes(hex)) out.push(hex); }
        return out;
    }

    function parsePreviewsFromAttr(el){
        const raw = el.getAttribute('data-spw-previews') ||
                    el.closest(LINE_SEL)?.getAttribute('data-spw-previews') || '';
        if(!raw) return [];
        try { const arr = JSON.parse(raw); return Array.isArray(arr) ? arr.filter(Boolean) : []; }
        catch { return raw.split(',').map(s=>s.trim()).filter(Boolean); }
    }

    function alreadyInjected(root){ return !!root.querySelector('.spw-cart-preview'); }

    function candidateUrls(lineId){
        if(!lineId) return [];
        const b=`/spw/line_preview/${lineId}`;
        const e=['png','webp'];
        const suf=['','-1','-2','-3','-4','-5','-6','_1','_2','_3','_4','_5','_6','.1','.2','.3','.4','.5','.6'];
        const urls=[];
        e.forEach(ext=>urls.push(`${b}.${ext}`));
        suf.forEach(s=>e.forEach(ext=>urls.push(`${b}${s}.${ext}`)));
        return urls;
    }

    function addImageWhenExists(url, holder, seen){
        if(!url || seen.has(url)) return;
        const img = new Image();
        img.loading = 'lazy';
        img.alt = 'Personalización';
        img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
        img.onload = ()=>{ seen.add(url); holder.appendChild(img); };
        img.onerror = ()=>{};
        img.src = `${url}${url.includes('?')?'&':'?'}v=${Date.now()}`;
    }

    function injectInto(lineEl){
        safe(()=> {
            const info = lineEl.querySelector(INFO_SEL) || lineEl;
            if(!info || alreadyInjected(info)) return;

            const lineId = getLineId(lineEl);
            const colors = parseColors(info.textContent || '');

            const wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'margin-top:8px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap';

            const photos = document.createElement('div');
            photos.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;align-items:center';

            const pills = document.createElement('div');
            pills.style.cssText = 'display:flex;flex-direction:column;gap:6px;align-items:flex-start';

            // 1) urls desde data-spw-previews (si el backend las pone)
            let urls = parsePreviewsFromAttr(info);
            // 2) si no hay, probar variantes conocidas sin tocar backend
            if(!urls.length) urls = candidateUrls(lineId);

            const seen=new Set();
            urls.forEach(u=>addImageWhenExists(u, photos, seen));

            colors.forEach(hex=>{
                const pill=document.createElement('span');
                pill.title=hex;
                pill.style.cssText='display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
                pill.style.background=hex;
                pills.appendChild(pill);
            });

            if (photos.children.length || pills.children.length) {
                wrap.appendChild(photos);
                wrap.appendChild(pills);
                info.appendChild(wrap);
            }
        });
    }

    function initialInject(){ safe(()=> document.querySelectorAll(LINE_SEL).forEach(injectInto)); }

    function observeMutations(){
        safe(()=> {
            const target = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
            const mo = new MutationObserver((mutations)=>{
                for (const m of mutations) {
                    (m.addedNodes||[]).forEach(n=>{
                        if (!(n instanceof HTMLElement)) return;
                        if (n.matches?.(LINE_SEL)) injectInto(n);
                        else n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
                    });
                }
            });
            mo.observe(target,{childList:true,subtree:true});
        });
    }

    function boot(){
        // ¡Corta enseguida si no es carrito!
        if(!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        console.log('[SPW] injector activo (a prueba de fallos)');
    }

    onReady(boot);
});