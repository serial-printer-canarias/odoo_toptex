/** @odoo-module **/
odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    // Dev-badge para verificar que el JS se cargó
    function showBadge() {
        if (document.getElementById('spw-badge')) return;
        const b = document.createElement('div');
        b.id = 'spw-badge';
        b.textContent = 'SPW JS OK';
        b.style.cssText = 'position:fixed;right:12px;bottom:12px;padding:6px 10px;border-radius:6px;background:#e9eefc;color:#1b3a8f;font:600 12px/1.2 system-ui;z-index:9999;';
        document.body.appendChild(b);
    }

    function first(selArr, root=document) {
        for (const s of selArr) {
            const el = root.querySelector(s);
            if (el) return el;
        }
        return null;
    }

    function getTemplateId(root=document) {
        // inputs ocultos habituales
        let el = first(['input[name="product_id"]','input[name="product_template_id"]'], root);
        if (el && el.value) return el.value;
        // wrapper con data-oe-model
        const holder = root.querySelector('[data-oe-model="product.template"]');
        if (holder && holder.dataset.oeId) return holder.dataset.oeId;
        // /shop/product/<id> o /product/<id>
        const m = window.location.pathname.match(/(?:shop\/product|product)\/(\d+)/);
        return m ? m[1] : null;
    }

    function insertButton(root=document) {
        const buyBlock = first([
            '.o_wsale_product_form .o_wsale_product_btn',
            'form.o_wsale_product_form',
            'form[action*="/shop/cart/update"]',
            '#product_details',
            '.product_main',
            '#wrap .container'
        ], root);
        if (!buyBlock) return false;

        if (root.querySelector('.spw-btn-personalizar')) return true;

        const tmplId = getTemplateId(root);
        if (!tmplId) return false;

        const href = `/personalizar/${tmplId}?enable_editor=0`;

        const btn = document.createElement('a');
        btn.className = 'btn btn-outline-primary spw-btn-personalizar ms-2 mt-2';
        btn.href = href;
        btn.textContent = 'Personalizar';

        const addToCart = first([
            'button[name="add_to_cart"]',
            'a.js_add_cart_json',
            '.o_wsale_product_btn .btn.btn-primary'
        ], root);

        if (addToCart && addToCart.parentElement) {
            addToCart.parentElement.appendChild(btn);
        } else {
            buyBlock.appendChild(btn);
        }
        return true;
    }

    publicWidget.registry.SPWAddCustomizeBtn = publicWidget.Widget.extend({
        selector: 'body',
        start() {
            showBadge();
            // Reintenta porque el DOM del tema se hidrata poco a poco
            let tries = 0;
            const t = setInterval(() => {
                tries += 1;
                if (insertButton(document) || tries > 24) clearInterval(t);
            }, 250);

            // Y observa cambios dinámicos (por si el tema re-renderiza)
            const mo = new MutationObserver(() => insertButton(document));
            mo.observe(document.documentElement, {childList: true, subtree: true});
            return this._super(...arguments);
        },
    });
});