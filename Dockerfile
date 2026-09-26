# Une image : l'API (Python) sert l'interface construite (React). Une origine, un cookie, pas de CORS.

# --- 1. L'interface ------------------------------------------------------------
FROM node:22-slim AS interface
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

# --- 2. L'API --------------------------------------------------------------------
FROM python:3.11-slim
# WeasyPrint (les rapports PDF) : Pango, HarfBuzz, et DejaVu, la police des gabarits.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 courtage
WORKDIR /app
COPY api/pyproject.toml ./
COPY api/src ./src
RUN pip install --no-cache-dir .
COPY --from=interface /web/dist /app/web
COPY deploiement/demarrer.sh /app/demarrer.sh

ENV COURTAGE_WEB=/app/web \
    PYTHONUNBUFFERED=1 \
    PORT=8000
USER courtage
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/v1/sante', timeout=4)"
CMD ["sh", "/app/demarrer.sh"]
