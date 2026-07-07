import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server runs on 5173 — which is exactly the origin the backend's CORS
// settings already allow (see CORS_ORIGINS in the backend .env).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
});
