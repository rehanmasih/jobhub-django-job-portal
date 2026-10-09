// Auto-dismiss flash messages after a few seconds and confirm destructive actions.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".alert.auto-dismiss").forEach(function (el) {
    setTimeout(function () {
      if (window.bootstrap) { bootstrap.Alert.getOrCreateInstance(el).close(); }
    }, 6000);
  });
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (e) {
      if (!window.confirm(el.getAttribute("data-confirm"))) { e.preventDefault(); }
    });
  });
});
