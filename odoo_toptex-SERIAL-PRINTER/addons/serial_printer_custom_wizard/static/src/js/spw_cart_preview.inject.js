odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';
    const ts = () => Date.now();

    function onReady(cb){ document.readyState==='loading' ? document.addEventListener('DOMContentLoaded', cb, {once:true}) : cb(); }
    function addQuery(url, params){ const u=new URL(url, window.location.origin); Object.entries(params||{}).forEach(([k,v])=>u.searchParams.set(k,v)); return u.pathname+(u.search||''); }

    function getLineId(lineEl){
        const c = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return (c && (c.getAttribute?.('data-line-id') || c.getAttribute?.('data-id') || c.value)) || null;
    }

    function parsePersonalizations(text){
        if (!text) return [];
        const out = [];
        const re = /Color\s*SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g; // toma #RRGGBB
        let m, i = 0;
        while((m = re.exec(text))) out.push({ idx: i++, hex: m[1] });
        return out.length ? out : [{ idx: 0, hex: null }];
    }

    function candidates(lineId, idx){
        const n = idx+1, base = `/spw/line_preview/${lineId}`;
        const exts = ['png','webp','jpg','jpeg'];
        const bases = [`${base}-${n}`, `${base}/${n}`, `${base}_${n}`];
        const urls = [];
        for (const b of bases) for (const ext of exts) urls.push(addQuery(`${b}.${ext}`, { v: ts() }));
        for (const ext of exts) urls.push(addQuery(`${base}.${ext}`, { i: n, v: ts() }));
        urls.push(addQuery(base, { i: n, v: ts() }));
        for (const ext of exts) urls.push(addQuery(`${base}.${ext}`, { i: n, fb: 1, v: ts() }));
        return [...new Set(urls)];
    }

    function ensureWrap(info){
        let wrap = info.querySelector('.spw-cart-preview');
        if (!wrap){
            wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'display:flex;gap:12px;flex-wrap:wrap;margin-top:8px';
            info.appendChild(wrap);
        }
        return wrap;
    }

    function tryLoad(img, list){
        let k = 0;
        function next(){
            if (k >= list.length){ img.remove(); return; }
            const url = list[k++]; img.onerror = next; img.onload = null; img.src = url;
        }
        next();
    }

    function renderLine(lineEl){
        const info = lineEl.querySelector(INFO_SEL) || lineEl;
        const lineId = getLineId(lineEl);
        if (!info || !lineId) return;

        const wrap = ensureWrap(info);
        wrap.innerHTML = ''; // refresco limpio

        const persos = parsePersonalizations(info.textContent || '');
        persos.forEach(({ idx, hex }) => {
            const card = document.createElement('div');
            card.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:4px';

            const img = new Image();
            img.alt = 'Personalización';
            img.loading = 'lazy';
            img.style.cssText = 'width:120px;max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px;background:#fff';
            card.appendChild(img);

            const cap = document.createElement('div');
            cap.style.cssText = 'display:flex;align-items:center;gap:6px;font-size:12px;color:#6b7280';
            const pill = document.createElement('span');
            pill.style.cssText = 'width:12px;height:12px;border-radius:9999px;border:1px solid rgba(0,0,0,.15);display:inline-block;background:'+(hex||'transparent');
            cap.appendChild(pill);
            const txt = document.createElement('span');
            txt.textContent = hex || '—';
            cap.appendChild(txt);
            card.appendChild(cap);

            wrap.appendChild(card);
            tryLoad(img, candidates(lineId, idx));
        });
    }

    function boot(){
        const root = document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines');
        if (!root) return;
        document.querySelectorAll(LINE_SEL).forEach(renderLine);
        new MutationObserver(ms => {
            for (const m of ms){
                m.addedNodes && m.addedNodes.forEach(n => {
                    if (n instanceof HTMLElement){
                        if (n.matches?.(LINE_SEL)) renderLine(n);
                        else n.querySelectorAll?.(LINE_SEL).forEach(renderLine);
                    }
                });
            }
        }).observe(root, { childList:true, subtree:true });
        console.log('[SPW] previews del carrito listos');
    }

    onReady(boot);
});