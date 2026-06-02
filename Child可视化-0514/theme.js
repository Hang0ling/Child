(function () {
  const STORAGE_KEY = "child-theme";
  const root = document.documentElement;

  function storedTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // The UI still works when storage is unavailable.
    }
  }

  function applyTheme(theme) {
    const next = theme === "light" ? "light" : "dark";
    root.dataset.theme = next;
    saveTheme(next);
    window.dispatchEvent(new CustomEvent("child-theme-change", { detail: { theme: next } }));
  }

  function syncButton(button) {
    const isLight = root.dataset.theme === "light";
    button.setAttribute("aria-pressed", String(isLight));
    button.dataset.mode = isLight ? "light" : "dark";
    button.setAttribute("aria-label", isLight ? "切换到深色模式" : "切换到浅色模式");
    button.title = isLight ? "切换到深色模式" : "切换到浅色模式";
  }

  function mountToggle() {
    const button = document.createElement("button");
    button.className = "theme-toggle";
    button.type = "button";
    button.innerHTML = '<span class="theme-icon" aria-hidden="true"></span>';

    button.addEventListener("click", () => {
      applyTheme(root.dataset.theme === "light" ? "dark" : "light");
      syncButton(button);
    });

    document.body.appendChild(button);
    syncButton(button);
  }

  applyTheme(storedTheme() || root.dataset.theme);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mountToggle);
  } else {
    mountToggle();
  }
})();
