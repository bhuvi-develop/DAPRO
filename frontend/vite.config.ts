import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(__dirname, "src") } },
  server: {
    port: 5180,
    proxy: { "/api": { target: process.env.DAPRO_API_URL ?? "http://localhost:8410", changeOrigin: false } },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
          radix: ["@radix-ui/react-dialog", "@radix-ui/react-dropdown-menu", "@radix-ui/react-select",
                  "@radix-ui/react-tabs", "@radix-ui/react-popover", "@radix-ui/react-tooltip"],
        },
      },
    },
  },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"], include: ["src/**/*.test.{ts,tsx}"] },
} as never);
