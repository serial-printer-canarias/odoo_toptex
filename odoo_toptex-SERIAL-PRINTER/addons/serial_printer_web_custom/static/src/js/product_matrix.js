/** Serial Printer – Matrix (Odoo 18) */
odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    /**
     * Nos anclamos al bloque estable de la página de producto.
     * (Evita depender de .o_wsale_product_page / #product_details, que pueden no existir según el tema.)
     */
    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '#oe_structure_website_sale_product',

        /**
         * Soportamos tus clases actuales y un prefijo propio por si las cambias:
         *  - Botón:  .add-to-cart-btn  o  .sp-add-to-cart
         *  - Contenedor: [data-sp-matrix], .sp-matrix, .border.rounded.p-3
         *  - Cantidades: .qty-input  o  .sp-qty-input  (con data-variant-id)
         */
        events: {
            'click .add-to-cart-btn': '_onAddToCart',
            'click .sp-add-to-cart':  '_onAddToCart',
        },

        /**
         * Recolecta líneas válidas (qty > 0 y variant id presente) dentro del ámbito dado.
         */
        _collectLines($scope) {
            const lines = [];
            $scope.find('.sp-qty-input, input.qty-input').each(function () {
                // Acepta "1,5" o "1.5"
                const raw = String(this.value || '').trim().replace(',', '.');
                const qty = parseFloat(raw);
                const product_id = parseInt(this.dataset.variantId || this.getAttribute('data-variant-id') || '0', 10);
                if (Number.isFinite(qty) && qty > 0 && product_id) {
                    lines.push({ product_id, qty });
                }
            });
            return lines;
        },

        /**
         * Click en "Añadir a carrito" del matrix.
         */
        _onAddToCart(ev) {
            ev.preventDefault();

            const $btn  = $(ev.currentTarget);
            const $card = $btn.closest('[data-sp-matrix], .sp-matrix, .border.rounded.p-3');
            const $scope = $card.length ? $card : this.$el;

            const lines = this._collectLines($scope);
            if (!lines.length) {
                // Nada que añadir: no hacemos ruido, simplemente salimos.
                return;
            }

            const calls = lines.map(({ product_id, qty }) =>
                ajax.jsonRpc('/shop/cart/update_json', 'call', {
                    product_id: product_id,
                    add_qty: qty,
                    display: false,
                })
            );

            Promise.all(calls)
                .then(() => {
                    // Lo más simple y seguro: refrescar para ver totales/stock actualizados.
                    window.location.reload();
                })
                .catch((err) => {
                    // Si algo falla, al menos no dejamos al usuario sin feedback.
                    // (En consola para debug; en producción el reload también suele recuperar estado.)
                    console.error('SerialPrinterMatrix error:', err);
                    window.location.reload();
                });
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});