// serial_printer_custom_wizard/static/src/js/customizer.js
// Vanilla JS seguro: solo actúa en la página del configurador
(function () {
  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var canvas = document.getElementById('spw_canvas');
    if (!canvas) return; // no estamos en la página del configurador

    var imgLogo = document.getElementById('spw_logo_preview');
    var input   = document.getElementById('spw_logo_input');
    var size    = document.getElementById('spw_size');
    var rot     = document.getElementById('spw_rotate');
    var posx    = document.getElementById('spw_posx');
    var posy    = document.getElementById('spw_posy');

    function applyTransform() {
      var s = (parseInt(size && size.value || '70', 10)) / 100;
      var r = parseInt(rot && rot.value || '0', 10);
      var x = parseInt(posx && posx.value || '50', 10);
      var y = parseInt(posy && posy.value || '60', 10);

      imgLogo.style.left = x + '%';
      imgLogo.style.top  = y + '%';
      imgLogo.style.transform = 'translate(-50%, -50%) scale(' + s + ') rotate(' + r + 'deg)';
    }

    [size, rot, posx, posy].forEach(function (el) {
      if (el) el.addEventListener('input', applyTransform);
    });

    if (input) {
      input.addEventListener('change', function (ev) {
        var file = ev.target.files && ev.target.files[0];
        if (!file) return;

        // Limpia el blob anterior si lo hubiera
        if (imgLogo.dataset.url) {
          URL.revokeObjectURL(imgLogo.dataset.url);
          delete imgLogo.dataset.url;
        }

        var url = URL.createObjectURL(file);
        imgLogo.dataset.url = url;
        imgLogo.src = url;
        imgLogo.classList.remove('d-none');
        applyTransform();
      });
    }
  });
})();