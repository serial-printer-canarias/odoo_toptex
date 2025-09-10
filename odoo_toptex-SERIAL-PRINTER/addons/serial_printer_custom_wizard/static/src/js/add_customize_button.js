/** @odoo-module **/

// JS minimal y MUY robusto para volver a poner el botón y
// dejar un badge "SPW JS OK" que nos confirma que el asset cargó.

(function () {
    "use strict";

    // util: primer selector que exista
    function firstSelector(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    // extrae id del template desde la URL /shop/product/<slug>-<id>
    function getTemplateIdFromUrl() {
        const m = window.location.pathname.match(/\/shop\/product\/.*-(\d+)(?:$|\/)/);
        return m ? m[1] : null;
    }

    function injectBadge() {
        if (document.getElementById('spw_badge')) return;
        const b = document.createElement('div');
        b.id = 'spw_badge';
        b.textContent = 'SPW JS OK';
        b.style.position = 'fixed';
        b.style.right = '12px';
        b.style.bottom = '12px';
        b.style.zIndex = '2147483647';
        b.style.padding = '6px 10px';
        b.style.borderRadius = '8px';
        b.style.background = '#e6eefc';
        b.style.border = '1px solid #9db7ff';
        b.style.color = '#1d3a8a';
        b.style.font = '600 12px/1 system-ui, sans-serif';
        document.body.appendChild(b);
    }

    function addButton() {
        // Evitamos duplicados
        if (document.getElementById('spw_customize_btn')) return;

        // ¿Estamos en una ficha? Si no hay título/controles, salimos.
        const pid = getTemplateIdFromUrl();
        if (!pid) return;

        // contenedor típico (varía según tema, probamos varios)
        const container = firstSelector([
            '#product_details',                 // tema estándar
            '.o_wsale_product_information',     // otra variante
            '.o_wsale_product_page',            // otra
            '.product_main',                    // algunas plantillas
            '#wrap .container',                 // fallback
            '#wrap'
        ]);
        if (!container) return;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-secondary mt-3';
        btn.textContent = 'Personalizar';
        btn.href = `/spw/personalizar/${pid}`;
        // Lo insertamos después del botón de "Add to cart" si existe,
        // si no, al final del contenedor encontrado.
        const addToCart = firstSelector(['#add_to_cart', 'form[action*="/shop/cart/update"] button[type="submit"]']);
        if (addToCart && addToCart.parentElement) {
            addToCart.parentElement.insertAdjacentElement('afterend', btn);
        } else {
            container.appendChild(btn);
        }
    }

    function boot() {
        injectBadge();
        addButton();

        // Por si el DOM del tema se re-renderiza (cambio de variante, etc.)
        const mo = new MutationObserver(() => addButton());
        mo.observe(document.body, { childList: true, subtree: true });
        window.addEventListener('hashchange', addButton);
        document.addEventListener('shop_product_configurator_ready', addButton);
    }

    if (document.readyState !== 'loading') {
        boot();
    } else {
        document.addEventListener('DOMContentLoaded', boot);
    }
})();