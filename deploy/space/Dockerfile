# The 25x125 website on Hugging Face Spaces (docs/website.md). .github/workflows/website.yml copies this file and
# README.md into the Space with REF set to the commit to run; the Space builds it and serves port 3000.
# One container: PostgreSQL 16 + PostGIS, the engine (Python 3.12) and the web app (Node.js 22).
FROM python:3.12-slim-bookworm

COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:22-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -sf ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git gnupg postgresql-common \
 && /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y \
 && apt-get install -y --no-install-recommends postgresql-16 postgresql-16-postgis-3 \
 && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

ARG REPO=https://github.com/GeddyLifeson/25x125.git
ARG REF=main
RUN git init -q . && git remote add origin "$REPO" \
 && git fetch -q --depth 1 origin "$REF" && git checkout -q FETCH_HEAD

# Python packages, web packages and the web build (scripts/codespace.py setup), plus the backup client.
RUN pip install --no-cache-dir --user huggingface_hub==0.36.0 \
 && NEXT_TELEMETRY_DISABLED=1 python scripts/codespace.py setup \
 && rm -rf web/.next/cache ~/.npm ~/.cache

ENV LOCAL_MODE=1 APP_ENV=development PYTHONUNBUFFERED=1 NEXT_TELEMETRY_DISABLED=1 \
    DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/x25x125
EXPOSE 3000
CMD ["python", "scripts/space.py"]
