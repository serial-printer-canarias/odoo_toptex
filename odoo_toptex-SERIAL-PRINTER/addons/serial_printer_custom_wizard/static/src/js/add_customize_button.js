odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';
    require('web.dom_ready');

    // --- Diagnóstico visual: pequeña píldora "SPW JS OK" ---
    (function spwBadge(){
        if (document.getElementById('spw_js_ok')) return;
        const b = document.createElement('div');
        b.id = 'spw_js_ok';
        b.textContent = 'SPW JS OK';
        Object.assign(b.style, {
            position:'fixed', right:'12px', bottom:'12px',
            padding:'6px 10px', background:'#e8eefc', border:'1px solid #c9d7ff',
            borderRadius:'6px', fontSize:'12px', zIndex: 9999
        });
        document.body.appendChild(b);
    })();

    function firstSelector(selectors) {
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el;
        }
        return null;
    }

    function getTemplateId() {
        // 1) url /shop/product/slug-305  ó /shop/product/305
        const m = location.pathname.match(/(?:-|\b)(\d+)(?:\/)?$/);
        if (m) return m[1];

        // 2) atributo de edición (cuando está en modo editor)
        const editNode = document.querySelector('[data-oe-model="product.template"][data-oe-id]');
        if (editNode) return editNode.getAttribute('data-oe-id');

        return null;
    }

    function ensureButton() {
        const pid = getTemplateId();
        if (!pid) return;

        // Dónde colocar el botón (al lado del Add to cart)
        const container = firstSelector([
            '.o_we_buy_now',                            // Odoo 16/17 estándar
            '.o_wsale_product_information',             // variación de tema
            '.o_wsale_product_page',                    // fallback
            'form[action*="/shop/cart/update"]',        // cerca del form de carrito
        ]);
        if (!container) return;

        if (document.getElementById('spw_customize_btn')) return; // no duplicar

        const btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.href = `/personalizar/${pid}`;
        btn.textContent = 'Personalizar';
        btn.className = 'btn btn-outline-secondary mt-3';

        // Si existe el contenedor del botón de carrito, lo dejamos justo detrás
        const cartBtn = container.querySelector('button[name="add_to_cart"], a[href*="cart"]');
        if (cartBtn && cartBtn.parentElement) {
            cartBtn.parentElement.appendChild(btn);
        } else {
            container.appendChild(btn);
        }
    }

    // Ejecutar de forma robusta (render tardío, cambios de variantes, etc.)
    let ticks = 0;
    const tryInterval = setInterval(function () {
        ticks += 1;
        try { ensureButton(); } catch (e) {}
        if (document.getElementById('spw_customize_btn') || ticks > 40) {
            clearInterval(tryInterval);
        }
    }, 250);

    // Además, observar cambios en DOM para reinsertar si la vista se recompone
    const obs = new MutationObserver(() => ensureButton());
    obs.observe(document.body, { childList: true, subtree: true });
});