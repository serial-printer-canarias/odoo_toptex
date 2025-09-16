odoo.define('serial_printer_custom_wizard.spw', [], function (require) {
    'use strict';

    // --- Polyfill web.ajax (arregla: "modules needed... web.ajax") ---
    try {
        // Si ya existe, esto lanzaría; por eso el try/catch evita redefinir.
        odoo.define('web.ajax', function () {
            async function jsonRpc(url, method, params) {
                const payload = { jsonrpc: '2.0', method: method || 'call', params: params || {}, id: Date.now() };
                const resp = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    credentials: 'include',
                });
                const data = await resp.json();
                if (data.error) throw new Error(data.error.data?.message || data.error.message || 'RPC Error');
                return data.result;
            }
            async function post(url, data) {
                const fd = new FormData();
                Object.entries(data || {}).forEach(([k, v]) => fd.append(k, v));
                const resp = await fetch(url, { method: 'POST', body: fd, credentials: 'include' });
                return resp.text();
            }
            return { jsonRpc, post };
        });
    } catch (e) { /* ya definido en core */ }

    // --- Pintar preview PNG en carrito usando sessionStorage ---
    function injectCartPreview() {
        const dataUrl = sessionStorage.getItem('spw_last_png');
        if (!dataUrl) return;

        // Busca un contenedor razonable según el tema
        const spots = [
            '.js_cart_lines .td-product_name',
            '.js_cart_lines .css_description',
            '.oe_cart .td-product_name',
            '.oe_cart',
        ];
        let container = null;
        for (const sel of spots) {
            const el = document.querySelector(sel);
            if (el) { container = el; break; }
        }
        if (!container) return;
        if (container.querySelector('.spw-cart-preview')) return;

        const img = document.createElement('img');
        img.src = dataUrl;
        img.className = 'spw-cart-preview';
        img.style.maxWidth = '180px';
        img.style.border = '1px solid #eee';
        img.style.marginTop = '8px';
        container.appendChild(img);
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (/\/shop\/cart/.test(window.location.pathname)) {
            injectCartPreview();
            // Por si el carrito se renderiza después (Ajax)
            const mo = new MutationObserver(() => injectCartPreview());
            mo.observe(document.body, { childList: true, subtree: true });
        }
    });
});
