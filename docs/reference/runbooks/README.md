# Runbooks — Context Map

Operator how-to-run/deploy guides — written for someone with a terminal
open, not for architectural understanding. This is Sprint 055 T005's
context-map for the folder.

## One demo family, three angles

All three runbooks cover the **same** demo — the BTC futures dry-run — from
different angles, and share the **same safety boundary**: simulated
execution only, no credentials, no real orders placed.

| File | Angle |
|---|---|
| [`LOCAL_BTC_FUTURES_DRY_RUN.md`](LOCAL_BTC_FUTURES_DRY_RUN.md) | Running it locally: live-data ingestion, simulated execution, operator notes |
| [`AWS_BTC_FUTURES_DRY_RUN.md`](AWS_BTC_FUTURES_DRY_RUN.md) | Deploying it to AWS: dry-run worker container packaging, smoke checklist |
| [`LIVE_PAPER_PIPELINE_INSPECTION.md`](LIVE_PAPER_PIPELINE_INSPECTION.md) | Verifying it end-to-end: the live-paper/AWS dry-run pipeline architecture verdict and operator checklist |

## There are no research-workflow runbooks

`data fetch`, `research run`, and `report render` have no dedicated
runbook — their operator surface (commands, config schema, exit codes) is
documented in [`../modules/OPERATOR_CLI.md`](../modules/OPERATOR_CLI.md)
instead. This is a known gap (see
`docs/planning/sprints/SPRINT_055_T001_REFERENCE_TARGET_IA.md` §5.3), not
something this sprint fills — stop looking here for it.
