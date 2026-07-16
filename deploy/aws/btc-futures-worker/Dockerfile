# syntax=docker/dockerfile:1.7

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

ENTRYPOINT ["python", "-m", "scripts.execution.run_aws_btc_futures_worker"]
