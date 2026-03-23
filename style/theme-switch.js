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
    btn.dataset.current = isDark ? "\u263E" : "\u2600"; // ☾ in dark, ☀ in light
    btn.dataset.alt = isDark ? "\u2600" : "\u263E";     // swap on hover
    btn.textContent = btn.dataset.current;
    btn.title = isDark ? "Light theme" : "Dark theme";
    btn.setAttribute("aria-label", btn.title);
  }

  function mount() {
    const anchor = document.querySelector("[data-theme-switch]");
    btn = document.createElement("button");
    btn.className = "theme-toggle";
    btn.addEventListener("click", () =>
      setTheme(resolvedTheme() === "dark" ? "light" : "dark")
    );
    btn.addEventListener("mouseenter", () => { btn.textContent = btn.dataset.alt; });
    btn.addEventListener("mouseleave", () => { btn.textContent = btn.dataset.current; });
    btn.addEventListener("focus", () => { btn.textContent = btn.dataset.alt; });
    btn.addEventListener("blur", () => { btn.textContent = btn.dataset.current; });
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
