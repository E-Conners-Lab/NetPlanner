# ── Stage 1: Build ────────────────────────────────────────────
FROM node:20-slim AS builder

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY package.json package-lock.json* ./

# Install all dependencies (including devDependencies needed for the build)
RUN npm ci

# Copy the rest of the source
COPY . .

# Produce the optimised static bundle
RUN npm run build

# ── Stage 2: Production ────────────────────────────────────────
FROM nginx:1.27-alpine AS production

# Patch base OS packages (openssl, expat, …) to clear fixable CVEs the pinned
# base tag ships behind (SEC-31). Re-runs on every rebuild for fresh fixes.
RUN apk upgrade --no-cache

# Remove the default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our SPA-aware nginx config
COPY nginx.conf /etc/nginx/conf.d/netplanner.conf

# Copy the built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Run nginx as a non-root user.
# nginx:1.27-alpine already ships with the 'nginx' user (uid 101).
# nginx.conf already listens on 8080 (non-privileged port).
# Grant ownership of runtime-writable paths to the nginx user.
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
