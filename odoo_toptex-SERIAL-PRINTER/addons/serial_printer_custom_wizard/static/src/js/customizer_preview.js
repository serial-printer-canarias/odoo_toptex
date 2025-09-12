/** preview local del logo **/
document.addEventListener('DOMContentLoaded', () => {
  const file = document.getElementById('spw_logo_input');
  const preview = document.getElementById('spw_logo_preview');
  if (!file || !preview) return;

  file.addEventListener('change', e => {
    const f = e.target.files && e.target.files[0];
    if (!f) { preview.removeAttribute('src'); preview.classList.add('d-none'); return; }
    const reader = new FileReader();
    reader.onload = evt => {
      preview.src = evt.target.result;
      preview.classList.remove('d-none');
    };
    reader.readAsDataURL(f);
  });
});