# Analysis workspace — Sprint 003 design record

This preserves the original planning requirements, ADR summary and scope notes. Use the [current overview](../../reference/system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) for guidance.

## 23. Persistence Decision for Sprint 003

Sprint 003 does not implement persistent storage of derived analytical matrices.

It implements:

- execution-scoped result storage,
- in-memory exact-match cache,
- output identity,
- result assembly contract,
- optional in-memory AnalysisFrame materialization.

Persistent DerivedAnalysisDataset storage is deferred.

---

---

## 24. Model Definitions and Workspace Requests

Market Models and Signal Models do not directly manipulate workspace columns.

They declare required component outputs.

Example:

```text
MarketModelDefinition
├── EMA(20):value
├── EMA(50):value
├── ATR(14):value
├── TrendState:value
└── VolatilityState:value
```

The planner resolves these requirements into a DAG.

The executor creates the workspace.

The assembler exposes aliases required by the consumer.

Models remain declarative compositions, not active DataFrame-processing classes.

---

---

## 25. Strategy Composition

A complete strategy may require outputs from multiple domains:

```text
Market Model
× Signal Model
× Exit Model
× Risk Model
```

The execution planner should merge all requirements into one shared plan.

This enables:

- one shared AnalysisWorkspace,
- deduplicated indicators,
- shared structures and states,
- a single aligned backtest view,
- consistent lineage across the strategy.

The strategy definition must not independently calculate or append helper columns.

---

---

## 26. Debug and Research Outputs

Research workflows may request additional diagnostic outputs that are not required by production execution.

Examples:

```text
raw_signal_mask
rejection_strength
normalized_distance
component_score
condition_a
condition_b
```

These may be declared as optional debug outputs.

A component may define output groups:

```text
core outputs
diagnostic outputs
research-only outputs
```

The planner includes optional outputs only when requested.

This avoids permanently expanding every workspace while preserving research transparency.

---

---

## 27. Security and Isolation of User Components

User-defined components use the same result contract as framework components.

They must not receive unrestricted ownership of the shared workspace.

User components:

- receive declared inputs,
- return declared outputs,
- cannot overwrite canonical data,
- cannot publish undeclared columns,
- must pass output validation,
- must use explicit aliases when materialized.

This keeps plugin and `user_data` components compatible with framework-level execution guarantees.

---

---

## 28. Public Contracts

The following should become stable public contracts:

```text
AnalysisResult
OutputSchema
OutputId
OutputRef
AnalysisWorkspaceView
AnalysisFrameRequest
AnalysisFrame
AnalysisFrameAssembler
```

The following should remain internal initially:

```text
workspace physical storage
array ownership implementation
column-pruning algorithm
executor memory policy
cache storage implementation
backend conversion strategy
```

---

---

## 29. Sprint 003 Requirements

Sprint 003 should include:

- multi-output `AnalysisResult`,
- explicit `OutputSchema`,
- stable `OutputId` and `OutputRef`,
- execution-scoped `AnalysisResultStore`,
- read-only market-data input view,
- executor-controlled result registration,
- deterministic aliases for assembled views,
- collision detection,
- in-memory `AnalysisFrameAssembler`,
- integration test with a wide analytical view,
- no mutation of the source dataset.

The integration test should assemble a frame containing at least:

```text
OHLCV
True Range
ATR
Volatility State
one additional reusable feature
one diagnostic output
```

The objective is to prove that the system supports multiple public outputs and wide workflow views without using a shared mutable DataFrame as its architectural foundation.

---

---

## 30. Out of Scope for Sprint 003

The following remain outside Sprint 003:

- persistent derived-data cache,
- automatic chunking,
- partial-range cache reuse,
- column pruning implementation,
- distributed result storage,
- parallel DAG execution,
- multitimeframe alignment,
- live incremental workspace,
- full feature-store architecture,
- GPU-specific containers,
- automatic optimizer-driven backend selection.

---

---

## 31. Testing Requirements

### Contract tests

All components must be tested for:

- declared output presence,
- output length and alignment,
- input immutability,
- deterministic aliases,
- stable output identity,
- multi-output correctness,
- valid warm-up metadata,
- lineage completeness.

### Workspace tests

The workspace must be tested for:

- no source-data mutation,
- no alias collision,
- shared-result reuse,
- correct dependency injection,
- correct final-output selection,
- correct wide-frame assembly.

### Performance tests

The technical spike should measure:

- cost of adding many outputs,
- cost of repeated DataFrame concatenation versus deferred assembly,
- memory usage of map-of-arrays versus wide DataFrame,
- conversion cost for TA-Lib and pandas adapters,
- peak memory for realistic NQ 1-minute datasets.

---

---

## 32. Architectural Invariants

The following invariants are mandatory:

1. Canonical Market Data is never mutated by Market Analysis.
2. Components return outputs instead of appending columns globally.
3. Every public output has stable semantic identity.
4. Aliases are not computation identity.
5. Internal temporaries are not automatically published.
6. Models declare requirements; they do not own DataFrames.
7. The planner computes only requested outputs and dependencies.
8. Equivalent computations are deduplicated.
9. ConsumerViews are assembled explicitly.
10. Derived analytical matrices are not canonical Market Data.
11. Wide workspaces are supported but remain execution-scoped.
12. Persistent derived data requires explicit materialization and lineage.

---

---

## 33. ADR Decision

### ADR-MA-007 — Analysis Workspace and Derived Data Materialization

**Status:** Accepted for Sprint 003 planning.

**Decision:**

The framework will use individually identifiable `AnalysisResult` objects as the reusable internal representation of analytical computations. During execution, results are managed within an execution-scoped `AnalysisWorkspace` and `AnalysisResultStore`. Research, backtest, charting, export, and execution workflows may request a flat, wide `AnalysisFrame` assembled from selected market-data and analytical outputs.

The wide frame is a consumer-specific materialization, not the primary domain model and not canonical Market Data.

Components may use internal temporary arrays, but only declared outputs are published to the workspace.

**Consequences:**

Positive:

- supports strategies with dozens of helper columns,
- preserves reuse and deduplication,
- prevents uncontrolled mutation,
- separates semantic identity from column aliases,
- allows backend-specific internal representations,
- supports future memory pruning and persistent derived datasets.

Negative:

- requires explicit result assembly,
- introduces output identity and alias management,
- requires stronger executor and validation contracts,
- is more complex than directly appending columns to a DataFrame.

**Rejected alternative:**

Using one shared mutable DataFrame as the primary execution and domain model.

This alternative was rejected because it creates hidden dependencies, naming collisions, order-dependent execution, weak lineage, repeated calculations, and poor control over memory and persistence.

---

---

## 34. Summary

The framework accepts that realistic strategies require wide analytical matrices.

The adopted model is:

```text
MarketDataset
= immutable market facts

AnalysisResult
= identifiable reusable computation output

AnalysisWorkspace
= temporary wide execution environment

AnalysisFrame / ConsumerView
= explicit flat materialization for one workflow
```

The architecture does not attempt to eliminate helper columns. It ensures that they are controlled, identifiable, reusable, and materialized only where they are needed.
