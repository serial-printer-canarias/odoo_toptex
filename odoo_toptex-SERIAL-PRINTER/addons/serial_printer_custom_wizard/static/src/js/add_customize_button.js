/** @odoo-module **/
(function () {
    "use strict";

    function firstSelector(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }
    function getTemplateIdFromUrl() {
        const m = window.location.pathname.match(/\/shop\/product\/.*-(\d+)(?:$|\/)/);
        return m ? m[1] : null;
    }
    function injectBadge() {
        if (document.getElementById('spw_badge')) return;
        const b = document.createElement('div');
        b.id = 'spw_badge';
        b.textContent = 'SPW JS OK';
        b.style.cssText = 'position:fixed;right:12px;bottom:12px;z-index:2147483647;padding:6px 10px;border-radius:8px;background:#e6eefc;border:1px solid #9db7ff;color:#1d3a8a;font:600 12px/1 system-ui,sans-serif';
        document.body.appendChild(b);
    }
    function addButton() {
        if (document.getElementById('spw_customize_btn')) return;
        const pid = getTemplateIdFromUrl();
        if (!pid) return;

        const container = firstSelector([
            '#product_details',
            '.o_wsale_product_information',
            '.o_wsale_product_page',
            '.product_main',
            '#wrap .container',
            '#wrap'
        ]);
        if (!container) return;

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-secondary mt-3';
        btn.textContent = 'Personalizar';
        btn.href = `/spw/personalizar/${pid}`;

        const addToCart = firstSelector(['#add_to_cart','form[action*="/shop/cart/update"] button[type="submit"]']);
        if (addToCart && addToCart.parentElement) {
            addToCart.parentElement.insertAdjacentElement('afterend', btn);
        } else {
            container.appendChild(btn);
        }
    }
    function boot() {
        injectBadge();
        addButton();
        const mo = new MutationObserver(addButton);
        mo.observe(document.body, { childList: true, subtree: true });
        window.addEventListener('hashchange', addButton);
        document.addEventListener('shop_product_configurator_ready', addButton);
    }
    if (document.readyState !== 'loading') boot();
    else document.addEventListener('DOMContentLoaded', boot);
})();