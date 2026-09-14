# Phase 17 — Research Application (Local Workbench)

Status: **ACCEPTED**. Architecture triage complete (ADR-0037 through ADR-0042,
accepted by the maintainer 2026-09-14). [Sprint 064](../sprints/SPRINT_064.md)
is approved (Wave 0 sign-off 2026-09-14) and open. This is the index for the
accepted phase; [Current Status](../CURRENT_STATUS.md) is authoritative for
active sprint work.

## Purpose

Deliver the first increment of `docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md`:
one local, desktop-first operator workflow — `apps/workbench` — that lets a
single researcher go from market-data acquisition through Signal Research
result comparison without opening a terminal, while leaving all research,
analytical and model-evaluation logic in the framework (`src/`) rather than
the application UI. Scope and non-goals are fixed by
`docs/product/PRD-research-workbench-mvp.md`.

This is a distinct product surface from Phase 16: Phase 16 is research
*artifacts and scoring* delivered through existing runners plus the public
portfolio dashboard (a read-only, public consumer per ADR-0022/ADR-0034).
Phase 17 is a *private, local* control surface that invokes Market Data and
Signal Research workflows directly. Phase 17 does not depend on Phase
16E–16G and does not touch `apps/dashboard`.

## Increment family

| Increment | State | Detail |
|---|---|---|
| 17A Canonical config + CLI entry point + workbench skeleton | Planned (Sprint 064 draft) | ADR-0037, ADR-0038 |
| 17B Job runner + first end-to-end Signal Research run | Planned (Sprint 064 draft) | ADR-0041 |
| 17C Data Manager (import, preview, validation/acknowledgement, Binance form) | Directional | ADR-0039, ADR-0040 |
| 17D Run catalog + comparison | Directional | ADR-0042 |

## Governing ADRs

- [ADR-0037](../../adr/ADR-0037-research-workbench-application-boundary.md) — Application boundary and control surface (`apps/workbench`, loopback JSON API, link-out to the existing dashboard/report)
- [ADR-0038](../../adr/ADR-0038-canonical-signal-research-configuration-and-templates.md) — Canonical Signal Research configuration (`SignalResearchDefinitionSpec` + `schema_version`) and template ownership
- [ADR-0039](../../adr/ADR-0039-trusted-local-model-discovery.md) — Trusted local model discovery (non-importing `model.yaml` sidecar scan)
- [ADR-0040](../../adr/ADR-0040-import-validation-findings-and-acknowledgement.md) — Import validation findings: fatal vs. acknowledgeable, acknowledgement gates finalize
- [ADR-0041](../../adr/ADR-0041-workbench-local-job-runner.md) — Local job runner: one job = one `trading-cli` subprocess, cancellation, structured progress, interrupted-on-restart
- [ADR-0042](../../adr/ADR-0042-workbench-catalog-index-and-comparison-facts.md) — Catalog index (rebuildable cache, manifests win) and comparison-compatibility facts

## Related technical debt

- [TD-035](../TECHNICAL_DEBT.md) — Trusted local model lineage hash covers only the entry file (ADR-0039 §6)

## Sequencing

Opens after Sprint 062/T007 (Phase 16D VPS deploy/rollback and 24-hour
observation) closes. Technically parallelizable — disjoint surfaces from
Phase 16D — but deliberately sequenced rather than run concurrently: one
maintainer, and T007 involves a live production deploy.

## Binding rules for the whole phase

- No Signal Research metric calculation in the application presentation
  layer (PRD success metrics; ADR-0013 Signal Research Analytics Boundary).
- No grid search, sweep, hyperopt, or automated candidate generation from the
  UI (PRD non-goals) — one submission is one consciously specified study.
- No editing, repairing, deleting, or silently migrating market data,
  datasets, runs, reports, or model artifacts; unsupported artifacts stay
  visible and marked `UNSUPPORTED`/`INCOMPLETE`, never rewritten (ADR-0042).
- No automatic retry or resume of interrupted work after an application or
  worker restart (ADR-0041 §6).
- `apps/workbench` follows the same `apps/*` import-boundary discipline as
  `apps/cli` (ADR-0022 rule 2, restated per-app by ADR-0037; ADR-0026
  precedent) — no reimplementation of research/analysis internals in the UI.

## Anticipated follow-up ADRs

None identified beyond ADR-0037–0042 for 17A/17B. 17C/17D increments may
surface narrower Wave 0 decisions (e.g. index storage format, per-job-kind
phase lists) rather than new ADRs, per the triage report; check the
[ADR index](../../adr/README.md) for what has since been accepted.
