/* D3 Power Tools — theme switcher
   Reads/writes localStorage key "d3pt-theme".
   Values: "light" (default), "dark".

   Usage:
     <script src="/style/theme-switch.js"></script>
   Injects a toggle button into [data-theme-switch] or top-right fixed.

   API:
     d3pt.setTheme("dark")
     d3pt.setTheme("light")
     d3pt.theme  // "light"|"dark"
*/

;(function () {
  const KEY = "d3pt-theme";
  const stored = localStorage.getItem(KEY);

  if (stored) document.documentElement.setAttribute("data-theme", stored);

  // SVG icons — moon shown in light mode (click for dark), sun in dark mode
  const MOON = '<svg width="16" height="16" viewBox="0 0 16 16"><path d="M12.4 10.3A5 5 0 115.7 3.6a4 4 0 006.7 6.7z" fill="var(--color-text-muted)" stroke="var(--color-text-muted)" stroke-width="0.5"/></svg>';
  const SUN = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="8" cy="8" r="3"/><line x1="8" y1="1.5" x2="8" y2="3"/><line x1="8" y1="13" x2="8" y2="14.5"/><line x1="1.5" y1="8" x2="3" y2="8"/><line x1="13" y1="8" x2="14.5" y2="8"/><line x1="3.4" y1="3.4" x2="4.5" y2="4.5"/><line x1="11.5" y1="11.5" x2="12.6" y2="12.6"/><line x1="3.4" y1="12.6" x2="4.5" y2="11.5"/><line x1="11.5" y1="4.5" x2="12.6" y2="3.4"/></svg>';

  function resolvedTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  }

  function setTheme(value) {
    const theme = value === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(KEY, theme);
    d3pt.theme = theme;
    updateButton();
    document.documentElement.dispatchEvent(
      new CustomEvent("themechange", { detail: { theme } })
    );
  }

  const d3pt = (window.d3pt = window.d3pt || {});
  d3pt.setTheme = setTheme;
  d3pt.theme = resolvedTheme();

  let btn;

  function updateButton() {
    if (!btn) return;
    const isDark = resolvedTheme() === "dark";
    btn.innerHTML = isDark ? SUN : MOON;
    btn.title = isDark ? "Switch to light" : "Switch to dark";
    btn.setAttribute("aria-label", btn.title);
  }

  function mount() {
    const anchor = document.querySelector("[data-theme-switch]");
    btn = document.createElement("button");
    btn.className = "theme-toggle";
    btn.addEventListener("click", () =>
      setTheme(resolvedTheme() === "dark" ? "light" : "dark")
    );
    updateButton();

    if (anchor) {
      anchor.appendChild(btn);
    } else {
      btn.style.cssText =
        "position:fixed;top:12px;right:12px;z-index:9999";
      document.body.appendChild(btn);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
