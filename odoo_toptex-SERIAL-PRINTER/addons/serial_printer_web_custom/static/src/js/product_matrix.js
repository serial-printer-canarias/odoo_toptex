/** @odoo-module **/
import publicWidget from 'web.public.widget';
import ajax from 'web.ajax';

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// Espera a que cambie el product_id (cuando Odoo recalcula la combinación)
async function waitProductIdChange($root, oldId, timeout = 1500) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const cur = parseInt($root.find('input[name="product_id"]').val() || '0', 10);
        if (cur && cur !== oldId) return cur;
        await sleep(50);
    }
    return parseInt($root.find('input[name="product_id"]').val() || '0', 10);
}

publicWidget.registry.SerialPrinterMatrix = publicWidget.Widget.extend({
    selector: '.o_wsale_product_page',

    start() {
        // Construye matriz si hay al menos dos atributos (p.ej. Color y Talla)
        this.$root = this.$el;
        this._buildMatrix();
        return this._super(...arguments);
    },

    // Lee grupos de atributos de la ficha
    _getAttributeGroups() {
        const groups = [];
        this.$root.find('.css_attribute_color, .css_attribute').each(function () {
            const $g = $(this);
            // Título del grupo (Color/Talla/Size, etc.)
            const title = ($g.find('.attribute_name, label, .o_wsale_attr_label').first().text() || '').trim().toLowerCase();
            // Inputs de ese grupo
            const $inputs = $g.find('input[type="radio"].js_variant_change');
            if ($inputs.length) {
                groups.push({ $g, title, $inputs });
            }
        });
        return groups;
    },

    _buildMatrix() {
        const groups = this._getAttributeGroups();
        if (groups.length < 2) return; // nada que hacer

        // Elegimos: filas = tallas, columnas = el color actualmente seleccionado
        // Identificamos grupo de talla (name/label contiene 'talla'|'size'|'größe' etc.)
        const sizeIdx = groups.findIndex(g => /(talla|size|größe|taglia|maat|tamanho)/i.test(g.title));
        const colorIdx = groups.findIndex(g => /(color|colour|farbe|colore|kleur|cor)/i.test(g.title));
        // Fallback si no detecta nombres
        const rowGroup = sizeIdx >= 0 ? groups[sizeIdx] : groups[1];
        const colGroup = colorIdx >= 0 ? groups[colorIdx] : groups[0];

        // Contenedor bajo el botón "Add to cart"
        const $anchor = this.$root.find('form[action*="/shop/cart/update"] .o_wsale_cta_wrapper, form[action*="/shop/cart/update"]').last();
        if (!$anchor.length) return;

        const $box = $(`
            <div class="sp-matrix card rounded p-3 mt-3">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="fw-semibold">Pedido rápido por tallas</div>
                    <button class="btn btn-sm btn-primary sp-matrix-add">Añadir al carrito</button>
                </div>
                <div class="sp-matrix-grid"></div>
                <div class="text-muted small mt-2">Se añade para el <b>color seleccionado</b>.</div>
            </div>
        `);

        const $grid = $box.find('.sp-matrix-grid');

        // Renderiza lista de tallas con input de cantidad
        rowGroup.$inputs.each(function () {
            const $inp = $(this);
            const valId = parseInt($inp.val() || '0', 10);
            const label = ($inp.closest('label').text() || $inp.data('value_name') || '').trim() || $inp.attr('title') || `#${valId}`;
            const row = $(`
                <div class="sp-row d-flex align-items-center py-1">
                    <div class="sp-size badge me-2">${label}</div>
                    <input class="form-control form-control-sm sp-qty" type="number" min="0" step="1" value="0"
                           data-size-input-id="${valId}">
                </div>
            `);
            $grid.append(row);
        });

        // Click en “Añadir”
        $box.on('click', '.sp-matrix-add', async (ev) => {
            ev.preventDefault();
            const $rows = $box.find('.sp-qty');
            if (!$rows.length) return;

            // Color actual (no lo tocamos)
            const currentProductId = parseInt(this.$root.find('input[name="product_id"]').val() || '0', 10);

            // Recorremos tallas con qty > 0 y añadimos una por una para asegurar combinación correcta
            for (const el of $rows.toArray()) {
                const $qty = $(el);
                const qty = parseFloat($qty.val() || '0');
                if (qty <= 0) continue;

                // Selecciona la talla correspondiente (dispara recalculo de combinación)
                const sizeValId = $qty.data('size-input-id');
                const $sizeRadio = rowGroup.$inputs.filter((_, r) => parseInt(r.value || '0', 10) === sizeValId);
                if ($sizeRadio.length) {
                    // Guardamos id actual y forzamos el cambio
                    const before = parseInt(this.$root.find('input[name="product_id"]').val() || '0', 10);
                    $sizeRadio.prop('checked', true).change();
                    const variantId = await waitProductIdChange(this.$root, before);

                    if (variantId) {
                        await ajax.jsonRpc('/shop/cart/update_json', 'call', {
                            product_id: variantId,
                            add_qty: qty,
                            display: false,
                        });
                    }
                }
            }

            // Restaura la combinación original (por UX) si cambió
            if (currentProductId) {
                // Encuentra radios que llevan a ese product_id (opcional). Como es costoso, refrescamos.
                window.location.reload();
            } else {
                // Por si acaso
                window.location.reload();
            }
        });

        $anchor.after($box);
    },
});

export default publicWidget.registry.SerialPrinterMatrix;