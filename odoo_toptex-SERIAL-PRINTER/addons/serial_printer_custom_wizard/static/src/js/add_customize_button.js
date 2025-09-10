/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

export class SpwCustomizeButton extends publicWidget.Widget {
    selector = ".oe_website_sale, .o_wsale_product_page";

    start() {
        this._insertButton();
        this._observer = new MutationObserver(() => this._insertButton());
        this._observer.observe(this.el, { childList: true, subtree: true });
        return super.start();
    }

    _insertButton() {
        if (this.el.querySelector("#spw_customize_btn")) return;

        const prodInput = this.el.querySelector('input[name="product_id"]');
        if (!prodInput || !prodInput.value) return;

        const addBtn = this.el.querySelector("button[name='add_to_cart']");
        if (!addBtn) return;

        const html = `
          <a id="spw_customize_btn"
             class="btn btn-outline-primary ms-2"
             href="/personalizar/${prodInput.value}">
            <i class="fa fa-magic me-1"></i><span>Personalizar</span>
          </a>`;
        addBtn.insertAdjacentHTML("afterend", html);
    }
}
publicWidget.registry.SpwCustomizeButton = SpwCustomizeButton;