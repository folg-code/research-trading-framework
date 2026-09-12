# Sprint 006 — T001 Model Expression Spike and Architecture Decisions

## Metadata

```text
Task: S006-T001
Sprint: 006 — Declarative Market Model and Signal Model MVP
Status: DONE (2026-07-12)
Branch: sprint/declarative-models--wave0-decisions
Spike script: tests/spike/run_model_expression_spike.py
Direction: docs/planning/sprints/SPRINT_006.md
Depends on: SPRINT_005 merged to main (2026-07-12)
```

---

## 1. Spike objective

Validate the technical boundary between **Market Analysis** and **model expression evaluation**
before Wave 1 contracts:

```text
AnalysisFrame (aligned operands on evaluation grid)
    → Polars adapter (single boundary conversion)
    → three-valued boolean evaluation
    → ON_TRUE_EDGE / ON_EVENT firing on sample series
```

Run:

```bash
uv run python tests/spike/run_model_expression_spike.py
uv run python tests/spike/run_model_expression_spike.py --json
```

---

## 2. Spike results

Environment: Polars **1.42.1** (runtime dependency), Python **3.12**.

| Check | Result |
|-------|--------|
| `AnalysisFrame` → `pl.DataFrame` adapter | PASS |
| NaN preserved as null operand | PASS |
| Three-valued `AND` / `OR` / `NOT` | PASS |
| `Compare` with null operand → null | PASS |
| `ON_TRUE_EDGE` on dense condition series | PASS |
| `ON_EVENT` on sparse event series | PASS |
| Null rows do not emit | PASS |

---

## 3. ComponentOutputRef vs ComponentOutputReference

### Existing type (`market_analysis`)

`ComponentOutputRef` (`component_id`, `parameters`, `output_id`) links **component DAG
dependencies** inside Market Analysis. It does **not** include `computation_timeframe`.

### Model-layer type (new)

Introduce **`ComponentOutputReference`** in `model_expression/references.py`:

```python
@dataclass(frozen=True, slots=True)
class ComponentOutputReference:
    component_id: ComponentId
    parameters: CanonicalParameters
    output_id: OutputId
    computation_timeframe: Timeframe | None = None
    alias: str | None = None
```

| Field | Purpose |
|-------|---------|
| `computation_timeframe` | MTF identity for dependency extraction and frame column resolution |
| `alias` | Optional stable frame column name; default from assembler `default_alias` rules |

**Do not** rename or duplicate `ComponentOutputRef`. The model reference maps to:

```text
ComponentRequest          — for ExpressionDependencyExtractor / run_analysis
AnalysisFrameColumnSpec   — for AnalysisFrameAssembler request building
frame column key          — via alias or default_alias(computation_identity, output_id)
```

---

## 4. MarketFieldReference (MVP)

```python
class MarketField(StrEnum):
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"

@dataclass(frozen=True, slots=True)
class MarketFieldReference:
    field: MarketField
```

Frame resolution: column name equals `field.value` on the evaluation grid (same names as
`AnalysisFrameRequest.market_fields`).

Forbidden in MVP: shift, rolling, arbitrary names, Polars/lambda/repository access (PRB-011).

---

## 5. Package layout and dependency direction

```text
src/trading_framework/
├── model_expression/          # shared AST, references, validation, frame adapter, evaluate
├── market_model/              # MarketModelDefinition, MarketModelEvaluator, results
├── signal_model/              # SignalModelDefinition, firing, evaluators, results
└── application/model_evaluation/
    └── evaluate_models.py     # dependency extraction + run_analysis orchestration
```

| Package | May import | Must not import |
|---------|------------|-----------------|
| `model_expression` | `core`, MA **types** (`ComponentId`, `OutputId`, `AnalysisFrame`, …) | `application`, `strategy`, storage |
| `market_model` | `model_expression` | `signal_model`, `strategy`, `run_analysis` |
| `signal_model` | `model_expression` | `market_model`, `strategy`, `run_analysis` |
| `application/model_evaluation` | MA application, all model packages | — |

**Market Model and Signal Model are not Strategy.** Vision paths under `strategy/market_models/`
are superseded for implementation (reconcile in S006-T025 ADR).

---

## 6. AnalysisFrame adapter boundary

Single conversion module: `model_expression/evaluation/frame_adapter.py`.

```text
analysis_frame_to_polars(frame, column_keys) -> pl.DataFrame
```

Output columns:

```text
timestamp          — from frame.timestamps (UTC)
available_at       — derived per row from evaluation_timeframe + timestamp
<operand columns>  — float64; NaN means null operand
```

**Rule:** Polars appears only **inside** `model_expression/evaluation/` and result
materialization helpers — never in model definition dataclasses.

`available_at` derivation uses existing bar interval helpers (`derive_bar_interval` /
evaluation timeframe from run context). Operands on an aligned frame are already temporally
legal at each row; model row `available_at` = operand `available_at` max (MVP: all equal per
evaluation bar when frame is assembled correctly).

---

## 7. Expression AST (minimal)

Frozen dataclasses in `model_expression/expressions.py`:

```text
ReferenceExpression     — wraps ComponentOutputReference | MarketFieldReference
CompareExpression       — reference + operator + literal (bool | float)
AndExpression / OrExpression / NotExpression
```

| Constraint | Value |
|------------|-------|
| Max tree depth | **8** |
| Serialization | dataclass structure (JSON/YAML deferred) |
| Custom nodes | rejected at validation |

Comparison operators MVP: `EQ`, `NE`, `GT`, `GE`, `LT`, `LE` for numeric; `EQ`/`NE` for bool.

---

## 8. Three-valued null semantics

Null operand = **NaN** in frame float columns.

| Operation | Semantics |
|-----------|-----------|
| Compare with null operand | null |
| `false AND null` | false |
| `true AND null` | null |
| `true OR null` | true |
| `false OR null` | null |
| `NOT null` | null |
| Firing on null | no emission |

Implementation: explicit nullable bool column in Polars (`Boolean` with nulls), not coercing
NaN → false before logic.

---

## 9. Signal condition vs firing

| Stage | Output | Density |
|-------|--------|---------|
| `SignalModelEvaluator` | `SignalModelConditionResult` | dense (`condition_met`) |
| `SignalFiringPolicy` | `SignalEmissionResult` | sparse |

Policies MVP:

| Policy | Rule |
|--------|------|
| `ON_TRUE_EDGE` | emit when previous is false/null and current is true |
| `ON_EVENT` | emit where condition is true and operand is event-shaped (sparse 1.0) |

Deferred: `EACH_TRUE_BAR`.

`SignalDirection`: `LONG`, `SHORT`, `NEUTRAL` — **explicit** on `SignalModelDefinition`.

Do **not** name sparse emissions `SignalOccurrence` until Sprint 008 research payload.

---

## 10. Result shapes (Polars)

### MarketModelResult

```text
timestamp, available_at, market_model_id, model_result (bool, nullable)
```

### SignalModelConditionResult

```text
timestamp, available_at, signal_model_id, condition_met (bool, nullable)
```

### SignalEmissionResult

```text
detected_at, available_at, signal_model_id, direction, firing_policy
```

Materialization helpers live in `market_model/results.py` and `signal_model/results.py`.

---

## 11. Orchestration boundary

```text
ExpressionDependencyExtractor   — domain (model_expression/dependencies.py)
evaluate_models               — application (orchestrates run_analysis once)
MarketModelEvaluator          — domain; input = AnalysisFrame + definition
SignalModelEvaluator          — domain; input = AnalysisFrame + definition
```

Domain evaluators **must not** call `run_analysis`, resample, or align.

---

## 12. Binding decisions for Wave 1+

| # | Decision |
|---|----------|
| D-S006-01 | **`ComponentOutputReference`** is model-layer; **`ComponentOutputRef`** stays MA DAG-only. |
| D-S006-02 | **`MarketFieldReference`** MVP = canonical OHLCV on evaluation grid only. |
| D-S006-03 | Packages **`model_expression/`**, **`market_model/`**, **`signal_model/`** — not `strategy/`. |
| D-S006-04 | **Single Polars boundary** at `AnalysisFrame` adapter inside `model_expression/evaluation/`. |
| D-S006-05 | **Three-valued null** via NaN/nullable bool; null never fires. |
| D-S006-06 | **Signal condition** dense; **firing** sparse via explicit `SignalFiringPolicy`. |
| D-S006-07 | **`SignalDirection`** static on definition; no inference from component semantics. |
| D-S006-08 | **Max expression depth = 8**; unknown references fail at validation. |
| D-S006-09 | **`available_at`** derived on frame adapter; model row = max operand availability. |
| D-S006-10 | **Shared `run_analysis`** in application; deduplicated `ComponentRequest` set. |
| D-S006-11 | Task branches use **`sprint/declarative-models--<task-slug>`** (Git ref collision with sprint branch name). |
| D-S006-12 | **Architecture Simplification Checklist §5** — PASS (see spike JSON `checklist`). |

---

## 13. Architecture Simplification Checklist (§5)

| Item | Spike assessment |
|------|------------------|
| 5.1 Polars-first batch mapping | PASS — evaluation and results use Polars DataFrames |
| 5.2 No new global mutable state | PASS — evaluators are pure over frame input |
| 5.3 No speculative infrastructure | PASS — no persistence, no strategy layer |
| 5.4 Reuse MA frame path | PASS — consumes `AnalysisFrame`, no parallel compute |
| 5.5 Domain boundary preserved | PASS — model layer does not import storage/providers |

---

## 14. Wave 1 entry criteria

- [x] Spike PASS
- [x] Binding decisions D-S006-01 … D-S006-12 recorded
- [ ] PR merged to `sprint/declarative-models`

Next tasks: **S006-T002–T006** (references, expressions, validation, dependency extraction).

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial Wave 0 spike and binding decisions |
