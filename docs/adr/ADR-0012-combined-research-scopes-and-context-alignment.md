# ADR-0012 — Combined Research Scopes and Context Alignment

## Status

ACCEPTED

## Context

Sprint 008 delivered Signal Research for scope `SIGNAL_MODEL_ONLY` (ADR-0011). Phase 5 requires
all three explicit research scopes:

```text
SIGNAL_MODEL_ONLY
MARKET_MODEL_ONLY
MARKET_AND_SIGNAL
```

Wave 0 spike (`tests/spike/run_combined_research_spike.py`) validated binding decisions in
`docs/planning/sprints/S009_WAVE0_DECISIONS.md`.

Key architectural tension: Market Model describes **context** (dense state), not signal emissions.
Research must separate:

```text
Market Model State       — dense evaluation output
MarketModelObservation   — sampling point for forward outcomes
Market Model Segment     — continuous true interval (deferred)
```

## Decision

### Explicit research scope

Every new run declares `ResearchScope`. Scope is **not** inferred from model lists.

Validation rules:

| Scope | Market models | Signal models |
|-------|---------------|---------------|
| `SIGNAL_MODEL_ONLY` | rejected | required |
| `MARKET_MODEL_ONLY` | required | rejected |
| `MARKET_AND_SIGNAL` | required | required |

Invalid combinations fail before computation.

### Market Model observation policy

Market Models do **not** receive `SignalFiringPolicy`. Research materializes observations via:

```text
MarketModelObservationPolicy.TRUE_EDGE  (false → true)
```

Dense state remains available from `evaluate_models`. Segment materialization is deferred.

### Context timing (MARKET_AND_SIGNAL)

Market Model context for each `SignalOccurrence` is evaluated at:

```text
SignalOccurrence.available_at
```

Alignment uses backward as-of semantics (latest legally available context). `detected_at` is
preserved for audit but must not drive context join.

### ContextFact invariants

MVP unique key: `occurrence_id + market_model_id`.

Fields:

```text
occurrence_id
market_model_id
context_met_at_available_at
context_evaluated_at
```

Occurrences are **not** dropped when context is false. `context_met = false` rows are retained
for conditional analytics (Sprint 010).

### One model combination per run

MVP: exactly one Market Model and one Signal Model per explicit experiment run. No implicit
Cartesian product, OR or AND composition from model lists.

### Envelope v2 layout

Schema version: `signal_research.v2`. Separate fact tables (Option A):

```text
SIGNAL_MODEL_ONLY:
    manifest.json, occurrences.parquet, outcomes.parquet

MARKET_MODEL_ONLY:
    manifest.json, observations.parquet, outcomes.parquet

MARKET_AND_SIGNAL:
    manifest.json, occurrences.parquet, context.parquet, outcomes.parquet
```

Manifest includes: `schema_version`, `research_scope`, `market_model_ids`, `signal_model_ids`,
fact table descriptors, row counts, checksums (Wave 2 implementation detail).

### Compatibility

```text
signal_research.v1  — read-only
signal_research.v2  — read/write
```

No physical `v1 → v2` migrator in Sprint 009. Immutable v1 runs are not rewritten.

### Workflow API

Keep `run_signal_research(...)`. Introduce scope-aware `SignalResearchRequest` with required
`ResearchScope`. Do **not** introduce generic `run_research(...)`.

Convenience factories: `.signal_only(...)`, `.market_only(...)`, `.market_and_signal(...)`.

### Run identity

`run_id` hash must include `research_scope`, market model identity, signal model identity, and
all Sprint 008 inputs. Changing scope changes `run_id` even when models and dataset are identical.

### Outcome semantics

Forward outcome calculator and sign conventions from ADR-0011 remain unchanged. Market model
observations attach outcomes via `observation_id` (Wave 2 schema detail).

## Consequences

### Positive

- Clear separation of market state, observations and signal occurrences,
- explicit no-look-ahead context join for combined scope,
- envelope layout supports Polars/DuckDB analytics without wide nullable tables,
- v1 runs remain readable during v2 rollout.

### Negative

- Only `TRUE_EDGE` observation policy in MVP,
- one market + one signal model per run,
- segment analysis deferred,
- outcome row key generalization (`occurrence_id` vs `observation_id`) resolved in Wave 2.

## Implementation (Sprint 009)

Implemented on sprint branch `sprint/combined-research-scopes`:

- `ResearchScope`, `SignalResearchRequest`, `ContextFact`, `MarketModelObservation`
- scope-aware `run_signal_research` for all three scopes
- envelope `signal_research.v2` with repository read/write and v1 read compatibility
- integration tests and combined research spike
- manual inspection: `tests/spike/run_inspect_combined_research.py`

## References

- `docs/planning/sprints/S009_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_009.md`
- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `tests/spike/run_combined_research_spike.py`
