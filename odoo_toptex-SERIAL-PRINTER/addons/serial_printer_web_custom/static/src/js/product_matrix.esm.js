/** SP Matrix — bootstrap mínimo visible y con “pruebas” */
(function () {
  const log = (...a) => (_sp?.debug?.log || console.log.bind(console, '[SP]'))(...a);

  function badge(text, ok=true) {
    const b = document.createElement('div');
    b.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:999999;' +
      'padding:6px 10px;border-radius:6px;font:600 12px/1.2 system-ui;' +
      (ok ? 'background:#0a0;color:#fff' : 'background:#c00;color:#fff');
    b.textContent = 'SP ' + text;
    document.body.appendChild(b);
    setTimeout(() => b.remove(), 3000);
  }

  function buildOnce() {
    if (document.getElementById('sp-matrix')) return true;

    // Contenedor robusto (varios fallbacks)
    const container =
      document.querySelector('.o_wsale_product_page') ||
      document.querySelector('main .container') ||
      document.querySelector('main') ||
      document.body;

    if (!container) return false;

    // Usa el ancla XML si está, si no lo crea
    let anchor = container.querySelector('#sp-matrix-anchor');
    if (!anchor) {
      anchor = document.createElement('div');
      anchor.id = 'sp-matrix-anchor';
      anchor.className = 'sp-matrix-anchor';
      container.appendChild(anchor);
    }

    // Placeholder MUY visible para validar
    const box = document.createElement('div');
    box.id = 'sp-matrix';
    box.className = 'sp-matrix';
    box.innerHTML = `
      <div class="sp-matrix__placeholder">
        <strong>SP Matrix</strong> — ancla OK. (Ahora hidrataremos variantes, precio y stock)
      </div>
      <button type="button" class="btn btn-primary mt-2 sp-add-to-cart">Añadir selección</button>
    `;
    anchor.appendChild(box);

    log('product_matrix activo: placeholder pintado');
    badge('Matrix pintado', true);
    return true;
  }

  function start() {
    // 1) Intento inmediato
    if (buildOnce()) return;

    // 2) Observador por si el DOM llega después
    const mo = new MutationObserver(() => {
      if (buildOnce()) mo.disconnect();
    });
    mo.observe(document.documentElement, { childList: true, subtree: true });

    // 3) Último intento por timeout
    setTimeout(() => { buildOnce() || badge('No encontró contenedor', false); }, 2500);
  }

  // Exponer helper manual: en consola ejecutar _sp.test()
  window._sp = window._sp || {};
  _sp.test = () => buildOnce();

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();