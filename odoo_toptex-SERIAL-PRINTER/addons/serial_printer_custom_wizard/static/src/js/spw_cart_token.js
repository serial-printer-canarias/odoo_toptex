/** SPW – Forzar líneas independientes en carrito (token por personalización) */
odoo.define('serial_printer_custom_wizard/js/spw_cart_token', function (require) {
    'use strict';

    var ajax = require('web.ajax');

    function uid() {
        return 'spw_' + Math.random().toString(36).slice(2, 10) + '_' + Date.now().toString(36);
    }

    // Detección del contexto del wizard (más tolerante)
    function inWizardContext() {
        if (document.querySelector('.spw-wizard,[data-spw-wizard="1"],form[action*="/spw/"]')) return true;
        var href = window.location.href;
        return /\/spw\/|[\?&]spw=1/.test(href);
    }

    // Parcheamos jsonRpc sólo para /shop/cart/update_json cuando estamos en el wizard
    var _jsonRpc = ajax.jsonRpc;
    ajax.jsonRpc = function (url, method, params) {
        try {
            if (url && url.indexOf('/shop/cart/update_json') !== -1 && inWizardContext()) {
                params = params || {};
                if (!params.spw_token) params.spw_token = uid();
                // clave: no actualizar una línea existente ⇒ obligamos a crear línea nueva
                if ('line_id' in params) delete params.line_id;
            }
        } catch (e) {
            console.warn('[SPW] token inject warn:', e);
        }
        return _jsonRpc.call(this, url, method, params);
    };

    console.log('[SPW] cart_token activo (líneas separadas por spw_token)');
});