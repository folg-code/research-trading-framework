# ADR-MA-013 — CME ES RTH Session Resolution and Swing Structure MTF Projection

## Status

ACCEPTED

## Context

Sprint 004 delivered batch multitimeframe (MTF) analysis with fixed UTC resampling and
`LAST_CLOSED_BAR` alignment for continuous indicator outputs (ADR-MA-012). Exchange session
semantics remained deferred (PRB-007).

Sprint 005 adds:

1. **Batch session resolution** for CME ES regular trading hours (RTH) on the analysis path.
2. **`structure.swing`** — neutral swing structure with explicit event/state outputs and
   higher/lower classification (replacing legacy pivot naming in the spike).
3. **Per-output MTF alignment policy** — stateful levels vs sparse event flags require different
   projection onto a finer evaluation grid.

Requirements:

- no per-bar Python calendar loops in the hot path,
- lookahead-free swing confirmation on the detection bar only,
- Sprint 004 MTF resample/align path unchanged for existing indicators,
- visual and automated verification of temporal semantics.

Decision inputs: `S005_CALENDAR_SPIKE_AND_DECISIONS.md`, `S005_SWING_STRUCTURE_CONTRACT.md`,
Sprint 004 MTF spike (T001).

## Decision

### 1. Trading session resolver (CME ES RTH MVP)

Introduce `TradingSessionResolver` in `time/sessions/`:

```python
class TradingSessionResolver(Protocol):
    def resolve(self, timestamps: pl.Series) -> pl.DataFrame: ...
```

MVP implementation: `CmeEsRthSessionResolver`.

| Output column | Meaning |
|---------------|---------|
| `timestamp` | input UTC instant (unchanged) |
| `trading_day` | calendar date in `America/New_York` |
| `session_id` | `ES_RTH` or `OUTSIDE_RTH` |
| `is_rth` | `True` when weekday and 09:30 ≤ NY time < 16:00 |

Optional `holiday_dates: frozenset[date]` masks weekdays that would otherwise qualify as RTH.

**Explicitly not in MVP:**

- CMES Globex / ETH availability,
- `is_market_open` for 24h ES,
- session-boundary resampling,
- missing-range detection integration,
- global calendar registry or holiday administration UI.

Batch Polars mapping is mandatory; per-bar Python loops are spike-only.

Enrichment path: `RunAnalysisRequest.session_resolver` → `TradingSessionMetadata.resolve()`
→ attached to `AnalysisWorkspace` and `AnalysisFrame.session_metadata`. Market bars are **not**
mutated.

### 2. Swing structure component (`structure.swing`)

Component id: **`structure.swing`** (not `structure.pivot`).

Geometry: **right-window confirmation only** — not symmetric classic pivot.

For available index `t` and `pivot_range = pr`:

```text
observed index p = t - pr
confirmation window = bars [p .. t] inclusive
```

Swing high at `p` when no bar in `(p .. t]` exceeds `high[p]`. Output is written at **`t` only**
(observed index is never back-written).

Temporal fields on outputs:

| Concept | Implementation |
|---------|----------------|
| Output row index | available / detection index `t` |
| Observed index | float64 column `swing_*_observed_index` (= `p`) |
| `available_at` | HTF bar close via `derive_available_at_timestamps` |

Availability: `DELAYED_BARS` with `delay_bars = pivot_range`.

### 3. Event vs state outputs

**Events** (sparse 0/1 flags and attached values on confirmation rows):

```text
swing_high_event, swing_low_event
swing_high_price, swing_low_price
swing_*_observed_index
higher_high_event, lower_high_event, higher_low_event, lower_low_event
```

**State** (forward-filled on computation grid):

```text
latest_swing_high_level, latest_swing_low_level
latest_higher_*_level, latest_lower_*_level
matching latest_*_observed_index columns
```

Classification uses strict `>` / `<`. Equal swings update `latest_swing_*` but emit no
higher/lower classification event. First swing of a type emits swing event only.

Kernel: NumPy reference loop in `adapters/numpy/swing.py` (Numba deferred).

### 4. MTF alignment policies (S005-T010)

Extend `AlignmentPolicy` and `OutputFieldSpec.alignment_policy`:

| Policy | Use for | Behaviour on LTF grid |
|--------|---------|------------------------|
| `LAST_CLOSED_BAR` | Stateful `latest_*` outputs (default) | Backward `join_asof` on `available_at`; forward fill intentional |
| `EVENT_AT_AVAILABLE` | Event flags and event-attached values | `1.0` / value on **first** LTF bar with `timestamp >= available_at`; inactive fill elsewhere |

Rationale: applying `LAST_CLOSED_BAR` to event flags would forward-fill `1.0` across bars —
a representation bug, not look-ahead. Variant A (`EVENT_AT_AVAILABLE`) is the Sprint 005 MVP
for point events.

`AlignmentIdentity` includes `output_id` so mixed policies on one component do not collide in
`AlignmentCache`.

**Observed index semantics on MTF:** `swing_*_observed_index` values are **computation-grid bar
indices** (e.g. 5m), not LTF indices. Consumers map to timestamps via the resampled
`AnalysisDataView` for that component — not via the evaluation grid index.

Sprint 004 continuous indicators retain default `LAST_CLOSED_BAR`; no change to existing
resample or `join_asof` path.

### 5. Visual inspection

Sprint 005 delivers `tests/spike/run_inspect_mtf_swing.py` — interactive Plotly HTML consuming
`run_analysis` frame output only (no compute in chart layer). Copy to `user_data/development/`
for local iteration.

## Consequences

### Positive

- RTH session columns available on analysis/frame path without bar mutation.
- Swing structure is lookahead-free, testable and MTF-aware with explicit policies.
- Event vs state projection is documented, cache-safe and regression-tested.
- Sprint 004 MTF foundation unchanged for TR/ATR/EMA path.

### Negative / limitations

- RTH resolver is ES-specific; other instruments need new resolver implementations.
- Resampling remains UTC epoch buckets (ADR-MA-012); session boundaries do not affect bucket edges.
- `observed_index` on LTF frames requires HTF grid mapping by consumers until optional
  `*_observed_at` columns are added in a future increment.
- Full PRB-007 resolution (Globex, missing-range, calendar registry) remains open.

### Follow-up (deferred)

- Session-boundary or calendar-aware resampling,
- `*_observed_at` datetime columns on aligned frames,
- Numba swing kernel matching reference loop,
- Structure transition / BOS semantics (separate downstream components).

## References

- `docs/planning/sprints/S005_CALENDAR_SPIKE_AND_DECISIONS.md`
- `docs/planning/sprints/S005_SWING_STRUCTURE_CONTRACT.md`
- `docs/adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md`
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-007 (partial MVP)
- `src/trading_framework/time/sessions/`
- `src/trading_framework/market_analysis/components/structure/swing.py`
- `src/trading_framework/market_analysis/data/align.py`
- `tests/spike/run_inspect_mtf_swing.py`
