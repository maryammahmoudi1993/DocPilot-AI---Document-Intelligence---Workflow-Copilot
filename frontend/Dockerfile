# Production image. The frontend is deliberately NOT containerized for
# local development (see root docker-compose.yml's comment — `npm run
# dev` is faster and more reliable there); this image exists purely for
# a production-parity deployment/dry-run build (Phase 11).
#
# Multi-stage: build the static Vite bundle in a node image, then serve
# it from a minimal nginx image — the final image never contains
# node_modules, source TypeScript, or the Node runtime itself.

FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# VITE_API_BASE_URL is baked into the static bundle at build time (Vite
# env vars are compile-time, not runtime) — see docs/DEPLOYMENT.md for
# why that means a rebuild is required to point at a different backend,
# not just a container restart.
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
