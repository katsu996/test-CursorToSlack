/**
 * トップの「並び替え・絞り込み・列の表示」パネル開閉（Escape で閉じる）。
 */
(function () {
  "use strict";

  function initToolbarCollapse() {
    var btn = document.getElementById("toolbar-panel-toggle");
    var panel = document.getElementById("toolbar-panel");
    var chev = btn && btn.querySelector(".filter-chevron");
    if (!btn || !panel) return;
    btn.addEventListener("click", function () {
      var willOpen = panel.hidden;
      panel.hidden = !willOpen;
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
      if (chev) chev.textContent = willOpen ? "▲" : "▼";
    });
    btn.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !panel.hidden) {
        panel.hidden = true;
        btn.setAttribute("aria-expanded", "false");
        if (chev) chev.textContent = "▼";
        btn.focus();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initToolbarCollapse);
  } else {
    initToolbarCollapse();
  }
})();
