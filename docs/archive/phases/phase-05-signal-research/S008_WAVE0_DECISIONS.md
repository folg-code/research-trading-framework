# Sprint 008 — T001 Signal Research Spike and Architecture Decisions

## Metadata

```text
Task: S008-T001
Sprint: 008 — Signal Research Computation MVP
Status: DONE (2026-07-12)
Branch: sprint/signal-research-mvp--wave0-decisions
Spike script: tests/spike/run_signal_research_spike.py
Direction: docs/planning/sprints/SPRINT_008.md
Depends on: SPRINT_006 merged to main (2026-07-12)
Scope: SIGNAL_MODEL_ONLY (first increment)
```

---

## 1. Spike objective

Validate the pipeline boundary between **Signal Model emissions** and **persistent research
outputs** before Wave 1 contracts:

```text
evaluate_models → signal_model_emissions (Polars)
    ↓
SignalOccurrence table (sparse occurrence facts)
    ↓
ForwardOutcome table (long-format outcome facts)
    ↓
run envelope: manifest + occurrences.parquet + outcomes.parquet
    ↓
repository read-back (round-trip)
```

Run (planned):

```bash
uv run python tests/spike/run_signal_research_spike.py
uv run python tests/spike/run_signal_research_spike.py --json
```

Spike uses canonical Sprint 006 models and committed market-data fixtures — no new components.

---

## 2. Scope gate — Sprint 007 skipped

Per `PHASE_4_5_SPRINT_DIRECTION.md` §3, the minimum component set for the first experiment is
already on `main`:

| Requirement | Status on main |
|-------------|----------------|
| Feature (ATR / EMA) | ✅ ATR, EMA, Volatility State |
| Structure (Pivot + HH/HL/LH/LL) | ✅ `structure.swing` |
| State (Volatility State) | ✅ `volatility.state` |
| One Signal Model | ✅ canonical examples |

**Decision D-S008-01:** Skip Sprint 007 for the first Signal Research experiment. Revisit 007
only when a concrete research question requires slope, Session Range, or Trend State.

---

## 3. SignalOccurrence ownership

Vision docs place **`SignalOccurrence` in the Strategy Domain** — a provider-independent artifact
produced by Signal Model evaluation.

Research may attach experiment metadata and forward outcomes but must not redefine core occurrence
semantics.

**Decision D-S008-02:** Introduce `strategy/signal_occurrence.py` with the core occurrence record /
Polars schema. Research domain owns outcome calculation and dataset persistence only.

**Decision D-S008-03:** Each occurrence carries a stable **`occurrence_id`** — deterministic within
a run (e.g. hash of `signal_model_id`, `detected_at`, `direction`). Required for outcome joins and
inspection selection.

---

## 4. Reference price policy (not execution price)

Sprint 008 studies **signal behaviour**, not strategy execution.

```text
reference_price  — descriptive research anchor
fill_price       — out of scope
entry_price      — out of scope (do not use this term in Sprint 008)
```

**Decision D-S008-04:** `reference_price` = **evaluation-frame close at `detected_at`**, provided
the signal is legally available on that evaluation grid row.

Rationale: `detected_at` is the evaluation-grid timestamp where the condition/emission is observed.
This is a **descriptive reference price** for measuring forward behaviour — not a simulated entry
fill.

When `available_at > detected_at` (e.g. state-edge signals), both timestamps are preserved on the
occurrence; outcome calculation still anchors to `reference_price` at `detected_at` per MVP policy.
Spike must confirm this on `ON_TRUE_EDGE` vs `ON_EVENT` canonical models.

**Decision D-S008-05:** Document explicitly in ADR and module docs that `reference_price ≠ fill_price`.

Alternative policies (`close at available_at`, `next-bar open`, mid-price) are deferred — may become
`ReferencePricePolicy` enum values later, but MVP uses one binding policy only.

---

## 5. Forward outcome definition (before calculator)

Outcome semantics must be **explicit and testable** before implementation.

**Decision D-S008-06:** Introduce `ForwardOutcomeDefinition` in `research/outcomes/`:

```python
@dataclass(frozen=True, slots=True)
class ForwardOutcomeDefinition:
    horizon_bars: int
    reference_price_policy: ReferencePricePolicy  # MVP: CLOSE_AT_DETECTED_AT
    terminal_price_field: MarketField             # MVP: CLOSE
    excursion_high_field: MarketField             # MVP: HIGH
    excursion_low_field: MarketField              # MVP: LOW
    incomplete_horizon_policy: IncompleteHorizonPolicy  # MVP: EMIT_WITH_STATUS
```

Calculator implementation (T004) consumes this definition — no magic constants in calculator body.

### Horizon semantics (binding)

**Decision D-S008-07:** `horizon_bars = N` means **N full evaluation bars after the signal bar**.

```text
Signal bar index:     t
Outcome window:       (t+1, t+2, …, t+N)  — signal bar excluded
Terminal return:      close[t+N] / reference_price - 1
MFE / MAE window:     same (t+1 … t+N)
```

Examples:

- `horizon_bars=5` → terminal close is the close of the **5th bar after** the signal bar.
- Signal bar is **never** included in MFE/MAE excursion window.

**Decision D-S008-08:** Outcome measurement starts from the **signal observation point**
(`detected_at` grid row). This is research observation semantics — not a simulated execution delay.
`available_at` is preserved for temporal audit but does not shift the outcome window in MVP.

### Direction normalization (binding)

**Decision D-S008-09:** Signed convention — consistent across LONG and SHORT:

```text
forward_return:  signed, direction-normalized (favourable > 0, adverse < 0)
mfe:             non-negative  (max favourable excursion; clamped to >= 0)
mae:             non-positive  (worst adverse excursion — signed; clamped to <= 0)
```

When no adverse move occurs in the window, `mae = 0.0`. Do **not** mix signed MAE with magnitude
MAE in later analytics.

LONG example: price rises → `forward_return > 0`, `mfe > 0`, adverse dip → `mae ≤ 0`.  
SHORT: signs inverted consistently so favourable downward moves yield `forward_return > 0`.

### Incomplete horizon (binding)

**Decision D-S008-10:** When `t+N` exceeds available data:

```text
outcome_status = INCOMPLETE_HORIZON
forward_return, mfe, mae = null
row retained — not dropped, not zero-filled
```

Additional statuses (spike/T005):

```text
COMPLETE            — full horizon available
INCOMPLETE_HORIZON  — run ended before t+N
INSUFFICIENT_DATA   — missing OHLCV in window (gaps)
```

**Decision D-S008-11:** Session boundaries — MVP counts **evaluation bars only**; does not stop at
RTH close. Document as known limitation (PRB-007 remainder).

---

## 6. Occurrence ↔ outcome relationship

**Decision D-S008-12:** Outcome rows are **not** 1:1 with occurrences when multiple horizons are
requested.

```text
1 occurrence × H horizons → H outcome rows (long format)
```

**Decision D-S008-13:** Use **long format** — not wide (`return_5`, `return_10`, …).

| Approach | MVP choice |
|----------|------------|
| Wide columns per horizon | ❌ deferred |
| Long: `(occurrence_id, horizon_bars, metrics…)` | ✅ binding |

Benefits: add horizons without schema migration; natural grouping; DuckDB-friendly later.

**Decision D-S008-14:** Forward price **paths** are **not stored** in MVP. Only summary outcomes
(terminal return, MFE, MAE). Inspection (T009) may reconstruct a path visually from market data +
occurrence metadata — not from persisted path columns.

---

## 7. Research dataset envelope

### Logical model

Two fact tables + manifest — not one denormalized mega-table.

**Occurrence facts** (`occurrences.parquet`):

```text
occurrence_id
signal_model_id
detected_at
available_at
direction
reference_price
instrument
evaluation_timeframe
source_dataset_ref
```

**Outcome facts** (`outcomes.parquet`):

```text
occurrence_id
horizon_bars
outcome_status
terminal_price
forward_return
mfe
mae
```

### Physical layout

**Decision D-S008-15:** Run envelope directory:

```text
{storage_root}/{run_id}/
├── manifest.json
├── occurrences.parquet
└── outcomes.parquet
```

`manifest.json` includes at minimum:

```text
run_id
schema_version
framework_version
created_at_utc
source_dataset_ref
evaluation_timeframe
signal_model_ids
horizon_bars_requested
outcome_definition_fingerprint
```

**Decision D-S008-16:** Resolve partial **PRB-006** for Signal Research MVP only. Strategy
Research dataset schema remains deferred.

---

## 8. Dataset repository — write and read (T006)

**Decision D-S008-17:** T006 delivers **writer and reader** — not writer alone.

Minimal API (exact naming TBD in implementation):

```text
SignalResearchDatasetRepository.write(envelope) → RunDatasetRef
SignalResearchDatasetRepository.read(run_id | ref) → SignalResearchRunEnvelope
```

Or functional equivalents:

```text
write_signal_research_run(...)
load_signal_research_run(...)
```

Required behaviour:

```text
load by run_id or research DatasetRef
schema version validation on read
immutability check — refuse overwrite of existing run_id
round-trip tested
physical paths hidden from application/analytics consumers
```

Not in MVP: DuckDB, filters, SQL, advanced query API (Sprint 010 boundary).

---

## 9. Application workflow

**Decision D-S008-18:** New use case `run_signal_research` in `application/signal_research/`:

```text
RunSignalResearchRequest
  dataset_ref, timeframe, requested_range, storage_root
  signal_models
  outcome_definition: ForwardOutcomeDefinition  # or horizon_bars + MVP defaults
  evaluation_timeframe (optional)
  experiment_id (optional)

RunSignalResearchResult
  run_id
  occurrences: pl.DataFrame
  outcomes: pl.DataFrame
  run_ref: RunDatasetRef          # not raw Path exposed to callers
  evaluate_models_result (optional debug)
```

Orchestration reuses `evaluate_models` — no duplicate `run_analysis`.

Scope: **`SIGNAL_MODEL_ONLY`** — no Market Model conditioning in Sprint 008.

---

## 10. Determinism and run identity

**Decision D-S008-19:** Same material inputs:

```text
published dataset identity
signal model definition identity
ForwardOutcomeDefinition
framework version
evaluation timeframe + requested range
```

must yield the same **`run_id`** (or deterministic content hash recorded in manifest). Repository
must detect duplicate write to same `run_id` and refuse overwrite.

---

## 11. Package layout (proposed)

```text
src/trading_framework/
├── strategy/
│   └── signal_occurrence.py           # occurrence schema + materialization + occurrence_id
├── research/
│   ├── outcomes/
│   │   ├── definition.py              # ForwardOutcomeDefinition, policies, statuses
│   │   └── calculator.py              # MFE / MAE / return from definition + frame
│   └── datasets/
│       └── signal_research.py         # manifest, write, read, schema validation
└── application/signal_research/
    └── run_signal_research.py         # orchestration
```

Infrastructure Parquet patterns follow Sprint 002 conventions — separate schema from market OHLCV.

---

## 12. Inspection increment (T009)

Validation tooling only — consumes finished run envelope via repository read.

Must show:

```text
selected occurrence
price window before/after event
detected_at marker
available_at marker
reference_price horizontal level
horizon end marker
MFE / MAE levels
terminal outcome annotation
```

Must **not** become: dashboard server, multi-model comparison, rankings, filters, statistical tests.

**Decision D-S008-20:** finplot may be used as an **optional inspection adapter** in spike/user
space — not imported by domain or application workflow.

---

## 13. ADR scope (T010)

ADR must answer (not only implementation details):

| Question | MVP answer |
|----------|------------|
| SignalOccurrence ownership | Strategy domain |
| Occurrence vs research dataset boundary | Two fact tables + manifest |
| `reference_price` meaning | Close at `detected_at`; descriptive, not fill |
| Forward return definition | `close[t+N] / reference_price - 1`, direction-normalized |
| MFE / MAE window | `(t+1 … t+N]`, signal bar excluded |
| Horizon meaning | N full bars after signal bar |
| Occurrence:outcome cardinality | 1:N when multiple horizons |
| Schema shape | Long format |
| Null / incomplete outcomes | Retained with explicit `outcome_status` |
| Forward path storage | Not persisted; summary only |
| Persistence identity | `run_id` + manifest fingerprints |
| Immutability | No overwrite of existing run |

---

## 14. Spike results

Environment: Polars runtime dependency, Python **3.12**, framework **0.1.0**.

Run:

```bash
uv run python tests/spike/run_signal_research_spike.py
uv run python tests/spike/run_signal_research_spike.py --json
```

| Check | Result |
|-------|--------|
| Horizon excludes signal bar (synthetic) | PASS |
| Incomplete horizon status (synthetic) | PASS |
| `higher_low` emissions non-empty (50 events) | PASS |
| Stable unique `occurrence_id` | PASS |
| `reference_price` = close at `detected_at` | PASS |
| Long-format multi-horizon (5 + 10) | PASS |
| MFE ≥ 0, MAE ≤ 0 on COMPLETE rows | PASS |
| Incomplete rows retain null metrics | PASS |
| Write → read round-trip | PASS |
| Immutability (refuse overwrite) | PASS |

Spike confirms binding decisions D-S008-01 … D-S008-19 for Wave 1 implementation.

Resolved questions:

1. ✅ `reference_price` — close at `detected_at` index on evaluation grid.
2. ✅ Overlapping signals — independent occurrence/outcome rows.
3. ✅ E2E model — `higher_low_long` → 50 emissions on fixture.
4. ✅ `occurrence_id` — SHA-256 truncated hash of model + detected_at + direction.
5. ⏭ `ON_TRUE_EDGE` — no emissions in fixture window; cover in integration test.

---

## 15. Non-goals (Sprint 008)

```text
MARKET_MODEL_ONLY / MARKET_AND_SIGNAL scopes (Sprint 009)
Analytics on stored datasets without recompute (Sprint 010)
Experiment Cartesian expansion
Rankings, sample-size filters, statistical tests
fill_price / entry_price / execution simulation
Stored forward price paths
Direct path reads by consumers
DuckDB / query layer
Production dashboard
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial Wave 0 draft |
| 2026-07-12 | Wave 0 spike complete — 15/15 checks PASS |
