# Workflows — Context Map

End-to-end research/operational workflows. This is Sprint 055 T005's
context-map for the folder — see `docs/planning/sprints/SPRINT_055_T001_REFERENCE_TARGET_IA.md`
§5.2/§8 for the full rationale.

## Workflow Architecture (shared preamble)

> Carried here from the retired `docs/reference/system/WORKFLOWS_ARCHITECTURE.md`'s
> opening section by Sprint 055 T005 (moved out of `RESEARCH_METHODOLOGIES.md`,
> where Sprint 055 T007 had parked it as an interim measure).

The framework's three primary workflows — Signal Research, Strategy
Research, Strategy Execution — must not be represented as a mandatory
pipeline:

```text
Signal Research
        ↓
Strategy Research
        ↓
Strategy Execution
```

This would incorrectly imply that every workflow requires the output of
the previous workflow. The correct architecture is:

```text
                         Shared Domains
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       Signal Research   Strategy Research   Strategy Execution
```

Shared domains include: Market, Market Analysis, Strategy, Research,
Execution, Time, Configuration, Infrastructure contracts. Each workflow
has its own purpose, inputs, orchestration, outputs, persistence model,
and analytics or runtime state.

A **workflow definition** is a validated configuration describing one use
case (datasets, assets, model definitions, logical expressions, parameter
spaces, execution assumptions, output policies, research scope, alignment
and timeframe rules) — it belongs to the application and configuration
layers, not the domain model.

Every research workflow separates **Research Computation** (creates
reusable factual datasets) from **Research Analytics** (interprets stored
results). A new report, filter, ranking or family analysis must not
automatically recalculate unchanged source results.

## Which file answers which question

| Question | File |
|---|---|
| "Which research methodology should I choose, and what question does it answer?" | [`RESEARCH_METHODOLOGIES.md`](RESEARCH_METHODOLOGIES.md) — compares all six methodologies (Signal, Model, Strategy, Robustness, Predictive, Portfolio) side by side |
| "What are Signal Research's scopes, contracts, and persisted outputs?" | [`SIGNAL_RESEARCH.md`](SIGNAL_RESEARCH.md) |
| "What are Strategy Research's composition rules, simulation, and analytics?" | [`STRATEGY_RESEARCH.md`](STRATEGY_RESEARCH.md) |
| "How does Strategy Execution's runtime flow work, and what's out of scope?" | [`STRATEGY_EXECUTION.md`](STRATEGY_EXECUTION.md) |
| "How does market data get imported, validated, and published?" | [`MARKET_DATA.md`](MARKET_DATA.md) |

`RESEARCH_METHODOLOGIES.md` and the four workflow-architecture files are
deliberately not merged: the methodology file answers "which one, and why";
the architecture files answer "what exactly does this workflow do,
contract-wise". See the reciprocal pointer at the top of each file.

## Known gaps (not fixed by this sprint)

- No runbooks exist for the research side (`data fetch`, `research run`,
  `report render`) — their operator surface is documented only inside
  [`../modules/OPERATOR_CLI.md`](../modules/OPERATOR_CLI.md). See
  `SPRINT_055_T001_REFERENCE_TARGET_IA.md` §5.3.
