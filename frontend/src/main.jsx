import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { applyTheme, getTheme } from "./theme";
import "./index.css";

// Apply the saved theme before the first paint (no flash of the wrong mode).
applyTheme(getTheme());

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
