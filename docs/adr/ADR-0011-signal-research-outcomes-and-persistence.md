# ADR-0011 — Signal Research Outcomes and Persistence

## Status

ACCEPTED

## Context

Sprint 008 delivers the first Signal Research computation increment with scope
`SIGNAL_MODEL_ONLY`. The workflow must connect Signal Model evaluation to persistent,
reproducible research facts without mixing strategy execution semantics.

Wave 0 spike (`tests/spike/run_signal_research_spike.py`) validated binding decisions in
`docs/planning/sprints/S008_WAVE0_DECISIONS.md`. Sprint 008 implementation added:

- `strategy/signal_occurrence.py` — occurrence facts and stable `occurrence_id`,
- `research/outcomes/` — explicit `ForwardOutcomeDefinition` and calculator,
- `research/datasets/signal_research.py` — run envelope write/read,
- `application/signal_research/run_signal_research.py` — orchestration via `evaluate_models`.

## Decision

### Domain ownership

1. **Strategy domain** owns `SignalOccurrence` — provider-independent sparse signal event
   facts. No research-only fields on the occurrence record.
2. **Research domain** owns forward outcome definition, outcome calculation and run
   persistence.
3. **Application layer** orchestrates evaluation, materialization, outcome computation and
   optional persistence. It does not expose filesystem paths to callers.

### Reference price (descriptive, not execution)

`reference_price` = evaluation-frame **close at `detected_at`**.

This is a descriptive research anchor for measuring forward behaviour. It is **not**
`fill_price`, `entry_price` or any simulated execution price.

### Forward outcome semantics

Introduce `ForwardOutcomeDefinition` before calculation. MVP binding rules:

| Field | Convention |
|-------|------------|
| Horizon | `N` full evaluation bars **after** the signal bar |
| Outcome window | bars `(t+1 … t+N]` — signal bar excluded |
| Terminal return | `close[t+N] / reference_price - 1`, direction-normalized |
| `forward_return` | signed; favourable > 0 for both LONG and SHORT |
| `mfe` | non-negative |
| `mae` | non-positive (signed adverse convention) |
| Incomplete horizon | row retained; `outcome_status = incomplete_horizon`; metrics null |
| Missing data | `outcome_status = insufficient_data`; metrics null (not zero-filled) |

### Occurrence ↔ outcome cardinality

Use **long-format** outcome facts:

```text
1 occurrence × H horizons → H outcome rows
```

Forward price paths are **not** stored in MVP — summary outcomes only.

### Run envelope and immutability

Physical layout under `storage_root`:

```text
{storage_root}/{run_id}/
├── manifest.json
├── occurrences.parquet
└── outcomes.parquet
```

Rules:

- `run_id` is deterministic from material inputs (dataset, models, horizons, range,
  framework version, outcome-definition fingerprint).
- Existing `run_id` directories must not be overwritten.
- Readers validate `schema_version` (`signal_research.v1` for MVP).
- Consumers load via `RunDatasetRef` / repository adapter — not direct path reads outside
  infrastructure and tests.

Manifest includes at minimum: `run_id`, `schema_version`, `framework_version`,
`created_at_utc`, `source_dataset_ref`, `evaluation_timeframe`, `signal_model_ids`,
`horizon_bars_requested`, `outcome_definition_fingerprint`.

### Application workflow

`run_signal_research` reuses `evaluate_models` (single analysis pass). It must not call
`run_analysis` directly or duplicate component computation.

Scope for Sprint 008 MVP: **signal models only** — Market Model conditioning deferred.

### Inspection boundary

Occurrence / forward-path inspection (T009) consumes a finished run envelope plus historical
OHLCV for chart context. It must not evaluate models, recompute outcomes or become an
analytics dashboard.

## Consequences

### Positive

- Clear separation between occurrence facts, outcome facts and run metadata,
- explicit, testable outcome semantics before calculator implementation,
- reproducible run identity and immutable persistence,
- inspection tooling validates persisted outputs without expanding domain scope.

### Negative

- MVP counts evaluation bars only — session-boundary horizon semantics deferred (PRB-007
  remainder),
- only one reference-price policy in MVP,
- analytics queries (filters, rankings, SQL) deferred to Sprint 010,
- Strategy Research dataset schema (PRB-006 remainder) still deferred.

## References

- `docs/planning/sprints/S008_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_008.md`
- `src/trading_framework/strategy/signal_occurrence.py`
- `src/trading_framework/research/outcomes/`
- `src/trading_framework/research/datasets/signal_research.py`
- `src/trading_framework/application/signal_research/run_signal_research.py`
- `tests/spike/run_signal_research_spike.py`
- `tests/spike/run_inspect_signal_research.py`
