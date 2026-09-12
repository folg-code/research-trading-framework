# Sprint 031 — Wave 0 Decisions

Date: 2026-07-18.

## D-S031-01 — Dashboard stays read-only for live paper

**Decision:** `apps/dashboard` only **visualizes** paper state via status API GET.
No start/stop worker, no order submission, no DynamoDB writes from the app.

## D-S031-02 — Worker owns execution

**Decision:** ECS worker continues to run full paper path (signal → paper broker →
persist). Status Lambda remains GetItem-only.

## D-S031-03 — Strategy Model is the domain object

**Decision:** Live/AWS paper trading must be driven by
`StrategyModelDefinition` (same domain type as Strategy Research). Live
adapters may support a subset of expressions initially, but must not introduce a
parallel AWS-only strategy type.

## D-S031-04 — Status URL configuration

**Decision:** `DASHBOARD_STATUS_URL` env and/or Streamlit sidebar. Missing URL →
clear configuration message, no crash.
