# Web app (Next.js standalone server). Build from the repo root:
#   docker build -f deploy/web.Dockerfile -t x25x125-web .
# The app imports rule files from data/rules at build time, so the context is the repo root.
# NEXT_PUBLIC_BASEMAP_STYLE is read at build time (default: OpenFreeMap Positron; "none" = plain background).
ARG NODE_IMAGE=node:22.23.4-bookworm-slim

FROM ${NODE_IMAGE} AS build
WORKDIR /repo/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY data/rules /repo/data/rules
COPY web /repo/web
ARG NEXT_PUBLIC_BASEMAP_STYLE
ENV NEXT_TELEMETRY_DISABLED=1 NEXT_OUTPUT=standalone NEXT_PUBLIC_BASEMAP_STYLE=${NEXT_PUBLIC_BASEMAP_STYLE}
RUN if [ -z "$NEXT_PUBLIC_BASEMAP_STYLE" ]; then unset NEXT_PUBLIC_BASEMAP_STYLE; fi && npm run build

FROM ${NODE_IMAGE}
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 APP_ENV=production PORT=3000 HOSTNAME=::
WORKDIR /app
# outputFileTracingRoot is the repo root, so the server sits at web/server.js inside the standalone folder.
COPY --from=build --chown=node:node /repo/web/.next/standalone ./
COPY --from=build --chown=node:node /repo/web/.next/static ./web/.next/static
USER node
EXPOSE 3000
CMD ["node", "web/server.js"]
