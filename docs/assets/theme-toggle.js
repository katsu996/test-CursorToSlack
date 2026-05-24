/**
 * K Original Pages: 配色トグル（自動 → ライト → ダーク → 自動）
 * #theme-toggle / #theme-toggle-icon / #theme-toggle-text を想定。
 */
(function () {
  var THEME_STORAGE = "k-original-color-scheme";

  var THEME_ICONS = {
    system:
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>',
    light:
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>',
    dark:
      '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>',
  };

  function applyThemeClass(mode) {
    var html = document.documentElement;
    html.classList.remove("theme-light", "theme-dark");
    if (mode === "light") html.classList.add("theme-light");
    else if (mode === "dark") html.classList.add("theme-dark");
  }

  function storedThemeMode() {
    var v = localStorage.getItem(THEME_STORAGE);
    if (v === "light" || v === "dark") return v;
    return "system";
  }

  function setThemeButtonLabel(btn, mode) {
    if (!btn) return;
    var label = mode === "light" ? "ライト" : mode === "dark" ? "ダーク" : "自動";
    var iconKey = mode === "light" ? "light" : mode === "dark" ? "dark" : "system";
    var iconEl = document.getElementById("theme-toggle-icon");
    var textEl = document.getElementById("theme-toggle-text");
    if (iconEl) iconEl.innerHTML = THEME_ICONS[iconKey] || "";
    if (textEl) textEl.textContent = label;
    btn.setAttribute("aria-label", "配色: " + label + "（クリックで切替）");
    btn.setAttribute("aria-pressed", mode === "system" ? "false" : "true");
    btn.title = "配色: " + label + "（クリックで 自動→ライト→ダーク→自動）";
  }

  function initKOriginalThemeToggle() {
    var mode = storedThemeMode();
    applyThemeClass(mode === "system" ? null : mode);
    var btn = document.getElementById("theme-toggle");
    setThemeButtonLabel(btn, mode);
    if (!btn) return;
    btn.addEventListener("click", function () {
      var cur = storedThemeMode();
      var next = cur === "system" ? "light" : cur === "light" ? "dark" : "system";
      if (next === "system") localStorage.removeItem(THEME_STORAGE);
      else localStorage.setItem(THEME_STORAGE, next);
      var m = storedThemeMode();
      applyThemeClass(m === "system" ? null : m);
      setThemeButtonLabel(btn, m);
    });
  }

  if (typeof window !== "undefined") {
    window.initKOriginalThemeToggle = initKOriginalThemeToggle;
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initKOriginalThemeToggle);
    } else {
      initKOriginalThemeToggle();
    }
  }
})();
