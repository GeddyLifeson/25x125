# Map tile server (Martin), the same version as docker-compose.yml, with martin/config.yaml baked in.
#   docker build -f deploy/tiles.Dockerfile -t x25x125-tiles .
# Needs DATABASE_URL (secret). On Fly, MARTIN_LISTEN=[::]:3000 (set in deploy/fly.tiles.toml) so the
# private network reaches it at http://x25x125-tiles.internal:3000.
FROM ghcr.io/maplibre/martin:v0.18.1
COPY martin/config.yaml /config/config.yaml
EXPOSE 3000
CMD ["--config", "/config/config.yaml"]
