# Sprint 005 — Swing Structure Contract

## Metadata

```text
Component: structure.swing
Sprint: 005 Wave 2 (T005–T009)
Status: ACCEPTED (2026-07-12)
Supersedes: S005_PIVOT_CONTRACT.md (pivot/HH naming retired)
```

---

## 1. Geometry — right-window confirmation (not symmetric pivot)

For available index `t` and parameter `pivot_range = pr`:

```text
observed index p = t - pr
confirmation window = bars [p .. t] inclusive
```

**Swing high** when no bar in `(p .. t]` exceeds `high[p]`.  
**Swing low** when no bar in `(p .. t]` goes below `low[p]`.

This is **not** a symmetric local extrema (classic pivot) detector. It does not
require a left-side window `[p - pr .. p - 1]`.

Output is written at **available index** `t` only. **Observed index** `p` is
never back-written.

Legacy `PivotDetectorBatched` used symmetric geometry; outputs are not
semantically equivalent.

---

## 2. Temporal semantics

| Concept | Meaning |
|---------|---------|
| Observed index | Bar where the extremum occurred (`p`) |
| Available index | Bar where confirmation completes (`t`); output row index |
| `available_at` | Close of detection bar on delayed event outputs |

Availability policy: `DELAYED_BARS` with `delay_bars = pivot_range`.

Observed indices are stored as `float64` with `NaN` where not applicable.

---

## 3. Event vs state outputs

### Swing point events (sparse values, dense 0/1 flags)

| Output | Type on grid |
|--------|----------------|
| `swing_high_event` / `swing_low_event` | `1.0` on confirmation, else `0.0` |
| `swing_high_price` / `swing_low_price` | price on confirmation, else `NaN` |
| `swing_high_observed_index` / `swing_low_observed_index` | `p` on confirmation, else `NaN` |

### Classification events

| Output | When `1.0` |
|--------|------------|
| `higher_high_event` | new swing high strictly above previous confirmed swing high |
| `lower_high_event` | new swing high strictly below previous confirmed swing high |
| `higher_low_event` | new swing low strictly above previous confirmed swing low |
| `lower_low_event` | new swing low strictly below previous confirmed swing low |

Equal swings emit swing events but **no** higher/lower classification event.

### General swing state (forward-filled from first confirmation)

```text
latest_swing_high_level
latest_swing_low_level
latest_swing_high_observed_index
latest_swing_low_observed_index
```

### Classified structural state (forward-filled)

```text
latest_higher_high_level / latest_lower_high_level
latest_higher_low_level / latest_lower_low_level
latest_*_observed_index (matching each level)
```

---

## 4. Edge-case policies (MVP)

| Case | Policy |
|------|--------|
| Simultaneous swing high + low at one row | Emit both independently |
| First swing of a type | Swing event only; no classification until second swing |
| Equal swing vs previous | Swing + `latest_swing_*` updated; no classification event |
| Input NaN | Kernel rejects (`ValidationError` at component boundary) |
| `pivot_body` / symmetric pivot | Deferred |
| Numba optimization | Deferred until contract stable; loop is reference implementation |

---

## 5. Technology split

```text
Polars  → dataset prep, resampling, joins (S004 path)
NumPy   → swing kernel (this component)
Numba   → optional later; must match reference loop in tests
pandas  → not used in production kernel
```

---

## 6. Downstream (future sprints)

Not in this component:

```text
Structural Level Cross Detection  (replaces legacy BOS/MSS naming)
Relative Range Level Calculator   (replaces fibo_swing)
Structural Transition Classifier  (interpretation layer)
```

Downstream should consume `latest_swing_high_level` / `latest_swing_low_level`
without knowing HH/LH classification internals.

---

## 7. Multitimeframe projection (S005-T010)

When `structure.swing` runs on a higher timeframe (for example 5m) and the
evaluation grid is lower (for example 1m), each output declares an
`alignment_policy` on its `OutputFieldSpec`:

| Output kind | Policy | Behaviour on LTF grid |
|-------------|--------|------------------------|
| Event flags and event-attached values (`swing_*_event`, prices, observed indices, classification events) | `EVENT_AT_AVAILABLE` | `1.0` (or attached value) on the **first** LTF bar whose timestamp is `>= available_at`; inactive fill (`0.0` or `NaN`) elsewhere — **no forward fill** |
| Stateful levels and indices (`latest_*`) | `LAST_CLOSED_BAR` | Backward `join_asof` on `available_at`; forward propagation on the dense grid is intentional |

All swing outputs carry per-bar `available_at` (HTF bar close) so alignment
can project without look-ahead. Sprint 004 continuous indicators keep their
existing default (`LAST_CLOSED_BAR`).

Variant A (`EVENT_AT_AVAILABLE`) is the MVP event projection policy. Sparse
event tables remain a future option.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial pivot contract (retired) |
| 2026-07-12 | Neutral swing event/state contract; right-window geometry documented |
| 2026-07-12 | MTF projection policies: EVENT_AT_AVAILABLE vs LAST_CLOSED_BAR |
