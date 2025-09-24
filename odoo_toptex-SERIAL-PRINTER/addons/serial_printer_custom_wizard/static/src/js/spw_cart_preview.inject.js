/** SPW – Cart preview injector (fotos múltiples + píldoras ordenadas, a prueba de fallos) */
odoo.define('serial_printer_custom_wizard.spw_cart_preview_inject', [], function () {
    'use strict';

    /* ---------- utilidades seguras ---------- */
    const DEBUG = false;
    function log(){ if (DEBUG) console.log.apply(console, arguments); }
    function safe(fn){ try { fn(); } catch(e){ console.warn('[SPW]', e); } }
    function onReady(cb){
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', cb, { once: true });
        } else { cb(); }
    }

    /* ---------- selectores ---------- */
    const LINE_SEL = '.o_cart_product, .js_cart_lines tr, .o_wsale_cart_item, .cart_line';
    const INFO_SEL = '.o_wsale_product_information, .o_wsale_cart_description, .o_wsale_cart_item_description, .product-name, .oe_subdescription';

    /* ---------- helpers ---------- */
    function getLineId(lineEl){
        if (!lineEl) return null;
        const n = lineEl.getAttribute('data-line-id') ? lineEl :
            lineEl.querySelector('[data-line-id]') ||
            lineEl.querySelector('input[name="line_id"]') ||
            lineEl.querySelector('button[data-line-id], a[data-line-id]');
        return n ? (n.getAttribute?.('data-line-id') || n.getAttribute?.('data-id') || n.value || null) : null;
    }

    // Devuelve TODOS los colores en el orden en que aparecen (sin deduplicar)
    function parseColorList(text){
        const out = [];
        if (!text) return out;
        const re = /SVG\s*:\s*(#[0-9a-fA-F]{3,8})/g;
        let m;
        while ((m = re.exec(text))) out.push(m[1].toUpperCase());
        return out;
    }

    // Permite que el backend nos entregue una lista de previews por data-attr (opcional)
    function previewsFromAttr(infoEl, lineEl){
        const raw = infoEl.getAttribute('data-spw-previews') ||
                    lineEl?.getAttribute('data-spw-previews') || '';
        if (!raw) return [];
        try {
            const arr = JSON.parse(raw);
            return Array.isArray(arr) ? arr.filter(Boolean) : [];
        } catch {
            return raw.split(',').map(s => s.trim()).filter(Boolean);
        }
    }

    function alreadyInjected(root){ return !!root.querySelector('.spw-cart-preview'); }

    // Para cada índice (1..N) generamos candidatos de URL
    function candidatesFor(lineId, idx /* 1-based */){
        const base = `/spw/line_preview/${lineId}`;
        const ext = ['png','webp'];
        const suffixes = idx
            ? [`-${idx}`, `_${idx}`, `.${idx}`]
            : ['']; // índice 0 => base
        const urls = [];
        suffixes.forEach(s => ext.forEach(e => urls.push(`${base}${s}.${e}`)));
        return urls;
    }

    // Carga la PRIMERA URL que exista de la lista y hace cb(img). Si ninguna existe, no hace nada.
    function loadFirstExisting(urls, cb){
        let i = 0;
        function next(){
            if (i >= urls.length) return;
            const u = urls[i++];
            const img = new Image();
            img.loading = 'lazy';
            img.alt = 'Personalización';
            img.style.cssText = 'max-width:120px;height:auto;border:1px solid #e5e7eb;border-radius:6px';
            img.onload = () => cb(img);
            img.onerror = () => next();
            // cache-bust para evitar que todas apunten al último render del servidor
            img.src = `${u}${u.includes('?') ? '&' : '?'}v=${Date.now()}`;
        }
        next();
    }

    /* ---------- inyección ---------- */
    function injectInto(lineEl){
        safe(() => {
            const info = lineEl.querySelector(INFO_SEL) || lineEl;
            if (!info || alreadyInjected(info)) return;

            const lineId = getLineId(lineEl);
            const colors = parseColorList(info.textContent || '');
            log('[SPW] cart line', { lineId, colors });

            const wrap = document.createElement('div');
            wrap.className = 'spw-cart-preview';
            wrap.style.cssText = 'margin-top:8px;display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap';

            const photos = document.createElement('div');
            photos.style.cssText = 'display:flex;gap:10px;flex-wrap:wrap;align-items:center';

            const pills = document.createElement('div');
            // vertical, una por línea, en el mismo orden
            pills.style.cssText = 'display:flex;flex-direction:column;gap:6px;align-items:flex-start';

            // 1) previews opcionales que el backend nos pase por atributo
            const attrUrls = previewsFromAttr(info, lineEl);
            attrUrls.forEach(u => loadFirstExisting([u], img => photos.appendChild(img)));

            // 2) previews por índice: uno por cada color detectado
            if (lineId) {
                colors.forEach((_, idx) => {
                    const urls = candidatesFor(lineId, idx + 1);  // -1, -2, …
                    loadFirstExisting(urls, img => photos.appendChild(img));
                });
                // 3) fallback: si no conseguimos ninguna imagen por índice, probamos la base
                loadFirstExisting(candidatesFor(lineId, 0), img => {
                    // solo añadir si aún no hay fotos
                    if (!photos.children.length) photos.appendChild(img);
                });
            }

            // píldoras (tantas como matches, sin deduplicar)
            colors.forEach(hex => {
                const pill = document.createElement('span');
                pill.title = hex;
                pill.style.cssText = 'display:inline-block;width:16px;height:16px;border-radius:9999px;border:1px solid #e5e7eb';
                pill.style.background = hex;
                pills.appendChild(pill);
            });

            if (photos.children.length || pills.children.length) {
                wrap.appendChild(photos);
                wrap.appendChild(pills);
                info.appendChild(wrap);
            }
        });
    }

    function initialInject(){ safe(() => document.querySelectorAll(LINE_SEL).forEach(injectInto)); }

    function observeMutations(){
        safe(() => {
            const target = document.querySelector('#o_cart, .o_wsale_products_main, .o_wsale_cart_summary, .js_cart_lines') || document.body;
            const mo = new MutationObserver(muts => {
                muts.forEach(m => (m.addedNodes || []).forEach(n => {
                    if (!(n instanceof HTMLElement)) return;
                    if (n.matches?.(LINE_SEL)) injectInto(n);
                    else n.querySelectorAll?.(LINE_SEL).forEach(injectInto);
                }));
            });
            mo.observe(target, { childList: true, subtree: true });
        });
    }

    function boot(){
        // Solo en carrito
        if (!document.querySelector('#o_cart, .o_wsale_cart_summary, .js_cart_lines')) return;
        initialInject();
        observeMutations();
        log('[SPW] injector listo');
    }

    onReady(boot);
});