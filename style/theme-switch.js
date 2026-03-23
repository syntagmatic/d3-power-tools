/* D3 Power Tools — theme switcher
   Reads/writes localStorage key "d3pt-theme".
   Values: "light" (default), "dark".

   Usage:
     <script src="/style/theme-switch.js"></script>
   Injects a .theme-switch widget into the first element matching
   [data-theme-switch] or, if absent, the <body> (top-right fixed).

   Can also be called manually:
     d3pt.setTheme("dark")
     d3pt.setTheme("light")
     d3pt.theme               // current theme ("light"|"dark")
*/

;(function () {
  const KEY = "d3pt-theme";
  const stored = localStorage.getItem(KEY);

  // Apply immediately to prevent FOWT
  if (stored) document.documentElement.setAttribute("data-theme", stored);

  function resolvedTheme() {
    return document.documentElement.getAttribute("data-theme") || "light";
  }

  function setTheme(value) {
    const theme = value === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem(KEY, theme);
    d3pt.theme = theme;
    updateButtons();
    document.documentElement.dispatchEvent(
      new CustomEvent("themechange", { detail: { theme } })
    );
  }

  // Public API
  const d3pt = (window.d3pt = window.d3pt || {});
  d3pt.setTheme = setTheme;
  d3pt.theme = resolvedTheme();

  // ── Widget ──

  let container;

  function updateButtons() {
    if (!container) return;
    const current = resolvedTheme();
    container.querySelectorAll("button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === current);
    });
  }

  function mount() {
    const anchor = document.querySelector("[data-theme-switch]");
    container = document.createElement("div");
    container.className = "theme-switch";
    container.setAttribute("role", "group");
    container.setAttribute("aria-label", "Color theme");

    [
      ["light", "\u2600"], // ☀
      ["dark", "\u263E"], // ☾
    ].forEach(([id, icon]) => {
      const btn = document.createElement("button");
      btn.dataset.theme = id;
      btn.textContent = icon;
      btn.title = id.charAt(0).toUpperCase() + id.slice(1);
      btn.setAttribute("aria-label", btn.title + " theme");
      btn.addEventListener("click", () => setTheme(id));
      container.appendChild(btn);
    });

    if (anchor) {
      anchor.appendChild(container);
    } else {
      container.style.cssText =
        "position:fixed;top:12px;right:12px;z-index:9999";
      document.body.appendChild(container);
    }
    updateButtons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
