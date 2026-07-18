# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/dashboard/.venv

WORKDIR /opt/dashboard

RUN pip install --no-cache-dir uv==0.9.17

COPY pyproject.toml uv.lock README.md ./
COPY Project_Overview.py ./
COPY pages ./pages
COPY src ./src

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PATH=/opt/dashboard/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DASHBOARD_STORAGE_ROOT=/data \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /opt/dashboard

RUN addgroup --system dashboard && adduser --system --ingroup dashboard dashboard \
    && mkdir -p /data && chown dashboard:dashboard /data

COPY --from=builder /opt/dashboard /opt/dashboard

USER dashboard

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health')"

CMD ["streamlit", "run", "Project_Overview.py", "--server.port=8501", "--server.address=0.0.0.0"]
