// static/src/js/customizer_preview.js
document.addEventListener('DOMContentLoaded', () => {
  const fileInput = document.querySelector('#spw_logo_input, input[name="spw_logo"]');
  const img = document.getElementById('spw_logo_preview');
  if (!fileInput || !img) return;

  fileInput.addEventListener('change', (ev) => {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    const url = URL.createObjectURL(file);
    img.src = url;
    img.classList.remove('d-none');
    img.onload = () => URL.revokeObjectURL(url);
  });
});