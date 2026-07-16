# AWS BTC Futures Dry-Run Worker

This reference describes the Sprint 022 AWS worker packaging slice for the BTCUSDT futures dry-run
demo.

## Container Image

The worker image is defined in:

```text
deploy/aws/btc-futures-worker/Dockerfile
```

Build locally from the repository root:

```bash
docker build \
  -f deploy/aws/btc-futures-worker/Dockerfile \
  -t trading-framework/btc-futures-worker:local .
```

Run locally with bounded execution:

```bash
docker run --rm \
  -e TRADING_FRAMEWORK_AWS_REGION=eu-central-1 \
  -e TRADING_FRAMEWORK_EXECUTION_STATE_TABLE=demo-execution-state \
  -e TRADING_FRAMEWORK_EXECUTION_STATE_BACKEND=local \
  -e TRADING_FRAMEWORK_DURATION_SECONDS=60 \
  -e TRADING_FRAMEWORK_MAX_MESSAGES=5 \
  trading-framework/btc-futures-worker:local
```

The entry point is:

```text
python -m scripts.execution.run_aws_btc_futures_worker
```

## Environment Contract

Required variables:

| Variable | Purpose |
|----------|---------|
| `TRADING_FRAMEWORK_AWS_REGION` | AWS region for the runtime deployment |
| `TRADING_FRAMEWORK_EXECUTION_STATE_TABLE` | DynamoDB execution state table name |

Optional variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRADING_FRAMEWORK_EXECUTION_STATE_BACKEND` | `dynamodb` | State backend: `dynamodb` for AWS, `local` for container smoke/dev |
| `TRADING_FRAMEWORK_RUNTIME_ID` | `btc-futures-dry-run-aws` | Runtime identity used in state records |
| `TRADING_FRAMEWORK_SYMBOL` | `BTCUSDT` | Binance USD-M futures symbol |
| `TRADING_FRAMEWORK_EVENT_LOG_PATH` | `/tmp/trading_framework/btc_futures_dry_run/events.jsonl` | Local JSONL event fallback |
| `TRADING_FRAMEWORK_STATE_REPOSITORY_PATH` | `/tmp/trading_framework/btc_futures_dry_run/state` | Local JSON state fallback until DynamoDB is wired |
| `TRADING_FRAMEWORK_STARTING_EQUITY` | `10000` | Simulated starting equity |
| `TRADING_FRAMEWORK_QUANTITY` | `0.001` | Simulated order quantity |
| `TRADING_FRAMEWORK_EMA_PERIOD` | `20` | Demo strategy EMA period |
| `TRADING_FRAMEWORK_EXIT_AFTER_BARS` | `10` | Demo strategy time-based exit threshold |
| `TRADING_FRAMEWORK_DURATION_SECONDS` | `3600` | Bounded worker runtime |
| `TRADING_FRAMEWORK_HEARTBEAT_SECONDS` | `30` | Runtime heartbeat interval |
| `TRADING_FRAMEWORK_MAX_CLOSED_BARS` | `200` | Rolling closed-bar window |
| `TRADING_FRAMEWORK_MAX_MESSAGES` | unset | Optional stop-after-message limit for smoke runs |

## ECS/Fargate MVP Notes

The image is intended for a single ECS Fargate service or scheduled task:

```text
ECS task
  -> container image
  -> worker entry point
  -> Binance public WebSocket
  -> execution repository
  -> read-only status API
```

Current packaging can run with either the local JSON state repository or DynamoDB. Use
`TRADING_FRAMEWORK_EXECUTION_STATE_BACKEND=local` for local container smoke runs. Use the default
`dynamodb` backend in ECS/Fargate.

`DynamoDbExecutionStateRepository` implements the same `ExecutionStateRepository` port against a
DynamoDB state item.

The MVP DynamoDB item shape is:

```text
pk = RUNTIME#{runtime_id}
sk = STATE
runtime_id
version
updated_at
state_json
```

`state_json` contains the same explicit state document used by the local JSON adapter: latest runtime
status, latest account and position snapshots, and bounded recent events/orders/fills. The AWS worker
creates the DynamoDB client from `TRADING_FRAMEWORK_AWS_REGION` when the backend is `dynamodb`.

## Read-Only Status API

The Lambda handler entry point is:

```text
scripts.execution.aws_status_api_handler.lambda_handler
```

It accepts API Gateway REST or HTTP API events and supports only `GET`. The handler:

- loads the same AWS runtime env contract as the worker,
- reads the latest `RuntimeStatusView` through `ExecutionStateRepository`,
- returns the same status JSON shape as `scripts/execution/show_execution_status.py`,
- returns `404` when the runtime state is missing,
- returns `405` for mutation methods,
- includes `Cache-Control: no-store`,
- does not include DynamoDB table names or raw infrastructure identifiers in the response body.

Optional API variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `TRADING_FRAMEWORK_STATUS_API_CORS_ORIGIN` | `*` | CORS origin for the read-only status response |
| `TRADING_FRAMEWORK_STATUS_API_RECENT_EVENTS` | `50` | Recent event limit in API payload |
| `TRADING_FRAMEWORK_STATUS_API_RECENT_ORDERS` | `20` | Recent simulated order limit in API payload |
| `TRADING_FRAMEWORK_STATUS_API_RECENT_FILLS` | `20` | Recent simulated fill limit in API payload |

## CloudWatch Logs And Metrics

The worker emits structured JSON logs to stdout. ECS/Fargate sends stdout to CloudWatch Logs when the
task definition uses the `awslogs` log driver.

Lifecycle log events:

| Event | Purpose |
|-------|---------|
| `runtime_started` | Worker runtime start |
| `heartbeat_recorded` | Runtime heartbeat and CloudWatch EMF metric |
| `market_message_processed` | Binance message consumed or ignored |
| `runtime_stopped` | Bounded worker runtime stop |
| `aws_worker_summary` | Final bounded run summary |

Common fields:

```text
runtime_id
provider
symbol
status
simulated
occurred_at
```

Heartbeat logs include CloudWatch Embedded Metric Format fields:

```text
_aws.CloudWatchMetrics[0].Namespace = TradingFramework/DryRun
Heartbeat = 1
RuntimeId / Provider / Symbol dimensions
```

This keeps metrics dependency-free in code: CloudWatch extracts the heartbeat metric from structured
logs, and the worker does not need direct CloudWatch write permissions.

## Smoke Checklist

1. Build the image from the repository root.
2. Run with `TRADING_FRAMEWORK_MAX_MESSAGES=1` and a short duration.
3. Confirm the process exits with status code `0`.
4. Confirm stdout contains `"event": "aws_worker_summary"`.
5. Confirm stdout contains `"simulated": true`.
6. Confirm no Binance API keys or account credentials are required.

## Safety Boundary

This worker is a dry-run demo process:

- no Binance API keys,
- no authenticated exchange account,
- no order submission endpoint,
- no public mutation route,
- simulated trades only.
