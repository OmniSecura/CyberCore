import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Service routing map.
 * Each key is a URL prefix (matched by Vite proxy in order — more specific first).
 * Add new microservices here as they come online.
 */
const SERVICES = {
  "/api/v1/organizations": "http://localhost:8081",  // organization-service
  "/api/v1/invites":       "http://localhost:8081",  // organization-service (invite accept)
  "/api/v1/users":         "http://localhost:8000",  // auth-service
  "/api/v1/email":         "http://localhost:8000",  // auth-service
  // "/api/v1/agents":     "http://localhost:8082",  // agent-service (future)
  // "/api/v1/alerts":     "http://localhost:8083",  // alert-service (future)
  // "/api/v1/logs":       "http://localhost:8084",  // log-service   (future)
};

const proxy = Object.fromEntries(
  Object.entries(SERVICES).map(([prefix, target]) => [
    prefix,
    { target, changeOrigin: true, secure: false },
  ])
);

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy,
  },
});
