/** @odoo-module **/

console.log("[SP] PROBE cargado (assets OK)");

(function () {
  const bar = document.createElement("div");
  bar.id = "sp-probe-bar";
  bar.textContent = "SP PROBE: assets OK";
  Object.assign(bar.style, {
    position: "fixed",
    top: "0", left: "0", right: "0",
    zIndex: "99999",
    background: "#ff2d55",
    color: "#fff",
    padding: "6px 10px",
    fontSize: "12px",
    textAlign: "center",
  });
  document.addEventListener("DOMContentLoaded", () => {
    document.body.appendChild(bar);
    setTimeout(() => bar.remove(), 3000); // se va a los 3s
  });
})();