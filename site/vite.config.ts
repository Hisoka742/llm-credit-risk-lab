import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Relative base so the static build works from any path (GitHub Pages project sites included).
// three.js needs no manual chunking: the loan field is lazy-imported, so it lands in its own
// chunk and stays out of the first paint.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss()],
});
