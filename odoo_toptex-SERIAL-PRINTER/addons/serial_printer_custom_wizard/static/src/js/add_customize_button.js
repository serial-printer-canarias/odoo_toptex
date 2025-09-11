/** SPW – Inserta botón PERSONALIZAR en la ficha y pasa la variante */
odoo.define('serial_printer_custom_wizard.add_customize_button', function (require) {
  'use strict';
  const publicWidget = require('web.public.widget');

  publicWidget.registry.SPWAddCustomizeButton = publicWidget.Widget.extend({
    selector: ".oe_website_sale",
    start() {
      this._insert();
      // Reinsertar si cambian los atributos/variante
      const mo = new MutationObserver(() => this._insert());
      mo.observe(this.el, { subtree: true, childList: true });
      return this._super(...arguments);
    },
    _insert() {
      if (this.el.querySelector('#spw_customize_btn')) return;

      const variantInput = this.el.querySelector('input[name="product_id"]'); // product.product id
      if (!variantInput) return;

      const tmplInput = this.el.querySelector('input[name="product_template_id"]');
      const tmplId = tmplInput ? tmplInput.value : this.el.dataset.productTemplateId;
      if (!tmplId) return;

      const btns = this.el.querySelector('.o_wsale_product_buttons, .o_wsale_product_btns');
      if (!btns) return;

      const a = document.createElement('a');
      a.id = 'spw_customize_btn';
      a.className = 'btn btn-outline-primary ms-2';
      a.href = `/personalizar/${tmplId}?variant_id=${variantInput.value}`;
      a.innerHTML = `<i class="fa fa-magic me-1"></i><span>Personalizar</span>`;
      btns.appendChild(a);
    },
  });
});