FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev \
    --extra-index-url https://download.pytorch.org/whl/cpu
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev \
    --extra-index-url https://download.pytorch.org/whl/cpu

# Debug: Check if venv exists
RUN ls -la /app/.venv/bin/ || echo "VENV NOT FOUND"
RUN /app/.venv/bin/python --version
RUN /app/.venv/bin/pip list | grep -E "arq|transformers" || echo "PACKAGES NOT FOUND"

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app:$PYTHONPATH"

WORKDIR /app/src
CMD ["/app/.venv/bin/arq", "app.core.worker.settings.WorkerSettings", "--verbose"]

