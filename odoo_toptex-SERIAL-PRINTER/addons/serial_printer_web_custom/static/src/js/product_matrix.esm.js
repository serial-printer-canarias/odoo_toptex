/** SP Matrix (bootstrap) - inserta contenedor en el ancla fijo */
(function () {
  const whenReady = (fn) => {
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
      setTimeout(fn, 0);
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  };

  whenReady(() => {
    try {
      const page = document.querySelector('.o_wsale_product_page');
      if (!page) {
        _sp.debug.warn('No se encontró .o_wsale_product_page (tema distinto?)');
        return;
      }

      // 1) ancla estable que añadimos por XML
      let anchor = page.querySelector('#sp-matrix-anchor');
      if (!anchor) {
        // fallback defensivo: lo creamos al final de la página de producto
        anchor = document.createElement('div');
        anchor.id = 'sp-matrix-anchor';
        anchor.className = 'sp-matrix-anchor';
        page.appendChild(anchor);
      }

      // 2) pinta un placeholder (para validar que aparece en pantalla)
      if (!anchor.querySelector('#sp-matrix')) {
        const box = document.createElement('div');
        box.id = 'sp-matrix';
        box.className = 'sp-matrix';
        box.innerHTML = `
          <div class="sp-matrix__placeholder">
            <strong>SP Matrix</strong> — ancla OK. (Luego hidratamos precios/stock)
          </div>`;
        anchor.appendChild(box);
      }

      _sp.debug.ok('product_matrix activo (ancla OK)');
    } catch (e) {
      console.error('[SP] product_matrix error:', e);
    }
  });
})();