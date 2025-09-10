odoo.define('serial_printer_custom_wizard.add_customize_button', function () {
    'use strict';

    function firstSelector(list) {
        for (var i = 0; i < list.length; i++) {
            var el = document.querySelector(list[i]);
            if (el) { return el; }
        }
        return null;
    }

    function getProductTemplateIdFromUrl() {
        // URLs de producto suelen terminar en ...-<id>
        var m = window.location.pathname.match(/-(\d+)(?:\/)?$/);
        return m ? m[1] : null;
    }

    function addButton() {
        var pid = getProductTemplateIdFromUrl();
        if (!pid) { return; }

        var container = firstSelector([
            '.o_wsale_product_information',
            '.o_wsale_product_page',
            '.product_main',
            '#wrap .container',
            '#wrap'
        ]);
        if (!container) { return; }

        if (document.getElementById('spw_customize_btn')) { return; }

        var btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.className = 'btn btn-outline-primary mt-3';
        btn.textContent = 'Personalizar';
        btn.href = '/spw/personalizar/' + pid;
        container.appendChild(btn);

        // Badge de verificación
        var badge = document.createElement('div');
        badge.textContent = 'SPW JS OK';
        badge.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:9999;padding:.35rem .5rem;border-radius:.25rem;background:#e9eefc;border:1px solid #cfe2ff;color:#1a56db;font-size:12px';
        document.body.appendChild(badge);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addButton);
    } else {
        addButton();
    }
});