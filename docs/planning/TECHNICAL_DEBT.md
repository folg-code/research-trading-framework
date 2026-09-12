# Trading Research Framework

# TECHNICAL_DEBT.md

## 1. Purpose

This register records known implementation debt that has been consciously accepted.

Technical debt is different from:

- an unresolved architectural problem,
- an unvalidated idea,
- a bug that violates expected behaviour,
- intentionally deferred future functionality.

An item belongs here only when:

1. a simpler or incomplete implementation is consciously accepted,
2. the limitation is understood,
3. the current system may still operate correctly within documented boundaries,
4. future remediation cost or risk is known.

Because the project is currently pre-implementation, this register initially contains mostly planned debt boundaries and no large body of accumulated code debt.

---

## 2. Statuses

```text
ACCEPTED
PLANNED_REPAYMENT
IN_PROGRESS
REPAID
OBSOLETE
```

---

## 3. Priority

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Priority reflects repayment importance.

---

## 4. Debt Entry Template

```markdown
## TD-XXX — Title

Status:
Priority:
Domain:
Introduced:
Target Review:
Owner:

### Accepted Shortcut

...

### Reason

...

### Consequences

...

### Safe Operating Boundary

...

### Repayment Trigger

...

### Repayment Direction

...

### Related Problems

- ...

### Related Tasks

- ...
```

---

# 5. Accepted Technical Debt

Read one item by ID. Full entries are grouped below; stable ID headings remain here for existing links.

## TD-001 — Architecture Decisions Are Consolidated Before Individual ADR Files Exist
[Full entry](registries/td-001-004.md#td-001).

## TD-002 — Planning State Is Maintained in Markdown Before GitHub Project Setup
[Full entry](registries/td-001-004.md#td-002).

## TD-003 — Initial Market Analysis Module Uses a Minimal Directory Structure
[Full entry](registries/td-001-004.md#td-003).

## TD-004 — Version 1 Keeps Position Sizing Inside the Risk Model
[Full entry](registries/td-001-004.md#td-004).

## TD-005 — Version 1 Uses an In-Memory Event Bus
[Full entry](registries/td-005-008.md#td-005).

## TD-006 — Historical Storage Uses Local Parquet Before a Dedicated Data Platform
[Full entry](registries/td-005-008.md#td-006).

## TD-007 — Initial Trading Calendar May Wrap an External Library
[Full entry](registries/td-005-008.md#td-007).

## TD-008 — Initial Research Planner Uses Conservative Static Limits
[Full entry](registries/td-005-008.md#td-008).

## TD-009 — Initial Strategy Backtest Supports a Limited Fill Model
[Full entry](registries/td-009-012.md#td-009).

## TD-010 — Documentation Consistency Is Reviewed Manually Before Automation
[Full entry](registries/td-009-012.md#td-010).

## TD-011 — Historical Query Returns List of MarketBar Objects
[Full entry](registries/td-009-012.md#td-011).

## TD-012 — Decimal OHLCV in Market Data with float64 Analysis Conversion
[Full entry](registries/td-009-012.md#td-012).

## TD-013 — Multi-Implementation Registry Before Second Backend
[Full entry](registries/td-013-016.md#td-013).

## TD-014 — Separate ResultStore, Workspace and In-Plan ExecutionCache
[Full entry](registries/td-013-016.md#td-014).

## TD-015 — AnalysisDataView Map-of-Arrays Instead of Columnar Frame
[Full entry](registries/td-013-016.md#td-015).

## TD-016 — ComponentId and ImplementationId Dual Identity Axis
[Full entry](registries/td-013-016.md#td-016).

## TD-017 — Signal / Market Research Occurrence and Outcome Materialization Is Row-Wise Python
[Full entry](registries/td-017-020.md#td-017).

## TD-018 — Robustness Child Runs Re-Execute Full Strategy Research Without Shared Evaluation
[Full entry](registries/td-017-020.md#td-018).

## TD-019 — Databento Contract Import Chunk Buffers Use Python Lists
[Full entry](registries/td-017-020.md#td-019).

## TD-020 — Continuous Trades Materialize Pays Per-Session Write + String Price Schema
[Full entry](registries/td-017-020.md#td-020).

## TD-021 — Predictive Research Has No Model Registry
[Full entry](registries/td-021-024.md#td-021).

## TD-022 — Fitted Predictive Artifacts Are Opaque and Not Portable
[Full entry](registries/td-021-024.md#td-022).

## TD-023 — Binance Historical Import Only Works for 1m
[Full entry](registries/td-021-024.md#td-023).

## TD-024 — CLI Import Boundary Is Module-Level, Not Symbol-Level
[Full entry](registries/td-021-024.md#td-024).

## TD-025 — Boundary Test Is Structurally Blind to Dynamically Loaded Strategy Files
[Full entry](registries/td-025-028.md#td-025).

## TD-026 — EquityPercentRiskModel Is Static, Authoring-Time Sizing Only
[Full entry](registries/td-025-028.md#td-026).

## TD-027 — Robustness Delay Stress Rejects Bracket Exits
[Full entry](registries/td-025-028.md#td-027).

## TD-028 — No Independent Reference Implementation for the Bracket Kernel
[Full entry](registries/td-025-028.md#td-028).

## TD-029 — Tree and Neural Predictive Model Promotion Is Deferred to a Version-Pinned Joblib Path
[Full entry](registries/td-029-031.md#td-029).

## TD-030 — Root `.gitignore` Does Not Cover Nested `<subdir>/user_data/` Directories
[Full entry](registries/td-029-031.md#td-030).

## TD-031 — No Loader Turns a Declared `signal_model_file` Into a `SignalModelDefinition`
[Full entry](registries/td-029-031.md#td-031).

## TD-032 — No CLI Support for `CandidateSetSpec` (Tree-Family Predictive Runs)
[Full entry](registries/td-032-034.md#td-032).

## TD-033 — Verdict Rule Thresholds and the Primary-Metric Convention Are Independently Triplicated
[Full entry](registries/td-032-034.md#td-033).

## TD-034 — Public Dashboard Projection Is a Monolithic JSON Bundle
[Full entry](registries/td-032-034.md#td-034).

# 6. Planned Debt Boundaries

The following shortcuts may be accepted later but are not yet introduced:

```text
- limited provider set,
- limited asset-class coverage,
- bar-only OHLCV market facts (Phase 2A; trades/quotes/options are Phase 2C–2D),
- local-only research execution,
- no UI,
- no distributed task scheduler,
- no live multi-account support,
- no automatic ML model registry (accepted as TD-021 in Sprint 040),
- no portability guarantee for fitted model artifacts (accepted as TD-022 in Sprint 040).
```

They should become technical-debt entries only when implementation consciously relies on them and repayment conditions are known.

## Phase 10 — Predictive Research (accepted in Sprint 040)

The two shortcuts below were planned before S039 and became live when S040 persisted
run envelopes. Numbered entries: **TD-021** (no model registry, MEDIUM) and
**TD-022** (opaque fitted blobs, LOW). Restated here so S041–S044 do not treat
them as oversights.

### No model registry (TD-021)

Predictive runs are addressed by content fingerprint under
`research/predictive_research/runs/{run_id}/`. There is no registry, no promotion workflow and no
model lifecycle state.

**Repayment trigger:** promoting a trained model to a Market Analysis component (IDEA-014), which
requires an addressable, durable artifact store. Sprint 044 ADR-0024 decides whether a
content-addressed store suffices or a registry is genuinely required.

### Fitted artifacts are not portable (TD-022)

The durable facts of a run are `predictions.parquet` and `metrics.json`. The fitted model is stored
as an opaque blob tagged with library name and version, and the framework promises nothing about
loading it after a library upgrade. Reproduction re-fits from the manifest instead.

**Consequence accepted:** a run whose library version is no longer installable can be read and
analyzed but not re-fitted identically. Fingerprints make this visible rather than silent.

**Repayment trigger:** the same as above — model promotion, or a demonstrated need to inspect old
artifacts. Repayment means choosing a serialization format with a stability guarantee, not adding a
registry.

---

# 7. Debt Review Rules

Review technical debt:

- at sprint retrospectives,
- before phase completion,
- before introducing related abstractions,
- when a repayment trigger occurs,
- when a debt item becomes a correctness risk.

A debt item must move to `PROBLEM_REGISTRY.md` or a bug when it begins violating expected behaviour or safety.

Do not use technical debt as a label for every unfinished feature.
