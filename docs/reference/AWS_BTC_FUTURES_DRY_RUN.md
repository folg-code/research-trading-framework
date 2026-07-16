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

## Status API Lambda Image

The read-only status API Lambda image is defined in:

```text
deploy/aws/status-api-lambda/Dockerfile
```

Build locally from the repository root:

```bash
docker build \
  -f deploy/aws/status-api-lambda/Dockerfile \
  -t trading-framework/status-api-lambda:local .
```

Push it to a separate ECR repository, for example:

```text
trading-framework/status-api-lambda
```

Example tag and push commands:

```bash
docker tag trading-framework/status-api-lambda:local \
  <account-id>.dkr.ecr.<region>.amazonaws.com/trading-framework/status-api-lambda:latest

docker push \
  <account-id>.dkr.ecr.<region>.amazonaws.com/trading-framework/status-api-lambda:latest
```

The Lambda container command is:

```text
scripts.execution.aws_status_api_handler.lambda_handler
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
status, latest account and position snapshots, bounded recent events/orders/fills, and bounded recent
closed OHLCV bars. The AWS worker creates the DynamoDB client from
`TRADING_FRAMEWORK_AWS_REGION` when the backend is `dynamodb`.

## Read-Only Status API

The Lambda handler entry point is:

```text
scripts.execution.aws_status_api_handler.lambda_handler
```

It accepts API Gateway REST or HTTP API events and supports only `GET`. The handler:

- reads the latest DynamoDB `state_json` item directly to keep Lambda cold start small,
- returns a dashboard-ready status JSON shape compatible with `scripts/execution/show_execution_status.py`,
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
| `TRADING_FRAMEWORK_STATUS_API_RECENT_BARS` | `1440` | Recent closed OHLCV bar limit in API payload |

The status payload includes `recent_bars`, a bounded list of closed OHLCV bars with `open`, `high`,
`low`, `close`, `volume`, `observed_at`, `available_at` and `simulated`. Portfolio charts must use
this OHLCV list for candles, not synthesize bars from `last_price`.

For the container-image Lambda deployment, create the function from the
`trading-framework/status-api-lambda:latest` ECR image. The Lambda execution role needs read-only
access to the execution state table:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadDryRunState",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:<region>:<account-id>:table/trading-framework-dry-run-state"
    }
  ]
}
```

Minimum Lambda environment:

```text
TRADING_FRAMEWORK_AWS_REGION=<region>
TRADING_FRAMEWORK_EXECUTION_STATE_TABLE=trading-framework-dry-run-state
TRADING_FRAMEWORK_RUNTIME_ID=btc-futures-dry-run-aws
TRADING_FRAMEWORK_STATUS_API_CORS_ORIGIN=*
```

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

## Stale Heartbeat Alarm

Create one CloudWatch alarm over the EMF `Heartbeat` metric:

```text
Namespace: TradingFramework/DryRun
MetricName: Heartbeat
Dimensions:
  RuntimeId = btc-futures-dry-run-aws
  Provider = binance_usdm
  Symbol = BTCUSDT
Statistic: Sum
Period: 60 seconds
EvaluationPeriods: 3
DatapointsToAlarm: 3
Threshold: 1
ComparisonOperator: LessThanThreshold
TreatMissingData: breaching
Alarm meaning: no heartbeat was observed for roughly 3 minutes
```

Suggested alarm name:

```text
trading-framework-btc-futures-dry-run-stale-heartbeat
```

SNS action can be added later. For the portfolio demo MVP, the alarm definition and runbook are enough
to show the expected operating model.

## EventBridge Scheduled Operation

For the first demo mode, prefer a scheduled ECS task over an always-on ECS service:

```text
EventBridge Scheduler
  -> ECS RunTask
  -> btc-futures-dry-run-worker task definition
  -> DynamoDB read model remains available after the task stops
```

Recommended first schedule:

```text
Schedule: rate(1 day)
Task runtime: 15-60 minutes
Network: public subnets with assignPublicIp=ENABLED
Task definition: smoke settings removed; no TRADING_FRAMEWORK_MAX_MESSAGES
```

The scheduler role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RunTask"
      ],
      "Resource": "arn:aws:ecs:<region>:<account-id>:task-definition/btc-futures-dry-run-worker:*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::<account-id>:role/trading-framework-ecs-task-execution-role",
        "arn:aws:iam::<account-id>:role/trading-framework-dry-run-worker-task-role"
      ]
    }
  ]
}
```

Only one task should write to a given `TRADING_FRAMEWORK_RUNTIME_ID` at a time. Concurrent manual smoke
runs are acceptable during setup, but a steady demo should have one worker per runtime id.

## Operator Runbook

### Deploy Or Update Image

1. Build the container image from the repository root.
2. Push it to the selected ECR repository.
3. Update the ECS task definition image tag.
4. Run one short scheduled task with:

```text
TRADING_FRAMEWORK_DURATION_SECONDS=60
TRADING_FRAMEWORK_MAX_MESSAGES=1
TRADING_FRAMEWORK_EXECUTION_STATE_BACKEND=dynamodb
```

5. Confirm CloudWatch Logs include `runtime_started`, `heartbeat_recorded`,
   `market_message_processed` and `aws_worker_summary`.
6. Confirm DynamoDB has a `pk=RUNTIME#btc-futures-dry-run-aws`, `sk=STATE` item.
7. Confirm the read-only status API returns `simulated: true` and a bounded `recent_bars` array.

### Stop The Demo

For an always-on ECS service:

```text
desired_count = 0
```

For scheduled operation:

```text
disable the EventBridge schedule
```

The latest read model remains in DynamoDB after the worker stops.

### Restart The Demo

1. Re-enable the EventBridge schedule or set ECS service `desired_count = 1`.
2. Confirm a fresh `runtime_started` log appears.
3. Confirm a fresh `heartbeat_recorded` log appears within 60 seconds.
4. Confirm `updated_at` changes on the DynamoDB state item.

### Investigate Stale Heartbeat

1. Check CloudWatch alarm state and the last datapoint timestamp.
2. Open the ECS task logs and search for:

```text
runtime_failed
runtime_stopped
aws_worker_summary
Binance
DynamoDB
```

3. Check ECS task stopped reason, exit code and memory/CPU utilization.
4. Check outbound network access to Binance public WebSocket endpoints.
5. Check DynamoDB IAM permissions for `GetItem` and `PutItem`.
6. Restart the task after correcting configuration or transient network issues.

### Roll Back

1. Set ECS service `desired_count = 0` or disable the schedule.
2. Re-point the task definition to the previous known-good image tag.
3. Start one short smoke run before restoring the normal operating mode.
4. Confirm read-only API still serves the previous DynamoDB state while the worker is stopped.

## Cost Estimate And Operating Modes

Use AWS Pricing Calculator before deploying to a real AWS account. Prices vary by region, CPU
architecture, public IPv4 usage, NAT/data-transfer shape, log volume and retention. The MVP should be
operated with explicit limits, not as an unbounded production service.

Assumptions for a low-cost demo estimate:

```text
Region: eu-central-1 target, calculator-confirmed before deploy
Worker: 1 ECS Fargate task
Task size: 0.25 vCPU / 0.5 GB memory
Storage: default Fargate ephemeral storage
DynamoDB: on-demand, one small STATE item per runtime
API: HTTP API + Lambda, read-only status endpoint
Logs: structured JSON, 14-day retention
Metrics: one EMF heartbeat metric with RuntimeId/Provider/Symbol dimensions
Data transfer: small public Binance WebSocket ingress + small status API egress
```

### Recommended Demo Mode

Use scheduled operation first:

```text
EventBridge schedule
  -> run one ECS task for 15-60 minutes
  -> update DynamoDB read model
  -> leave API serving last state after worker stops
```

This keeps the demo visible while avoiding a permanently running task. It also proves cloud runtime,
persistence, logs, metrics and API integration.

### Operating Modes

| Mode | Worker runtime | Use case | Expected cost posture |
|------|----------------|----------|-----------------------|
| Smoke | 1-5 minutes on demand | Validate image, env, DynamoDB, API | cents-level per run |
| Scheduled demo | 15-60 minutes/day | Portfolio demo with fresh status windows | low monthly cost |
| Business-hours demo | 8 hours/day on weekdays | More realistic live monitoring demo | moderate monthly cost |
| Always-on | 24/7 ECS service | Strongest live demo signal | highest MVP cost |

### Cost Drivers

| Component | Cost driver | Control |
|-----------|-------------|---------|
| ECS Fargate | vCPU-seconds and GB-seconds | Use 0.25 vCPU / 0.5 GB first; prefer scheduled runs |
| DynamoDB | read/write requests and storage | One compact `STATE` item, bounded recent arrays |
| Lambda | requests and GB-seconds | Small read-only handler, no heavy dependencies in handler path |
| API Gateway | request count and response data transfer | Poll dashboard at a modest interval, e.g. 15-60 seconds |
| CloudWatch Logs | ingestion and retention | JSON logs only, retention 7-14 days for demo |
| CloudWatch Metrics | custom metric count | One heartbeat metric dimension set for one runtime |
| Public IPv4 / networking | task public IP or NAT path | Avoid NAT gateway for MVP if public subnet task is acceptable |

### Back-Of-Envelope Guidance

For a personal portfolio demo, start with scheduled mode. A daily 30-minute task is roughly 2% of the
compute duration of an always-on task, while still keeping the DynamoDB-backed dashboard useful. API,
DynamoDB and Lambda should remain small unless the public dashboard is polled aggressively.

Before switching to always-on:

1. Confirm the AWS Pricing Calculator estimate for the selected region.
2. Confirm CloudWatch log retention is bounded.
3. Confirm dashboard polling interval is not excessive.
4. Confirm there is no NAT gateway unless intentionally accepted.
5. Set a monthly AWS Budget alert for the demo account or project tag.

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
