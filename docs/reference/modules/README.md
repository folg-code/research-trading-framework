# Modules — Context Map

Per-package/per-app implementation reference. This is Sprint 055 T005's
context-map for the folder. This tree holds two different kinds of
document, distinguished below — the filenames alone don't signal which.

## Implementation references (what a package does and how)

| File | Purpose |
|---|---|
| [`MARKET_ANALYSIS_MODULE.md`](MARKET_ANALYSIS_MODULE.md) | Market Analysis implementation guide — flow, key types, verification, design notes |
| [`ANALYSIS_COMPONENT_CATALOG.md`](ANALYSIS_COMPONENT_CATALOG.md) | The full built-in component catalog — per-component semantics, warm-up, output fields, zero-denominator conventions |
| [`PREDICTIVE_PROMOTION.md`](PREDICTIVE_PROMOTION.md) | Predictive model promotion — parameter-file schema, store layout, fingerprint derivation, guards |
| [`DASHBOARD_APPLICATION.md`](DASHBOARD_APPLICATION.md) | Research Dashboard (`apps/dashboard`) — boundary, contracts, pages, publishing runbook |

## Operator/author-facing guides (how to use a package)

| File | Purpose |
|---|---|
| [`MODEL_AUTHORING.md`](MODEL_AUTHORING.md) | Authoring DSL — one copy-pasteable market + signal model |
| [`STRATEGY_AUTHORING.md`](STRATEGY_AUTHORING.md) | Custom strategy authoring (`strategy_file`) — loading contract, trust model, error table |
| [`STRATEGY_EXAMPLES.md`](STRATEGY_EXAMPLES.md) | Worked example strategies (`build_strategy()`) using the catalog above |
| [`OPERATOR_CLI.md`](OPERATOR_CLI.md) | Operator CLI (`trading-cli` / `apps/cli`) — command groups, config schema pointer, exit codes |

## What's deliberately *not* here

Domain-level questions ("what does Market Analysis own?", "which package
implements the Strategy domain?") belong in
[`../system/DOMAIN_MODEL.md`](../system/DOMAIN_MODEL.md) and
[`../system/MODULE_MAP.md`](../system/MODULE_MAP.md), not here. There is
deliberately no `modules/SIGNALS.md`, `modules/STRATEGY.md`,
`modules/EXECUTION.md`, or `modules/DATA.md` — no module-level
implementation reference exists for those (Market Data's is a workflow
document at [`../workflows/MARKET_DATA.md`](../workflows/MARKET_DATA.md)
instead). See
`docs/planning/sprints/SPRINT_055_T001_REFERENCE_TARGET_IA.md` §5.4 for
why each was rejected rather than fabricated.
