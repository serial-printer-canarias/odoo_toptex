/** SPW – Controles extra sin tocar código existente */
(function () {
    "use strict";

    if (!location.pathname.startsWith("/personalizar/")) return;

    const Q = (s, r = document) => r.querySelector(s);
    const QA = (s, r = document) => [...r.querySelectorAll(s)];

    /* ---------- 1) Imagen de variante ---------- */
    function applyVariantImage() {
        const img = Q("#spw_base_img") || Q(".spw-base-img") || Q(".o_wsale_product_img img");
        if (!img) return;

        const url = new URL(location.href);
        const vid = url.searchParams.get("vid");
        if (vid) {
            img.src = `/web/image/product.product/${vid}/image_1920`;
        }
    }

    /* ---------- 2) Render de panel extra ---------- */
    const TECHNIQUES = [
        { key: "serigrafia",  label: "Serigrafía" },
        { key: "dtf",         label: "DTF" },
        { key: "bordado",     label: "Bordado" },
        { key: "cuero",       label: "Marcado en cuero" },
    ];

    // Paleta editable (pon aquí los colores exactos de tu carta NS300)
    const NS300_COLORS = [
        { code: "BLACK",        hex: "#000000" },
        { code: "WHITE",        hex: "#FFFFFF", border: true },
        { code: "NAVY",         hex: "#0B1F3A" },
        { code: "ROYAL",        hex: "#4169E1" },
        { code: "RED",          hex: "#CF1020" },
        { code: "BURGUNDY",     hex: "#6D071A" },
        { code: "ORANGE",       hex: "#FF7F00" },
        { code: "YELLOW",       hex: "#FFD700" },
        { code: "GOLD",         hex: "#C6A700" },
        { code: "KELLY",        hex: "#198754" },
        { code: "FOREST",       hex: "#064E3B" },
        { code: "BOTTLE",       hex: "#003D2E" },
        { code: "SKY",          hex: "#87CEEB" },
        { code: "TURQUOISE",    hex: "#40E0D0" },
        { code: "PURPLE",       hex: "#6F42C1" },
        { code: "FUCHSIA",      hex: "#E91E63" },
        { code: "PINK",         hex: "#FFC0CB", border: true },
        { code: "GREY",         hex: "#808080" },
        { code: "LIGHT_GREY",   hex: "#D3D3D3", border: true },
        { code: "CHARCOAL",     hex: "#333333" },
        { code: "BROWN",        hex: "#6F4E37" },
        { code: "SAND",         hex: "#C2B280" },
        { code: "OLIVE",        hex: "#6B8E23" },
        { code: "KHAKI",        hex: "#BDB76B" },
    ];

    function ensureHost() {
        // Buscamos un sitio neutro bajo las instrucciones
        let host = Q("#spw-extra-controls");
        if (host) return host;
        host = document.createElement("section");
        host.id = "spw-extra-controls";
        host.className = "spw-extra";
        // Por defecto lo añadimos tras el primer h3/p de instrucciones
        const anchor = Q(".spw-instructions") || Q("p, .oe_structure, .s_text") || Q(".container");
        (anchor && anchor.parentElement ? anchor.parentElement : document.body).appendChild(host);
        return host;
    }

    function renderControls() {
        const host = ensureHost();
        if (!host) return;

        host.innerHTML = `
            <div class="spw-group">
                <div class="spw-label">Tipo de personalización</div>
                <div class="spw-chips" id="spw-tech-chips"></div>
            </div>

            <div class="spw-group">
                <div class="spw-label">Color (paleta)</div>
                <div class="spw-swatches" id="spw-color-swatches"></div>
            </div>

            <div class="spw-group">
                <div class="spw-label">Posición rápida</div>
                <div class="spw-chips" id="spw-pos-chips">
                  <button type="button" class="spw-chip" data-pos="pecho_izq">Pecho izq.</button>
                  <button type="button" class="spw-chip" data-pos="pecho_dcha">Pecho dcha.</button>
                  <button type="button" class="spw-chip" data-pos="espalda">Espalda</button>
                  <button type="button" class="spw-chip" data-pos="libre">Libre</button>
                </div>
            </div>

            <div class="spw-group">
                <label class="spw-label" for="spw_notes">Observaciones</label>
                <textarea id="spw_notes" class="spw-notes" rows="3" placeholder="Tamaño de impresión y notas…"></textarea>
            </div>
        `;

        // Técnicas
        const techWrap = Q("#spw-tech-chips", host);
        TECHNIQUES.forEach(t => {
            const b = document.createElement("button");
            b.type = "button";
            b.className = "spw-chip";
            b.dataset.value = t.key;
            b.textContent = t.label;
            b.addEventListener("click", () => selectChip(techWrap, b));
            techWrap.appendChild(b);
        });

        // Colores
        const swWrap = Q("#spw-color-swatches", host);
        NS300_COLORS.forEach(c => {
            const s = document.createElement("button");
            s.type = "button";
            s.className = "spw-swatch";
            s.style.setProperty("--sw", c.hex);
            if (c.border) s.classList.add("sw-has-border");
            s.title = c.code;
            s.dataset.code = c.code;
            s.addEventListener("click", () => selectSwatch(swWrap, s));
            swWrap.appendChild(s);
        });

        // Posiciones rápidas
        Q("#spw-pos-chips", host).addEventListener("click", (ev) => {
            const b = ev.target.closest(".spw-chip"); if (!b) return;
            const where = b.dataset.pos;
            setQuickPosition(where);
            selectChip(Q("#spw-pos-chips"), b);
        });
    }

    function selectChip(container, btn) {
        QA(".spw-chip", container).forEach(x => x.classList.remove("is-selected"));
        btn.classList.add("is-selected");
    }
    function selectSwatch(container, btn) {
        QA(".spw-swatch", container).forEach(x => x.classList.remove("is-selected"));
        btn.classList.add("is-selected");
    }

    /* ---------- 3) Integramos con sliders existentes ---------- */
    function setSliderValue(idOrEl, v) {
        const el = typeof idOrEl === "string" ? Q(idOrEl) : idOrEl;
        if (!el) return;
        el.value = v;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
    }

    // Ajusta según tus rangos actuales de sliders (0..100)
    function setQuickPosition(where) {
        const x = Q("#spw_pos_x");
        const y = Q("#spw_pos_y");
        if (!x || !y) return;
        const W = 100, H = 100;
        const map = {
            "pecho_izq":  { x: 30, y: 35 },
            "pecho_dcha": { x: 70, y: 35 },
            "espalda":    { x: 50, y: 25 },
            "libre":      { x: Number(x.value) || 50, y: Number(y.value) || 50 },
        };
        const t = map[where] || map.libre;
        setSliderValue(x, t.x);
        setSliderValue(y, t.y);
    }

    /* ---------- 4) Antes de añadir al carrito, guardamos los valores ---------- */
    function ensureHiddenFields() {
        let f = Q("#spw_hidden_fields");
        if (!f) {
            f = document.createElement("div");
            f.id = "spw_hidden_fields";
            f.style.display = "none";
            (Q("form") || document.body).appendChild(f);
        }
        function ensure(name) {
            let i = Q(`input[name="${name}"]`, f);
            if (!i) {
                i = document.createElement("input");
                i.type = "hidden";
                i.name = name;
                f.appendChild(i);
            }
            return i;
        }
        return { f, ensure };
    }

    function collectAndAttach() {
        const { ensure } = ensureHiddenFields();
        // Técnica
        const tech = Q("#spw-tech-chips .spw-chip.is-selected");
        ensure("spw_technique").value = tech ? tech.dataset.value : "";

        // Color
        const sw = Q("#spw-color-swatches .spw-swatch.is-selected");
        ensure("spw_color_code").value = sw ? sw.dataset.code : "";

        // Notas
        ensure("spw_notes").value = (Q("#spw_notes") && Q("#spw_notes").value) || "";

        // Posición elegida (opcional)
        const pos = Q("#spw-pos-chips .spw-chip.is-selected");
        ensure("spw_position").value = pos ? pos.dataset.pos : "";

        // Ids
        const tmpl = Q('input[name="product_template_id"]') || Q('input[name="product_template"]');
        const vid  = Q('input[name="product_id"]');
        ensure("spw_product_template_id").value = tmpl && tmpl.value ? tmpl.value : "";
        ensure("spw_product_id").value = vid && vid.value ? vid.value : "";
    }

    function hookSubmission() {
        // Capturamos clicks en botones principales del wizard
        document.addEventListener("click", (ev) => {
            const a = ev.target.closest('button[type="submit"], .spw-add-to-cart, a[href*="/shop/cart"]');
            if (!a) return;
            collectAndAttach();
        }, { capture: true });
        // Por si es un submit nativo
        document.addEventListener("submit", (ev) => {
            collectAndAttach();
        }, { capture: true });
    }

    /* ---------- Init ---------- */
    applyVariantImage();
    renderControls();
    hookSubmission();
})();