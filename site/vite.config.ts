import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Relative base so the static build works from any path (GitHub Pages project sites included).
// three.js needs no manual chunking: the loan field is lazy-imported, so it lands in its own
// chunk and stays out of the first paint.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
  // Compile syntax down for older iPhones too (Safari 15), not only the newest browsers.
  build: { target: ["es2020", "safari15"] },
  // The live demo API (python -m scripts.serve). Only the dev server proxies it: a production
  // build calls VITE_API_URL, or hides the demo when that is not set.
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
});
