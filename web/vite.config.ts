/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// En développement, /api part vers l'API (uvicorn courtage.principal:app, port 8000).
// VITE_DEMO=1 : la démonstration statique, un seul script (les imports dynamiques intégrés).
const demo = process.env.VITE_DEMO === "1";
// VITE_MAQUETTE=1 : une page seule autour d'un composant (maquette.html), assemblée comme la démonstration.
const maquette = process.env.VITE_MAQUETTE === "1";

export default defineConfig({
  plugins: [react()],
  base: demo || maquette ? "./" : "/",
  build: maquette
    ? { outDir: "dist-maquette", assetsInlineLimit: 1_000_000,
        rollupOptions: { input: "maquette.html", output: { inlineDynamicImports: true } } }
    : demo ? { outDir: "dist-demo", assetsInlineLimit: 1_000_000, rollupOptions: { output: { inlineDynamicImports: true } } } : {},
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.ts"], globals: true },
});
