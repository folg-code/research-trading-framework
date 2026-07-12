# Trading Research Framework

# PROBLEM_REGISTRY.md

## 1. Purpose

This registry records observed architectural, research, implementation and operational problems.

A problem is different from:

- an idea,
- a planned feature,
- a known implementation shortcut,
- an accepted architectural decision.

A problem represents a risk, inconsistency, unknown or demonstrated weakness that may require:

- research,
- design,
- an ADR,
- a bug fix,
- an epic,
- a technical-debt item.

Problems remain in this registry until resolved, rejected or explicitly converted into another tracked form.

---

## 2. Statuses

```text
OPEN
UNDER_INVESTIGATION
DECISION_REQUIRED
PLANNED
MITIGATED
RESOLVED
DEFERRED
REJECTED
```

---

## 3. Severity

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Severity reflects impact, not implementation urgency alone.

---

## 4. Problem Entry Template

```markdown
## PRB-XXX — Title

Status:
Severity:
Domain:
Owner:
Discovered:
Last Updated:

### Description

...

### Evidence

...

### Impact

...

### Possible Directions

- ...

### Decision or Resolution Criteria

- ...

### Related Documents

- ...

### Related ADRs

- ...

### Related Tasks

- ...
```

---

# 5. Active Problems

## PRB-001 — Dataset Identity Is Conceptually Defined but Not Yet Algorithmically Specified

```text
Status: MITIGATED
Severity: HIGH
Domain: Market
Owner: Unassigned
Discovered: 2026-06-19
Last Updated: 2026-06-19
```

### Description

The architecture defines dataset identity, versioning, lineage and lifecycle, but does not yet define the exact algorithm used to determine:

- logical dataset identity,
- new-version creation,
- content equality,
- checksum scope,
- partition replacement,
- semantic versus physical change.

**MVP resolution (Sprint 002 Wave 1):** `DatasetId` canonical key, monotonic integer versions per identity, `DatasetRef(dataset_id, version)`, and `DatasetVersionPolicy` material-change rules implemented in `src/trading_framework/market/datasets/`. Full partition and content-addressed semantics remain open.

### Evidence

The documentation lists material version inputs but intentionally leaves exact implementation open.

### Impact

An incorrect definition may cause:

- accidental reuse of incompatible data,
- unnecessary versions,
- mutation of published logical datasets,
- weak Research reproducibility,
- difficult partition repair.

### Possible Directions

- stable `DatasetId` for logical series plus monotonically increasing version,
- content-addressed version identity,
- manifest hash over semantic metadata and partition checksums,
- hybrid logical identity plus immutable version manifest.

### Resolution Criteria

- one deterministic identity specification,
- examples for unchanged physical rewrite,
- examples for corrected records,
- examples for changed normalization,
- explicit test cases.

### Related Documents

- `ARCHITECTURE_FOUNDATIONS.md`
- `ARCHITECTURE_TECHNICAL.md`
- `DATA_MODULE.md`

---

## PRB-002 — Component Fingerprint Algorithm Is Not Defined

```text
Status: PARTIALLY_RESOLVED (MVP)
Severity: HIGH
Domain: Market Analysis
Owner: Unassigned
Discovered: 2026-06-19
```

**MVP resolution (Sprint 003):** Parameter fingerprinting for execution identity is implemented via
`ParameterSchema.canonicalize()` → `CanonicalParameters` embedded in `ComputationIdentity`. DAG nodes
and the in-plan execution cache key on `ComputationIdentity.canonical_key()`. Full
`implementation_hash` / transitive dependency hashing for research-grade component fingerprints
remains open — see ADR-MA-003 and ADR-0010 (planned).

### Description

Working Market Analysis components require:

```text
implementation_hash
dependency_hash
resolved_parameters
```

The exact hashing boundary is not specified.

Open questions include:

- source file only or transitive local files,
- imported helper functions,
- Python version,
- framework version,
- environment dependencies,
- dynamically generated code,
- configuration defaults.

### Impact

Weak fingerprints may label non-equivalent implementations as identical.

Overly broad fingerprints may invalidate reuse too often.

### Possible Directions

- normalized source-code hash plus declared dependency fingerprints,
- package artifact hash,
- Git tree hash for controlled component directory,
- explicit component manifest.

### Resolution Criteria

- deterministic fingerprint contract,
- bounded and understandable scope,
- unit tests for meaningful changes,
- clear experimental reproducibility status.

---

## PRB-003 — Local Model Definition Fingerprints Are Not Yet Specified

```text
Status: OPEN
Severity: HIGH
Domain: Strategy
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

Mutable local Market, Signal, Exit, Risk and Strategy Models require a `definition_hash`, but canonical serialization is not defined.

### Impact

Equivalent definitions may receive different identities, or changed expression semantics may reuse stale Research results.

### Possible Directions

- canonical JSON serialization,
- sorted expression-tree representation,
- resolved defaults included in hash,
- dependency identities embedded in the manifest.

### Resolution Criteria

- canonical form for each model definition,
- stable ordering rules,
- versioned serialization schema,
- regression tests.

---

## PRB-004 — Public Discovery of `user_data` Components Needs a Safe Contract

```text
Status: OPEN
Severity: HIGH
Domain: Market Analysis / Configuration
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

The framework must load user components without `src/` importing concrete `user_data` modules.

The discovery mechanism is not selected.

### Impact

A poor design may create:

- dependency inversion violations,
- unsafe arbitrary imports,
- ambiguous duplicate component IDs,
- difficult testing,
- framework/user coupling.

### Possible Directions

- explicit entry-point configuration,
- manifest-based registry,
- controlled import paths from user configuration,
- plugin loader with public Protocol validation.

### Resolution Criteria

- no concrete user import from domain modules,
- deterministic duplicate handling,
- explicit validation,
- isolated tests,
- clear error reporting.

---

## PRB-005 — Market Analysis Result Storage Shape Is Not Fixed

```text
Status: PARTIALLY_RESOLVED (MVP)
Severity: MEDIUM
Domain: Market Analysis
Owner: Unassigned
Discovered: 2026-06-19
```

**MVP resolution (Sprint 003):** In-memory `AnalysisResult` with typed `OutputSeries`, multi-output
`OutputSchema`, lineage and warm-up metadata. Results live in `AnalysisResultStore` /
`AnalysisWorkspace` for one execution; optional `AnalysisFrame` assembly for wide consumers.
Persistent derived-dataset storage remains deferred — see ADR-MA-005 and ADR-MA-007.

### Description

Features, Structures and States have naturally different output shapes.

The framework has not selected how results should be materialized and persisted.

### Impact

A premature universal schema could:

- flatten rich structures incorrectly,
- create inefficient wide tables,
- complicate lineage,
- prevent efficient reuse.

### Possible Directions

- common metadata wrapper with type-specific payloads,
- columnar Feature and State outputs,
- event tables for Structures,
- typed in-memory results with adapter-specific persistence.

### Resolution Criteria

- one complete vertical slice,
- measured query and storage needs,
- no forced scalar representation,
- preserved temporal and component lineage.

---

## PRB-006 — Research Dataset Physical Schema Is Intentionally Undefined

```text
Status: DEFERRED
Severity: MEDIUM
Domain: Research
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

Logical content of Signal and Strategy Research Datasets is described, but physical schemas and storage formats are not fixed.

### Impact

Implementation cannot proceed past MVP storage without selecting:

- fact-table structure,
- partitioning,
- trade/event representation,
- metadata manifest,
- query engine.

### Possible Directions

- Parquet fact datasets plus metadata manifests,
- DuckDB query layer,
- Polars lazy access,
- separate raw facts and derived analytics.

### Resolution Criteria

Resolve during Phase 5 and Phase 6 using actual vertical-slice requirements.

---

## PRB-007 — Trading Calendar Implementation Is Not Selected

```text
Status: OPEN (partial MVP resolution — Sprint 005)
Severity: HIGH
Domain: Time / Market
Owner: Unassigned
Discovered: 2026-06-19
Last Updated: 2026-07-12
```

### Description

Trading Calendars are required for:

- missing-range detection,
- session boundaries,
- holidays,
- shortened sessions,
- resampling,
- futures data validation.

The contract is defined, but implementation strategy is not selected.

**Sprint 004 deferral (2026-07-12):** Multitimeframe batch resampling uses fixed UTC duration
buckets (`ResampleSpec`, Polars `group_by_dynamic`) without exchange sessions or holidays.
Documented in ADR-MA-012. Calendar-aware resampling, missing-range detection and session
boundaries remain blocked on full resolution of this problem.

**Sprint 005 partial MVP (2026-07-12):** Batch `TradingSessionResolver` protocol and
`CmeEsRthSessionResolver` (CME ES RTH: `trading_day`, `session_id`, `is_rth`) enrich
`AnalysisWorkspace` and `AnalysisFrame` via `RunAnalysisRequest.session_resolver`.
Documented in ADR-MA-013. **Not resolved:** Globex/ETH, `is_market_open`, missing-range
integration, global calendar registry, session-boundary resampling, shortened-session rules
beyond optional holiday date mask.

### Impact

Incorrect calendars can produce false data gaps and temporal errors.

### Possible Directions

- adapter around an established exchange-calendar library,
- framework-owned minimal calendar definitions,
- hybrid external library plus user overrides.

### Resolution Criteria

- provider-independent contract,
- CME support,
- DST and shortened-session tests,
- versionable holiday assumptions,
- override mechanism.

---

## PRB-008 — Bar Timestamp Convention Must Be Explicit

```text
Status: MITIGATED
Severity: HIGH
Domain: Time / Market
Owner: Unassigned
Discovered: 2026-06-19
Last Updated: 2026-06-19
```

### Description

Providers may timestamp bars by interval open, close or another convention.

The framework needs one canonical convention or explicit metadata.

**MVP resolution (Sprint 002 Wave 1):** `observed_at` = interval start (UTC), `available_at` = interval end derived from `timeframe`. Implemented in `src/trading_framework/market/temporal/bar_interval.py`.

### Impact

Ambiguity affects:

- resampling,
- `observed_at`,
- `available_at`,
- joins,
- gap detection,
- Research/runtime parity.

### Possible Directions

- canonical interval-start timestamp plus explicit end,
- canonical interval-end timestamp,
- `TimeRange` as primary bar interval identity.

### Resolution Criteria

- documented invariant,
- normalization rules,
- provider examples,
- temporal regression tests.

---

## PRB-009 — Intrabar Higher-Timeframe Semantics Need a Formal Contract

```text
Status: DEFERRED
Severity: MEDIUM
Domain: Market Analysis
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

The architecture permits explicit partial higher-timeframe components but does not define the concrete contract.

### Impact

Ad hoc implementation could create look-ahead bias or Research/live divergence.

### Possible Directions

- separate `IntrabarComponent` Protocol,
- partial-bar dataset node,
- stability and update metadata,
- strict runtime/research equivalence tests.

### Resolution Criteria

Resolve only when a real intrabar use case is implemented.

---

## PRB-010 — Initial Numeric Types Are Not Fixed

```text
Status: MITIGATED
Severity: MEDIUM
Domain: Core / Market / Execution
Owner: Unassigned
Discovered: 2026-06-19
Last Updated: 2026-06-19
```

### Description

Price, volume, quantity, PnL and money types are conceptually explicit but concrete numeric representations are not selected.

**MVP resolution (Sprint 002 Wave 1):** `Price` uses `Decimal`, `Volume` uses non-negative `int` in `src/trading_framework/core/types/`. Money, quantity and PnL remain deferred.

### Impact

Choices affect:

- precision,
- performance,
- serialization,
- provider normalization,
- order sizing,
- equality tests.

### Possible Directions

- `Decimal` for money and order quantities,
- integer ticks and fixed-point values,
- float for analytical arrays with explicit boundary conversions,
- hybrid domain and analytical representations.

### Resolution Criteria

- asset-class examples,
- serialization rules,
- performance expectations,
- clear domain/analytics boundary.

---

## PRB-011 — MarketFieldReference May Become an Architectural Bypass

```text
Status: OPEN
Severity: MEDIUM
Domain: Market Analysis / Strategy
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

`MarketFieldReference` is required for simple source-field conditions, but an overly broad API could allow models to bypass component contracts and lineage.

### Impact

Potential consequences:

- arbitrary DataFrame-like access,
- hidden transformations,
- missing temporal validation,
- model/storage coupling.

### Possible Directions

- fixed supported fields,
- explicit timeframe and dataset identity,
- no arbitrary expressions,
- reference resolution through the dependency graph.

### Resolution Criteria

- minimal immutable reference model,
- strict resolver,
- negative tests for unsupported access.

---

## PRB-012 — Research Space Planner Limits Need Initial Defaults

```text
Status: OPEN
Severity: MEDIUM
Domain: Research
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

The framework requires bounded and observable experiment spaces but has no default candidate limits or complexity constraints.

### Impact

Users may accidentally generate excessive combinations.

### Possible Directions

- configurable hard maximum candidate count,
- warning and confirmation thresholds,
- maximum model conditions,
- maximum parameter dimensions,
- preflight cost estimate.

### Resolution Criteria

- initial conservative defaults,
- explicit override,
- planner tests,
- no silent pruning.

---

## PRB-013 — Research/Runtime Parity Is Not Yet Measurable

```text
Status: OPEN
Severity: HIGH
Domain: Research / Execution
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

The architecture requires consistent model semantics between Research and Strategy Execution, but parity criteria and tests are not defined.

### Impact

A Strategy Model may behave differently in batch backtest, replay and paper execution.

### Possible Directions

- canonical decision fixtures,
- same component implementations across modes,
- parity test datasets,
- comparison of SignalOccurrences and decisions.

### Resolution Criteria

- formal parity test suite,
- accepted tolerances,
- documented differences where unavoidable.

---

## PRB-014 — Vectorized Backtest Semantics Need a Deliberately Limited MVP

```text
Status: DEFERRED
Severity: HIGH
Domain: Research
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

A batch/vectorized backtest is planned, but full order and fill semantics can quickly become equivalent to an execution simulator.

### Impact

Attempting full realism too early may create a large, ambiguous engine.

### Possible Directions

- start with bar-based deterministic fills,
- explicit unsupported scenarios,
- separate simulation assumptions,
- progressively add order types.

### Resolution Criteria

Define before Phase 6 implementation.

---

## PRB-015 — Architecture Documents Require a Formal Consistency Check

```text
Status: PLANNED
Severity: MEDIUM
Domain: Documentation / Governance
Owner: Unassigned
Discovered: 2026-06-19
```

### Description

Several architecture documents were updated iteratively and may retain:

- old terminology,
- duplicate text,
- numbering inconsistencies,
- stale directory examples,
- inconsistent cross-references.

### Impact

AI agents and contributors may follow conflicting instructions.

### Possible Directions

- scripted terminology scan,
- manual cross-document review,
- architecture index with authoritative ownership,
- documentation tests for key terms.

### Resolution Criteria

- no deprecated `Technical Analysis` references except historical explanation,
- consistent Strategy Execution naming,
- consistent model composition,
- valid heading numbering,
- consistent file references.

---

## PRB-016 — ADR History Has Not Yet Been Materialized

```text
Status: MITIGATED
Severity: MEDIUM
Domain: Governance / Architecture
Owner: Unassigned
Discovered: 2026-06-19
Last Updated: 2026-06-19
```

### Description

Accepted decisions are recorded in consolidated architecture documents, but individual ADR files do not yet exist.

ADR-0001 through ADR-0003 were materialized in Sprint 001. ADR-0004 through ADR-0010 remain planned.

### Impact

The current state is documented, but decision history, alternatives and consequences are harder to audit.

### Possible Directions

Create initial ADR set from accepted decisions.

### Resolution Criteria

- numbered ADRs,
- accepted status,
- rationale and alternatives,
- cross-references from architecture documents.

---

# 6. Resolved Problems

No problems have yet been formally moved to `RESOLVED`.

When resolving a problem:

- preserve the original description,
- record the resolution date,
- link the ADR or task,
- describe remaining limitations.
