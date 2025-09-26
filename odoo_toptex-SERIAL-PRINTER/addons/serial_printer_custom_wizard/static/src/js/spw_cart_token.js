/** SPW – Forzar líneas independientes en carrito (token por personalización) */
odoo.define('serial_printer_custom_wizard.spw_cart_token', function (require) {
    'use strict';

    var ajax = require('web.ajax');

    function uid() {
        // token corto pero único suficiente para separar líneas
        return 'spw_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-6);
    }

    // Detecta si estamos en contexto del wizard (ajusta el selector si usas otro)
    function inWizardContext() {
        return !!document.querySelector('.spw-wizard, [data-spw-wizard="1"]');
    }

    // Parchea jsonRpc para añadir spw_token cuando se llama a /shop/cart/update_json
    var _jsonRpc = ajax.jsonRpc;
    ajax.jsonRpc = function (url, method, params) {
        try {
            if (url && url.indexOf('/shop/cart/update_json') !== -1 && inWizardContext()) {
                params = params || {};
                // Sólo si no viene ya uno del backend
                if (!params.spw_token) {
                    params.spw_token = uid();
                }
                // IMPORTANTÍSIMO: NO pasar line_id para no actualizar una línea existente
                if ('line_id' in params) {
                    delete params.line_id;
                }
            }
        } catch (e) {
            console.warn('[SPW] token inject warn:', e);
        }
        return _jsonRpc.call(this, url, method, params);
    };

    console.log('[SPW] cart_token listo (líneas separadas por spw_token)');
});