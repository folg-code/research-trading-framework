# syntax=docker/dockerfile:1.7
#
# VPS BTC futures dry-run status service (ADR-0035 SS1, SS3). GET-only, reads
# the execution-state volume read-only. Built with the repository root as
# context so it can reuse src/ and scripts/ unchanged. Never published to a
# host port -- Compose ``expose``-only, reachable only from ``dashboard``.

FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/trading-framework/.venv

WORKDIR /opt/trading-framework

RUN pip install --no-cache-dir uv==0.9.17

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scripts ./scripts

RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PATH=/opt/trading-framework/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/trading-framework

RUN addgroup --system trading && adduser --system --ingroup trading trading

COPY --from=builder /opt/trading-framework /opt/trading-framework

USER trading

EXPOSE 8090

# Process liveness + state-volume readability only, per /healthz (ADR-0035 SS4.5).
# Must not report unhealthy merely because the worker/state is absent.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8090/healthz')"]

ENTRYPOINT ["python", "-m", "scripts.execution.run_vps_status_service"]
