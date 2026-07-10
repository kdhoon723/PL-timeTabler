# syntax=docker/dockerfile:1.7
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
RUN pip install --no-cache-dir "uv>=0.8,<0.9"
WORKDIR /app/apps/backend
COPY apps/backend/pyproject.toml apps/backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/backend/README.md ./README.md
COPY apps/backend/src ./src
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /app/apps/backend/.venv /app/.venv
# uv-generated console scripts retain the builder project path in their
# shebang. Keep that path valid in the runtime image while using one venv.
RUN mkdir -p /app/apps/backend && ln -s /app/.venv /app/apps/backend/.venv
COPY apps/backend/src /app/apps/backend/src
COPY data /app/data
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/apps/backend/src" \
    PYTHONUNBUFFERED=1 \
    TIMETABLER_DATA_ROOT=/app/data \
    TIMETABLER_ENVIRONMENT=production
USER app
EXPOSE 8000
CMD ["timetabler-api"]
