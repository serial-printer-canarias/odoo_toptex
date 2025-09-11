/** serial_printer_custom_wizard/static/src/js/add_customize_button.js **/
odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
    'use strict';
    const publicWidget = require('web.public.widget');

    publicWidget.registry.SPWAddCustomizeButton = publicWidget.Widget.extend({
        selector: 'body',
        start() {
            // Solo en página de producto (no en /shop) y fuera del editor
            const isEditor = document.body.classList.contains('o_is_editable');
            const productDetails = document.querySelector('#product_details');
            if (!isEditor && productDetails) {
                const addToCart = productDetails.querySelector('.o_add_to_cart, form[action*="/shop/cart/update"] button[type="submit"]');
                if (addToCart && !document.getElementById('spw_customize_btn')) {
                    const tmplId = this._getTemplateId(productDetails);
                    const variantId = this._getVariantId(productDetails);
                    if (tmplId) {
                        const btn = document.createElement('a');
                        btn.id = 'spw_customize_btn';
                        btn.className = 'btn btn-outline-primary ms-2';
                        btn.href = `/personalizar/${tmplId}` + (variantId ? `?variant_id=${variantId}` : '');
                        btn.textContent = 'Personalizar';
                        addToCart.parentElement.appendChild(btn);
                    }
                }
            }
            return this._super(...arguments);
        },
        _getTemplateId(root) {
            // Odoo suele incluirlo como data-product-template-id o meta
            const el = root.querySelector('[data-product-template-id]');
            if (el) return el.getAttribute('data-product-template-id');
            const meta = document.querySelector('meta[name="product-template-id"]');
            return meta ? meta.content : '';
        },
        _getVariantId(root) {
            // El input usado para el add to cart suele ser product_id (variant)
            const inp = root.querySelector('input.product_id, input[name="product_id"]');
            return inp ? inp.value : '';
        },
    });

    return publicWidget.registry.SPWAddCustomizeButton;
});