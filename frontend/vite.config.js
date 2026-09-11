import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev server proxies API + figures to the FastAPI backend.
// Override with: VITE_PROXY_TARGET=http://localhost:8010 npm run dev
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target, changeOrigin: true },
      "/figures": { target, changeOrigin: true },
      "/docs": { target, changeOrigin: true },
      "/openapi.json": { target, changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
        },
      },
    },
  },
});
