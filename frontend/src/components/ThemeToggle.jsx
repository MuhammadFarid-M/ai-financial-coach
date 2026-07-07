import { useState } from "react";
import { getTheme, setTheme } from "../theme";

// Fixed top-right toggle. Shows a sun while in dark mode (tap -> go light) and
// a moon while in light mode (tap -> go dark).
export default function ThemeToggle() {
  const [theme, setLocalTheme] = useState(getTheme());
  const isDark = theme === "dark";

  function toggle() {
    const next = isDark ? "light" : "dark";
    setTheme(next);
    setLocalTheme(next);
  }

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Light mode" : "Dark mode"}
    >
      {isDark ? (
        // sun
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <circle cx="12" cy="12" r="4.2" fill="currentColor" />
          <g stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
            <line x1="12" y1="2.5" x2="12" y2="5" />
            <line x1="12" y1="19" x2="12" y2="21.5" />
            <line x1="2.5" y1="12" x2="5" y2="12" />
            <line x1="19" y1="12" x2="21.5" y2="12" />
            <line x1="5.1" y1="5.1" x2="6.9" y2="6.9" />
            <line x1="17.1" y1="17.1" x2="18.9" y2="18.9" />
            <line x1="5.1" y1="18.9" x2="6.9" y2="17.1" />
            <line x1="17.1" y1="6.9" x2="18.9" y2="5.1" />
          </g>
        </svg>
      ) : (
        // moon
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
          <path
            fill="currentColor"
            d="M21 12.8A8.5 8.5 0 0 1 11.2 3a7 7 0 1 0 9.8 9.8z"
          />
        </svg>
      )}
    </button>
  );
}
