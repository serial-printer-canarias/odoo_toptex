/** @odoo-module **/

class SPWPreview {
    constructor(root) {
        this.root = root;
        this.canvas = root.querySelector("#spwCanvas");
        this.ctx = this.canvas.getContext("2d");
        this.logoInput = root.querySelector("#spw_logo");
        this.positionSelect = root.querySelector("#spw_position");
        this.productImgUrl = root.dataset.productImage || "";
        this.logoImg = new Image();
        this.baseImg = new Image();
        this._bind();
        this._loadBase();
    }

    _bind() {
        if (this.logoInput) {
            this.logoInput.addEventListener("change", (ev) => this._onLogo(ev));
        }
        if (this.positionSelect) {
            this.positionSelect.addEventListener("change", () => this.render());
        }
        window.addEventListener("resize", () => this.render());
    }

    _loadBase() {
        if (!this.productImgUrl) return;
        this.baseImg.crossOrigin = "anonymous";
        this.baseImg.onload = () => this.render();
        this.baseImg.src = this.productImgUrl;
    }

    _onLogo(ev) {
        const file = ev.target.files?.[0];
        if (!file) return;
        const r = new FileReader();
        r.onload = () => {
            this.logoImg = new Image();
            this.logoImg.onload = () => this.render();
            this.logoImg.src = r.result;
            const hidden = this.root.querySelector("#spw_logo_data");
            if (hidden) hidden.value = r.result; // base64 para backend
        };
        r.readAsDataURL(file);
    }

    render() {
        const maxW = Math.min(700, this.root.clientWidth || 700);
        const ratio = this.baseImg.naturalWidth ? (this.baseImg.naturalHeight / this.baseImg.naturalWidth) : 1;
        this.canvas.width = maxW;
        this.canvas.height = Math.round(maxW * (ratio || 1));
        const ctx = this.ctx;
        ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        if (this.baseImg && this.baseImg.src) {
            ctx.drawImage(this.baseImg, 0, 0, this.canvas.width, this.canvas.height);
        }

        if (this.logoImg && this.logoImg.src) {
            // tamaño y posición aproximados
            const pos = (this.positionSelect && this.positionSelect.value) || "pecho";
            const logoW = Math.round(this.canvas.width * 0.28);
            const logoH = Math.round(logoW * ((this.logoImg.naturalHeight || 1) / (this.logoImg.naturalWidth || 1)));
            let x = (this.canvas.width - logoW) / 2;
            let y = Math.round(this.canvas.height * 0.25);
            if (pos === "espalda") y = Math.round(this.canvas.height * 0.35);
            if (pos === "lateral") x = Math.round(this.canvas.width * 0.7);
            ctx.globalAlpha = 0.92;
            ctx.drawImage(this.logoImg, x, y, logoW, logoH);
            ctx.globalAlpha = 1;
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("spw_customizer");
    if (root) new SPWPreview(root);
});

export default {};