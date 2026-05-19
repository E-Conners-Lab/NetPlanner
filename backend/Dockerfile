# NetPlanner backend image.
# Slim base (SEC-31), runs as a non-root user (SEC-31, SEC-32).
FROM python:3.12-slim

# uv binary, pinned to an exact release (SEC-30).
COPY --from=ghcr.io/astral-sh/uv:0.9.21 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Native libraries WeasyPrint needs for PDF rendering (Phase 5 readiness).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies first so the layer caches across code changes.
# --frozen fails the build if uv.lock drifts from pyproject.toml; --no-dev
# excludes test/lint tooling from the production image (SEC-29, SEC-31).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# SEC-31 / SEC-32 — least privilege: drop root, own the SQLite data dir.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
