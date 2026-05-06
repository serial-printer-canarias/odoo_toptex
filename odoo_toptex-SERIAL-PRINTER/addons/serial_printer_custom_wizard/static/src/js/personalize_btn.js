<odoo>
  <template id="spw_personalize_btn" inherit_id="website_sale.product">
    <!-- Dentro del form que contiene el input hidden product_id -->
    <xpath expr="//form[.//input[@name='product_id']]" position="inside">
      <div class="mt-2">
        <button type="button" id="spw_personalize_btn" class="btn btn-primary w-100">
          <i class="fa fa-magic me-1"/> <span>Personalizar</span>
        </button>
      </div>
    </xpath>

    <!-- Script mínimo: toma la variante seleccionada y redirige -->
    <xpath expr="//form[.//input[@name='product_id']]" position="after">
      <script type="text/javascript">
        (function () {
          document.addEventListener('click', function(ev){
            var btn = ev.target.closest && ev.target.closest('#spw_personalize_btn');
            if(!btn) return;
            var form = btn.closest('form');
            if(!form) return;
            var ip = form.querySelector('input[name="product_id"]');
            var variantId = ip && ip.value;
            if (variantId) {
              window.location.href = '/spw/customize/' + variantId;
            }
          }, true);
        })();
      </script>
    </xpath>
  </template>
</odoo>