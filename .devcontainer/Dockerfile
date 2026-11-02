# Workspace for GitHub Codespaces: Python 3.12 (engine and loaders), Node.js 22 (web app) and the Postgres 16
# client tools (pg_restore for the data snapshot). The database runs in its own container (compose.yml).
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# The base image lists a Yarn apt source that has broken builds when its key expired; Yarn is not used.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-common \
 && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
 && apt-get install -y --no-install-recommends postgresql-client-16 \
 && rm -rf /var/lib/apt/lists/*
