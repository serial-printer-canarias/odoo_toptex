/** ************************************************************************
 *  Product Matrix (SERIAL PRINTER)
 *  - Construye una tabla Cantidades (color x talla) en la página de producto
 *  - Añade al carrito todas las cantidades introducidas
 *  - Detección robusta de bloques de atributos (funciona con plantillas nuevas)
 ************************************************************************* */

odoo.define('serial_printer_web_custom.product_matrix', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const ajax = require('web.ajax');

    // Utilidad sencilla
    function onReady(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
        selector: '.o_wsale_product_page',

        events: {
            // Interceptamos el "Add to cart" sólo si hay cantidades en la matriz
            'click form[action="/shop/cart/update"] .o_add_cart': '_onAddToCart',
            'click .js_add_cart_json': '_onAddToCart',
            'click button[name="add_to_cart"]': '_onAddToCart',
        },

        /**
         * Inicio del widget
         */
        start: function () {
            onReady(() => {
                try {
                    this._buildIfPossible();
                } catch (e) {
                    // Evitar romper la página si algo falla
                    console.error('[SP] Error al construir la matriz:', e);
                }
            });
            return this._super.apply(this, arguments);
        },

        // ===============================
        //  BLOQUES DE ATRIBUTOS (NUEVO)
        // ===============================

        /**
         * Detecta los bloques de atributos en diferentes plantillas/temas.
         * Devuelve un array de { name, options: [{id, name, $inp}], $el }
         */
        _getAttributeBlocks() {
            const blocks = [];

            // (1) Patrón clásico: contenedores con data-attribute_name
            this.$('.js_product .js_attributes [data-attribute_name]').each(function () {
                const $b = $(this);
                const name = ($b.attr('data-attribute_name') || '').trim();
                const options = $b.find('input[type="radio"]').map(function () {
                    const $inp = $(this);
                    const id = parseInt(
                        $inp.data('value_id') ||
                        $inp.data('attribute_value_id') ||
                        $inp.val(), 10
                    );
                    const label = ($inp.closest('label').text() || $inp.attr('title') || '').trim();
                    return id ? { id, name: label, $inp } : null;
                }).get();
                if (name && options.length) blocks.push({ name, options, $el: $b });
            });

            if (blocks.length) {
                return blocks;
            }

            // (2) Fallback: etiquetas con .o_variant_label y radios sueltos
            const $root = this.$('.js_product .js_attributes, .js_product .o_wsale_product_configurator').first();
            if ($root.length) {
                const groups = {};
                $root.find('label.o_variant_label').each(function () {
                    const $lbl = $(this);
                    const attrName = ($lbl.text() || $lbl.attr('title') || '').trim();
                    if (!attrName) return;
                    const $container = $lbl.parent();
                    const options = $container.find('input[type="radio"]').map(function () {
                        const $inp = $(this);
                        const id = parseInt(
                            $inp.data('value_id') ||
                            $inp.data('attribute_value_id') ||
                            $inp.val(), 10
                        );
                        const text = ($inp.closest('label').text() || $inp.attr('title') || '').trim();
                        return id ? { id, name: text, $inp } : null;
                    }).get();
                    if (options.length) {
                        if (!groups[attrName]) {
                            groups[attrName] = { name: attrName, options: [], $el: $container };
                        }
                        groups[attrName].options = groups[attrName].options.concat(options);
                    }
                });
                Object.values(groups).forEach(g => blocks.push(g));
            }

            return blocks;
        },

        /**
         * Localiza el grupo Color y el grupo Talla por nombre (con regex).
         */
        _pickColorAndSize(blocks) {
            const isColor = (n) => /^(color|colour|couleur)$/i.test((n || '').trim().toLowerCase());
            const isSize  = (n) => /^(talla|size|taille|talle)$/i.test((n || '').trim().toLowerCase());

            let color = blocks.find(b => isColor(b.name));
            let size  = blocks.find(b => isSize(b.name));

            // Fallback si no detecta por nombre
            if (!color || !size) {
                // Coge los dos primeros grupos con opciones
                const withOptions = blocks.filter(b => (b.options || []).length);
                if (withOptions.length >= 2) {
                    color = color || withOptions[0];
                    size  = size   || withOptions[1];
                }
            }
            return { color, size };
        },

        // ==========================================
        //  CONSTRUCCIÓN E INSERCIÓN (PUNTO NUEVO)
        // ==========================================

        /**
         * Construye la matriz si Color y Talla están presentes.
         * Inserta *después* del bloque de atributos (punto estable).
         */
        async _buildIfPossible() {
            const blocks = this._getAttributeBlocks();
            const { color, size } = this._pickColorAndSize(blocks);
            if (!color || !size) return; // no hacemos nada si falta algo

            // Marcamos que la matriz está activa (para ocultar radios originales)
            this.el.classList.add('sp-matrix-active');

            // Contenedor de montaje: tras los atributos; si no, tras el precio
            const $after = this.$('.js_product .js_attributes').last();
            const $mount = $('<div id="sp-matrix" class="sp-matrix o-pt-3"></div>');
            if ($after.length) {
                $after.after($mount);
            } else {
                this.$('.product_price').first().after($mount);
            }

            // Pintamos la tabla
            const $grid = this._renderGrid(color, size);
            $mount.empty().append($grid);
        },

        /**
         * Crea la tabla HTML y asigna eventos.
         */
        _renderGrid(colorBlock, sizeBlock) {
            // Orden amables: dejamos el orden como aparecen
            const colors = colorBlock.options;
            const sizes  = sizeBlock.options;

            // Tabla
            const $table = $(`
                <table class="sp-matrix__table table table-borderless">
                    <thead>
                        <tr>
                            <th class="sp-sticky-left"></th>
                            ${sizes.map(s => `<th><div class="text-center fw-medium">${_.escape(s.name)}</div></th>`).join('')}
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            `);

            // Cuerpo
            const $tbody = $table.find('tbody');
            colors.forEach(c => {
                const $row = $(`
                    <tr>
                        <th class="sp-sticky-left">
                            <div class="sp-color">
                                <div class="sp-color__img" aria-hidden="true"></div>
                                <div class="sp-color__name">${_.escape(c.name)}</div>
                            </div>
                        </th>
                        ${sizes.map(s => `
                            <td>
                                <div class="sp-cell">
                                    <input class="sp-qty form-control form-control-sm"
                                           type="number" min="0" step="1"
                                           inputmode="numeric"
                                           data-color-id="${c.id}"
                                           data-size-id="${s.id}"
                                           placeholder="0" />
                                    <div class="sp-meta">
                                        <span class="sp-price"></span>
                                        <span class="sp-stock"></span>
                                    </div>
                                </div>
                            </td>
                        `).join('')}
                    </tr>
                `);
                $tbody.append($row);
            });

            // Delegación de eventos: al introducir cantidad calculamos variant_id (lazy)
            const debounce = (fn, t=150) => {
                let h; return (...args) => { clearTimeout(h); h = setTimeout(() => fn.apply(this, args), t); };
            };
            $tbody.on('input', '.sp-qty', debounce((ev) => this._onQtyEdit(ev)));

            return $table;
        },

        // =========================
        //  VARIANT & RPC HELPERS
        // =========================

        /**
         * Cache de combinaciones → variant_id
         */
        _variantCache: null,

        _ensureCache() {
            if (!this._variantCache) this._variantCache = new Map();
            return this._variantCache;
        },

        /**
         * Obtiene el product_template_id desde el DOM (varios fallbacks).
         */
        _getTemplateId() {
            const $tpl = this.$('input[name="product_template_id"], input[name="product_tmpl_id"]');
            if ($tpl.length) {
                return parseInt($tpl.first().val(), 10) || 0;
            }
            const dataAttr = this.el.getAttribute('data-product-template-id');
            if (dataAttr) return parseInt(dataAttr, 10) || 0;
            // Último recurso: mirar en un contenedor con data-product-template-id
            const el = this.el.querySelector('[data-product-template-id]');
            return el ? parseInt(el.getAttribute('data-product-template-id'), 10) || 0 : 0;
        },

        /**
         * Llama a endpoint para resolver combination -> variant_id
         * Devuelve {variant_id, price, stock} en la medida de lo posible.
         */
        async _getCombinationInfo(colorId, sizeId) {
            const key = `${colorId}-${sizeId}`;
            const cache = this._ensureCache();
            if (cache.has(key)) return cache.get(key);

            const product_template_id = this._getTemplateId();
            const combination = [colorId, sizeId].filter(Boolean);

            let info = { variant_id: 0, price: null, stock: null };

            // Intento 1: /sale/get_combination_info (Odoo 15/16 eCommerce)
            try {
                const r1 = await ajax.jsonRpc('/sale/get_combination_info', 'call', {
                    product_template_id,
                    combination,
                    add_qty: 1,
                    pricelist_id: undefined,
                    parent_combination: [],
                    product_id: 0,
                    only_template: false,
                });
                if (r1 && r1.product_id) {
                    info.variant_id = parseInt(r1.product_id, 10) || 0;
                    if (r1.price) info.price = r1.price;
                    if (r1.qty_available !== undefined) info.stock = r1.qty_available;
                }
            } catch (e) {
                // silencioso
            }

            // Intento 2 (fallback): /shop/get_combination_info
            if (!info.variant_id) {
                try {
                    const r2 = await ajax.jsonRpc('/shop/get_combination_info', 'call', {
                        product_template_id,
                        combination,
                        add_qty: 1,
                        pricelist_id: undefined,
                        parent_combination: [],
                        product_id: 0,
                        only_template: false,
                    });
                    if (r2 && r2.product_id) {
                        info.variant_id = parseInt(r2.product_id, 10) || 0;
                        if (r2.price) info.price = r2.price;
                        if (r2.qty_available !== undefined) info.stock = r2.qty_available;
                    }
                } catch (e) {
                    // silencioso
                }
            }

            cache.set(key, info);
            return info;
        },

        /**
         * Handler al editar cantidad: resuelve variant y pinta meta (precio/stock).
         */
        async _onQtyEdit(ev) {
            const $inp = $(ev.currentTarget);
            const qty = parseFloat($inp.val() || '0');
            const colorId = parseInt($inp.data('color-id') || 0, 10);
            const sizeId  = parseInt($inp.data('size-id') || 0, 10);

            if (!qty) return; // nada que hacer

            const info = await this._getCombinationInfo(colorId, sizeId);
            if (info && info.variant_id) {
                // guardamos en dataset para Add to Cart
                $inp.data('variant-id', info.variant_id);
                // meta visual (si hay)
                const $cell = $inp.closest('.sp-cell');
                if (info.price != null) {
                    $cell.find('.sp-price').text(this._fmtPrice(info.price));
                }
                if (info.stock != null) {
                    $cell.find('.sp-stock').text(` · Stock: ${info.stock}`);
                }
            } else {
                // no existe variante (combinación no válida)
                $inp.closest('td').addClass('sp-unavailable');
            }
        },

        _fmtPrice(p) {
            // Formateo básico como fallback (Odoo ya formatea en servidor)
            const n = Number(p);
            if (isNaN(n)) return '';
            return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(n);
        },

        // =========================
        //  AÑADIR AL CARRITO
        // =========================

        /**
         * Intercepta Add to cart si hay cantidades en la matriz.
         */
        async _onAddToCart(ev) {
            const $matrix = this.$('#sp-matrix');
            if (!$matrix.length) return; // no hay matriz → dejar flujo normal

            const $qtys = $matrix.find('.sp-qty');
            const entries = [];
            // Recopila cantidades > 0
            $qtys.each((_, el) => {
                const $q = $(el);
                const qty = parseFloat($q.val() || '0');
                if (!qty) return;
                const colorId = parseInt($q.data('color-id') || 0, 10);
                const sizeId  = parseInt($q.data('size-id') || 0, 10);
                entries.push({ $q, qty, colorId, sizeId });
            });

            if (!entries.length) return; // dejar flujo normal (un único add-to-cart)

            ev.preventDefault();
            ev.stopPropagation();

            // Para cada entrada, asegurar variant_id (lazy)
            for (const e of entries) {
                const cached = e.$q.data('variant-id');
                if (cached) {
                    e.variant_id = parseInt(cached, 10);
                } else {
                    const info = await this._getCombinationInfo(e.colorId, e.sizeId);
                    e.variant_id = info.variant_id || 0;
                }
            }

            // Filtramos combinaciones sin variante (por seguridad)
            const valid = entries.filter(e => e.variant_id && e.qty > 0);

            if (!valid.length) {
                // Nada válido: dejamos que el botón haga lo de siempre
                return;
            }

            // Disparamos todas las llamadas de carrito
            const calls = valid.map(e =>
                ajax.jsonRpc('/shop/cart/update_json', 'call', {
                    product_id: e.variant_id,
                    add_qty: e.qty,
                    display: false,
                })
            );

            try {
                await Promise.all(calls);
                window.location.reload();
            } catch (e) {
                console.error('[SP] Error al añadir al carrito:', e);
            }
        },
    });

    return publicWidget.registry.SerialPrinterMatrix;
});