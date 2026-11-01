# Engine (FastAPI) and the nightly jobs share this image. Build from the repo root:
#   docker build -f deploy/engine.Dockerfile -t x25x125-engine .
# Fly runs it as the engine app (deploy/fly.engine.toml) and as the scheduled nightly Machine.
# PYTHON_IMAGE can point at a registry mirror if Docker Hub rate-limits the build.
ARG PYTHON_IMAGE=python:3.12.16-slim-bookworm
FROM ${PYTHON_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    HOST=:: \
    PORT=8080

WORKDIR /app

# Dependencies first so code edits don't reinstall them. The code reads data/ next to the packages
# (data/rules, data/reference), so it runs from /app as an editable install, not from site-packages.
COPY pyproject.toml ./
RUN mkdir core db engine jobs \
    && touch core/__init__.py db/__init__.py engine/__init__.py jobs/__init__.py \
    && pip install -e . \
    && rm -rf core db engine jobs

COPY core core
COPY db db
COPY engine engine
COPY jobs jobs
COPY data/rules data/rules
COPY data/sources data/sources
COPY data/reference data/reference

RUN useradd --create-home --uid 10001 app && mkdir -p /app/.dev-mail && chown app /app/.dev-mail
USER app

EXPOSE 8080
# HOST "::" listens on IPv6 and IPv4, so Fly's private network (x25x125-engine.internal, IPv6) reaches it.
# On a machine without IPv6 (some local Docker setups) run with -e HOST=0.0.0.0.
# WEB_CONCURRENCY sets the worker count (default 1; see docs/deploy.md for memory per worker).
CMD ["sh", "-c", "exec uvicorn engine.app:app --host ${HOST} --port ${PORT} --workers ${WEB_CONCURRENCY:-1}"]
