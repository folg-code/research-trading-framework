# Sprint 022 - AWS Runtime MVP for BTC Futures Dry Run

## Metadata

```text
Sprint: 022
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: IN_PROGRESS
Planned Start: 2026-07-16
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_021
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - SPRINT_021.md
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (Strategy Execution, operational state)
  - docs/planning/ROADMAP.md (Phase 8)
```

---

## 0. Slice Choice

This sprint deploys the dry-run runtime to AWS. The goal is to demonstrate cloud-native runtime
operation, not to build a trading production system.

Preferred MVP architecture:

```text
ECS Fargate service
  -> BTCUSDT dry-run worker

DynamoDB
  -> latest runtime status
  -> recent events
  -> simulated orders/fills/positions

CloudWatch
  -> logs
  -> metrics
  -> alarms

API Gateway + Lambda
  -> read-only status endpoint
```

**Out of scope:** real exchange credentials, AWS trading secrets, multi-region deployment, CI/CD
automation beyond basic scripts, private VPC hardening beyond MVP, public dashboard UI.

---

## 1. Sprint Goal

```text
Containerized dry-run worker
  -> AWS runtime deployment
  -> DynamoDB execution read model
  -> CloudWatch logs and heartbeat metric
  -> public read-only status API
```

Success: the dry-run worker runs in AWS against Binance public BTCUSDT futures data and exposes a
read-only sanitized status endpoint for the portfolio dashboard.

---

## 2. MVP Scope Checklist

- [x] Add container entry point for BTCUSDT dry-run worker.
- [x] Add DynamoDB adapter for execution repository protocols.
- [x] Add AWS configuration model with explicit region/table names.
- [x] Add infrastructure notes or minimal IaC for ECS, DynamoDB, CloudWatch, API Gateway and Lambda.
- [x] Add read-only Lambda/API handler for latest status.
- [ ] Add CloudWatch log fields and heartbeat metric.
- [ ] Add stale heartbeat alarm design.
- [x] Add deployment/runbook documentation.
- [ ] Add cost estimate for always-on or scheduled operation.

---

## 3. Security and Safety

```text
No Binance API keys.
No real exchange account.
No endpoint that mutates runtime state.
No public endpoint exposing raw infrastructure identifiers beyond what is necessary.
Dashboard API is read-only and sanitized.
```

---

## 4. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S022-T001 | Add container runtime entry point | DONE |
| S022-T002 | Add DynamoDB execution repository adapter | DONE |
| S022-T003 | Add AWS config model and environment validation | DONE |
| S022-T004 | Add read-only status API handler | DONE |
| S022-T005 | Add CloudWatch structured logging and metrics | TODO |
| S022-T006 | Add stale heartbeat alarm/runbook notes | TODO |
| S022-T007 | Add deployment documentation or minimal IaC | DONE |
| S022-T008 | Add AWS smoke checklist | DONE |
| S022-T009 | Add cost estimate and operating modes | TODO |

---

## 5. Acceptance Criteria

1. AWS worker writes live dry-run status to DynamoDB.
2. Public API can return latest sanitized status without write permissions.
3. CloudWatch logs show startup, feed connection, heartbeat, simulated lifecycle events and shutdown.
4. Runtime can be stopped without losing last read model.
5. Documentation explains how to deploy, stop and verify the demo.
6. Quality gates pass locally before deployment.

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| AWS scope grows into full platform deployment | Keep one worker, one table family, one read-only API |
| Costs drift upward | Add operating mode: scheduled or always-on, with estimate |
| Public API becomes control plane | Read-only IAM and no mutation routes |
| Runtime fails silently | Heartbeat metric, stale alarm and DEGRADED status |

---

## 7. Post-Sprint Direction

Sprint 023 adds the OVH-hosted portfolio dashboard page that consumes the AWS read-only API.
