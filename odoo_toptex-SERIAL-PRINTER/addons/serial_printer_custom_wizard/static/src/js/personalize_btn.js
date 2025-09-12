/** serial_printer_custom_wizard/static/src/js/personalize_btn.js **/
odoo.define('serial_printer_custom_wizard.personalize_btn', function (require) {
    'use strict';

    var domReady = require('web.dom_ready');

    function goToCustomizer(btn) {
        var productId = btn.getAttribute('data-product-id') || (btn.dataset ? btn.dataset.productId : null);
        var variantInput = document.querySelector('form input[name="product_id"]');
        var variantId = variantInput ? variantInput.value : null;

        if (productId) {
            var url = '/spw/customize/' + productId + (variantId ? ('?variant_id=' + variantId) : '');
            window.location.href = url;
        }
    }

    domReady(function () {
        var btn = document.getElementById('spw_personalize_btn');
        if (!btn) { return; }
        btn.addEventListener('click', function (ev) {
            ev.preventDefault();
            goToCustomizer(btn);
        });
    });
});