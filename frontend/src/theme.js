// Light/dark theme, persisted in localStorage and applied as a data attribute
// on <html>. CSS reads [data-theme="light"] to swap the palette.
const KEY = "afw_theme";

export function getTheme() {
  return localStorage.getItem(KEY) || "dark"; // dark is the default identity
}

export function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

export function setTheme(theme) {
  localStorage.setItem(KEY, theme);
  applyTheme(theme);
}
