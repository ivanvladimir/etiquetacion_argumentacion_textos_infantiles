FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim as builder

WORKDIR /app

# Cache dependencies layer
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Copy and install project
COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Remove unnecessary files to reduce size
RUN find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
RUN find /app/.venv -type f -name "*.pyc" -delete
RUN find /app/.venv -type f -name "*.pyo" -delete
RUN find /app/.venv/lib -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
RUN find /app/.venv/lib -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# Final stage - minimal runtime
FROM python:3.12-slim-bookworm

WORKDIR /app

# Copy only the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

WORKDIR /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["/app/.venv/bin/arq", "app.core.worker.settings.WorkerSettings", "--verbose"]
