/* SPW: inyecta botón 'Personalizar' y muestra badge de diagnóstico */
(function () {
    if (window.__SPW_LOADED__) return;  // evita dobles cargas
    window.__SPW_LOADED__ = true;

    function ready(fn) {
        if (document.readyState !== 'loading') fn();
        else document.addEventListener('DOMContentLoaded', fn);
    }

    function badge(text, color) {
        try {
            var el = document.createElement('div');
            el.id = 'spw_probe';
            el.textContent = text;
            el.style.cssText =
                'position:fixed;bottom:8px;right:8px;z-index:99999;' +
                'padding:6px 10px;border-radius:6px;border:1px solid #333;' +
                'background:' + (color || '#dff0ff') + ';font:12px system-ui;';
            document.body.appendChild(el);
            setTimeout(function () { el.remove(); }, 6000);
        } catch (e) { /* nada */ }
    }

    ready(function () {
        badge('SPW JS OK');  // <- si ves esto, el JS está cargando

        // Localiza el <form> de compra en la ficha de producto (varía por tema)
        var form =
            document.querySelector('form.o_wsale_product_form') ||
            document.querySelector('#product_details form') ||
            document.querySelector('.o_wsale_product_page form') ||
            document.querySelector('.o_product_page form');

        if (!form) { console.warn('SPW: no se encontró el form'); return; }

        // Evitar duplicados
        if (document.getElementById('spw_customize_btn')) return;

        // ID del template desde la URL /shop/...-<id>
        var m = window.location.pathname.match(/-(\d+)(?:\/)?$/);
        var tmplId = m ? m[1] : null;
        if (!tmplId) { badge('SPW: sin ID de producto', '#ffe3e3'); return; }

        // Ancla: junto al botón Add to cart
        var addToCartBtn = form.querySelector('button[type="submit"], .o_add_to_cart');
        var anchor = addToCartBtn ? addToCartBtn.parentElement : form;

        var btn = document.createElement('a');
        btn.id = 'spw_customize_btn';
        btn.href = '/personalizar/' + tmplId;
        btn.className = 'btn btn-outline-primary ms-2';
        btn.style.marginLeft = '8px';
        btn.textContent = 'Personalizar';
        anchor.appendChild(btn);
    });
})();