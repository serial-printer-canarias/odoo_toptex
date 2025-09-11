(function () {
  function byId(id) { return document.getElementById(id); }

  const wrap  = byId('spw_canvas');
  const base  = byId('spw_base_img');
  const logo  = byId('spw_logo_img');
  const file  = byId('spw_logo');        // <input type="file" id="spw_logo">
  const sScale = byId('spw_scale');      // slider tamaño
  const sRot   = byId('spw_rotate');     // slider rotación
  const sX     = byId('spw_pos_x');      // slider X
  const sY     = byId('spw_pos_y');      // slider Y

  if (!wrap || !base || !logo || !file) return;

  const state = { x: 0, y: 0, scale: 1, rot: 0 };

  function getScaleValue() {
    if (!sScale) return 1;
    const v = parseFloat(sScale.value || '100'); // si tu slider va 0..100
    return v > 3 ? v / 100 : v;                  // 100 -> 1
  }

  function apply() {
    logo.style.transform =
      `translate(${state.x}px, ${state.y}px) rotate(${state.rot}deg) scale(${state.scale})`;
  }

  function centerLogoOnce() {
    const W = wrap.clientWidth;
    const H = wrap.clientHeight || base.clientHeight;
    const w = logo.naturalWidth || logo.width || 200;
    const h = logo.naturalHeight || logo.height || 200;
    state.x = (W - w) / 2;
    state.y = (H - h) / 2;
  }

  file.addEventListener('change', (ev) => {
    const f = ev.target.files && ev.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      logo.src = e.target.result;
      logo.onload = () => {
        logo.style.display = 'block';
        state.scale = getScaleValue();
        state.rot = sRot ? parseFloat(sRot.value || '0') : 0;
        centerLogoOnce();
        apply();
      };
    };
    reader.readAsDataURL(f);
  });

  if (sScale) sScale.addEventListener('input', () => { state.scale = getScaleValue(); apply(); });
  if (sRot)   sRot.addEventListener('input',   () => { state.rot   = parseFloat(sRot.value || '0'); apply(); });
  if (sX)     sX.addEventListener('input',     () => { state.x     = parseInt(sX.value || '0', 10); apply(); });
  if (sY)     sY.addEventListener('input',     () => { state.y     = parseInt(sY.value || '0', 10); apply(); });

  // Arrastrar el logo
  let dragging = false, last = { x: 0, y: 0 };
  function startDrag(x, y) { dragging = true; last = { x, y }; }
  function moveDrag(x, y)  { if (!dragging) return; state.x += x - last.x; state.y += y - last.y; last = { x, y }; apply(); }
  function endDrag()       { dragging = false; }

  logo.addEventListener('mousedown', (e) => { e.preventDefault(); startDrag(e.clientX, e.clientY); });
  document.addEventListener('mousemove', (e) => moveDrag(e.clientX, e.clientY));
  document.addEventListener('mouseup', endDrag);

  logo.addEventListener('touchstart', (e) => { const t = e.touches[0]; startDrag(t.clientX, t.clientY); }, { passive: true });
  document.addEventListener('touchmove', (e) => { const t = e.touches[0]; moveDrag(t.clientX, t.clientY); }, { passive: true });
  document.addEventListener('touchend', endDrag);

  window.addEventListener('resize', () => { if (logo.style.display !== 'none') { centerLogoOnce(); apply(); } });
})();