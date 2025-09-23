// Prueba visible y en consola para confirmar que el asset carga
(function () {
  const badge = document.createElement("div");
  badge.textContent = "SP assets ON";
  badge.style.cssText = "position:fixed;right:8px;bottom:8px;z-index:99999;background:#10b981;color:#fff;font:12px/1.2 sans-serif;padding:6px 8px;border-radius:6px;opacity:.85";
  document.addEventListener("DOMContentLoaded", () => document.body.appendChild(badge));
  window.__SP__ = { loaded: true, ts: Date.now() };
  console.log("[SP] web.assets_frontend cargado ✅");
})();