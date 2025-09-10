/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";

export class SpwCustomizerPreview extends publicWidget.Widget {
  selector = "#spw-customizer";

  start() {
    this.base = this.el.querySelector("#spw-base");
    this.logo = this.el.querySelector("#spw-logo");
    this.scale = this.el.querySelector("#spw-scale");
    this.form = this.el.querySelector("#spw-form");
    this.overlayJson = this.el.querySelector("#spw-overlay-json");

    // Carga del logo
    this.el.querySelector("#spw-logo-input").addEventListener("change", (ev) => {
      const file = ev.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        this.logo.src = reader.result;
        this.logo.classList.remove("d-none");
      };
      reader.readAsDataURL(file);
    });

    // Drag simple
    let dragging = false, offX = 0, offY = 0;
    this.logo.addEventListener("mousedown", (e) => {
      dragging = true; this.logo.classList.add("dragging");
      const rect = this.logo.getBoundingClientRect();
      offX = e.clientX - rect.left; offY = e.clientY - rect.top;
      e.preventDefault();
    });
    document.addEventListener("mouseup", () => { dragging = false; this.logo.classList.remove("dragging"); });
    document.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const box = this.base.getBoundingClientRect();
      const x = e.clientX - box.left - offX;
      const y = e.clientY - box.top - offY;
      this.logo.style.left = `${(x / box.width) * 100}%`;
      this.logo.style.top  = `${(y / box.height) * 100}%`;
      this.logo.style.transform = "translate(0, 0)";
    });

    // Escala
    this.scale.addEventListener("input", () => {
      this.logo.style.width = `${this.scale.value}%`;
      this.logo.style.height = "auto";
    });

    // Envío
    this.form.addEventListener("submit", (e) => this._submit(e));
    return super.start();
  }

  _submit(e) {
    e.preventDefault();

    // Guardamos overlay relativo a la imagen base
    const box = this.base.getBoundingClientRect();
    const logoBox = this.logo.getBoundingClientRect();
    const overlay = {
      left: (logoBox.left - box.left) / box.width,
      top:  (logoBox.top  - box.top)  / box.height,
      width: logoBox.width / box.width,
      scale: Number(this.scale.value) / 100,
    };
    this.overlayJson.value = JSON.stringify(overlay);

    const fd = new FormData(this.form);
    fetch("/spw/customize/add_to_cart", { method: "POST", body: fd })
      .then(r => r.json())
      .then(data => {
        if (data.ok) window.location.href = "/shop/cart";
        else alert(data.error || "No se pudo añadir al carrito.");
      })
      .catch(() => alert("Error de red."));
  }
}
publicWidget.registry.SpwCustomizerPreview = SpwCustomizerPreview;