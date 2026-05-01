import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Base URL for the backend — change this one constant before deploying
const API_BASE = "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: API_BASE,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});