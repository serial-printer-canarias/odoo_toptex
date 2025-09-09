/** @odoo-module **/
odoo.define('serial_printer_custom_wizard.personalizar_meta_patch', function (require) {
    'use strict';
    const domReady = require('web.dom_ready');

    domReady(function () {
        // Solo actuar en la página del personalizador
        const wrapper = document.getElementById('spw_wrapper');
        if (!wrapper) return;

        try {
            const prodId = parseInt(wrapper.getAttribute('data-product-id'), 10);
            if (!window.odoo) return;

            // Crear/forzar la estructura que usa el Website Editor
            const site = (odoo.__WOWL_WEBSITE__ = odoo.__WOWL_WEBSITE__ || {});
            site.metadata = site.metadata || {};
            site.metadata.mainObject = site.metadata.mainObject || {};

            if (!site.metadata.mainObject.model) {
                site.metadata.mainObject.model = 'product.template';
            }
            if (!site.metadata.mainObject.id && prodId) {
                site.metadata.mainObject.id = prodId;
            }
        } catch (e) {
            // Silencioso: no romper frontend por el editor
            // console.warn('SPW meta patch error', e);
        }
    });
});