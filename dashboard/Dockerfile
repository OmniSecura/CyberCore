# ── Stage 1: Build the React/Vite app ────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install deps first (layer-cached unless package.json changes)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build
# Output lands in /app/dist


# ── Stage 2: Serve with nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Replace the default config with ours (SPA routing + API proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
