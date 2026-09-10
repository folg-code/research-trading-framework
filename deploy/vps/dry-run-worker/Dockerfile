# syntax=docker/dockerfile:1.7
#
# VPS BTC futures dry-run worker (ADR-0035 SS1). Provider-neutral over the
# same runtime the AWS worker uses (deploy/aws/btc-futures-worker/Dockerfile);
# built with the repository root as context so it can reuse src/ and scripts/
# unchanged, without publishing or exposing any port -- this process is
# outbound-only (Binance public market data).

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

RUN addgroup --system trading && adduser --system --ingroup trading trading \
    && mkdir -p /var/lib/trading-framework/btc-futures-dry-run \
    && chown trading:trading /var/lib/trading-framework/btc-futures-dry-run

COPY --from=builder /opt/trading-framework /opt/trading-framework

USER trading

# No EXPOSE: this process never listens (ADR-0035 SS1 rule 1).

# Liveness is heartbeat freshness of the worker's own persisted state, not
# "process running" (ADR-0035 SS4.5). See scripts/execution/vps_worker_healthcheck.py.
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-m", "scripts.execution.vps_worker_healthcheck"]

ENTRYPOINT ["python", "-m", "scripts.execution.run_vps_btc_futures_worker"]
