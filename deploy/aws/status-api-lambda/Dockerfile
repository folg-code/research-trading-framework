# syntax=docker/dockerfile:1.7

FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install --no-cache-dir uv==0.9.17

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY scripts ./scripts

RUN uv pip install --system --no-cache .

CMD ["scripts.execution.aws_status_api_handler.lambda_handler"]
