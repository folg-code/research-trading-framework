# Market Analysis — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 6. Market Analysis

<a id="idea-010"></a>
## IDEA-010 — Component Scaffolding CLI

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Generate a local working component structure with:

- component file,
- tests,
- manifest,
- notes,
- example configuration.

### Potential Value

Encourages consistent local component development.

### Promotion Criteria

The component contract and local directory pattern are stable.

---

<a id="idea-011"></a>
## IDEA-011 — Automatic Candidate Promotion Report

```text
Status: INBOX
Category: Governance / Market Analysis
Added: 2026-06-19
```

### Summary

Evaluate whether a local component meets candidate or framework-promotion criteria.

Possible checks:

- tests,
- documentation,
- strategy independence,
- stable output schema,
- dependency declaration,
- proprietary thresholds,
- compatibility readiness.

### Important Rule

The tool may recommend promotion.

It must never promote automatically.

---

<a id="idea-012"></a>
## IDEA-012 — Order-Flow Component Pack

```text
Status: DEFERRED
Category: Market Analysis
Added: 2026-06-19
```

### Summary

Add reusable components for:

- volume delta,
- imbalance,
- footprint structures,
- absorption,
- DOM-derived states.

### Dependencies

- tick/trade/quote data models,
- high-volume storage,
- order-flow dataset contracts.

### Promotion Criteria

Market Data support for required source facts is stable.

---

<a id="idea-013"></a>
## IDEA-013 — Options-Derived Context Components

```text
Status: DEFERRED
Category: Market Analysis
Added: 2026-06-19
```

### Summary

Support Features and States derived from:

- gamma exposure,
- zero gamma,
- options positioning,
- implied volatility structures.

### Dependencies

- OptionsSnapshot model,
- provider data,
- timestamp and availability semantics.

---

<a id="idea-014"></a>
## IDEA-014 — Machine-Learned State Classifiers

```text
Status: GATED (ADR-0024 accepted, Sprint 044) — promotion not yet approved
Category: Market Analysis / ML
Added: 2026-06-19
Updated: 2026-08-28
```

### Summary

Allow trained statistical or ML models to produce Market Analysis States.

### Main Questions

- training artifact identity,
- data leakage,
- feature lineage,
- offline/online parity,
- model registry.

### Promotion Criteria

Rule-based Market Analysis and Research infrastructure are mature.

### Status Note (2026-08-28) — gate outcome

`ADR-0024` (`docs/adr/ADR-0024-machine-learned-state-promotion.md`) is **ACCEPTED**. It answers all
five questions above with testable conditions rather than principles, expanded into entry criteria
and a parity-test design sketch in `docs/archive/phases/phase-10-predictive-research/S044_GATE.md`:

1. **Training artifact identity** — a fingerprint over dataset, spec, seed and library versions,
   already computed as `run_fingerprint`, must be recorded in the `Lineage` of every State a
   promoted model produces. Durable serialization (replacing today's opaque `joblib` blobs, TD-022)
   is priced as a promotion sprint's first cost, not chosen here.
2. **Data leakage** — training-time leakage is already solved (purge/embargo, Sprint 039).
   Inference-time feature availability must be enforced by the component contract (the same
   `available_at` executor validation rule-based components already get), not by convention.
3. **Feature lineage** — already solved by Sprint 039's `OutputRef`-declared features; no new
   mechanism needed.
4. **Offline/online parity** — the hard condition. Batch research and the dry-run runtime must
   produce identical State values for identical inputs, which requires the fitted preprocessing
   transform to ship as part of the promoted artifact. A parity test on recorded data is the
   minimum, non-negotiable acceptance bar.
5. **Model registry** — deliberately not required. Promotion needs only a content-addressed
   artifact store (the layout Predictive Research already uses); TD-021 (no registry product)
   is restated, not repaid.

Strong out-of-sample metrics alone are explicitly **not sufficient** for promotion — a promoted
model becomes a Market Analysis input, so downstream strategies must still pass Phase 7 robustness
validation.

**This idea is still not approved for implementation.** The gate is now written and accepted; a
future promotion sprint that satisfies all five conditions would be the next step, and is not
scheduled by default (`docs/planning/ROADMAP.md` §13A, Phase 10 closure).

---

<a id="idea-027"></a>
## IDEA-027 — Price-Structure and Session Context Component Pack

```text
Status: INBOX
Category: Market Analysis
Added: 2026-09-17
```

### Summary

Add a new family of `structure.*` and `session.*` components, translating
well-known price-action / "smart money" concepts into plain,
mechanism-describing names with no trader slang. Inspired by a prior,
external framework's feature catalog (analyzed 2026-09-17), which documented
both the algorithms and their defects — lookahead bias, contradictory
definitions between strategies, broken dependencies between modules.
Inspiration for the mechanism only; no code or naming is carried over.

Proposed components:

- **`structure.range_discontinuity`** — three-bar range gap in the direction
  of a move: no overlap between the range two bars back and the current
  bar's range (formerly known in the source material as "fair value gap").
- **`structure.impulse_origin_range`** — the last opposite-direction bar
  preceding a directional impulse that exceeds an ATR-normalized threshold
  (formerly "order block"). Carries a `role` field (`active` /
  `invalidated`) instead of a separate "breaker" component for the
  invalidated case.
- **`structure.level_sweep_rejection`** — a level is pierced and price
  rejects back within an observation window (formerly "liquidity grab").
- **`structure.level_role_reversal`** — a level's role (resistance/support)
  flips after being broken and retested (formerly "SR flip").
- **`structure.matched_extreme_pair`** — two same-type extrema (high/high or
  low/low) within an ATR tolerance (formerly "equal highs/lows").
- **`structure.close_reversal_level`** — a level derived from a pair of
  closes whose direction reversed relative to two bars back (formerly "CISD
  / change in state of delivery").
- **`session.overlap_window`** — flags the time window where two named
  sessions' active hours overlap (formerly "killzone"); parametrized by the
  pair of sessions rather than a fixed label.
- **`session.previous_period_extreme`** — previous day/week high or low
  (`period`, `side` params).
- **`session.current_period_extreme`** — running high/low of the current
  session/day/week period, causal only (no full-period value assigned
  before the period closes).
- **`structure.impulse_follow_through`** — directional extreme move over a
  fixed lookahead window after an impulse event, normalized by ATR at the
  event bar (formerly "follow-through"/FT). Added 2026-09-17 on a second
  pass over the source material — it is the strength-of-continuation
  counterpart to `structure.impulse_origin_range` and belongs in the same
  pack rather than as a separate idea.
- **`structure.opening_gap`** — the gap between a bar's open and the prior
  bar's close (formerly "gap up/down"). Distinct from
  `structure.range_discontinuity`, which is a three-bar range gap, not an
  open-vs-prior-close gap. Added 2026-09-17, same pass as
  `impulse_follow_through`.

### Naming Convention (applies to this pack and to future components)

1. Names describe the calculation or the observed fact, not a trading
   metaphor — no slang as a component or field name (order block, FVG,
   killzone, CISD, breaker, etc.).
2. A source-material abbreviation may appear once in prose as a
   cross-reference, never as a field or component name.
3. Variant/invalidation states are fields on the same component (e.g.
   `role`), not separate components.
4. Clarity outweighs brevity when the two conflict.
5. Every new component gets an entry in
   [`ANALYSIS_COMPONENT_CATALOG.md`](../../reference/modules/ANALYSIS_COMPONENT_CATALOG.md)
   (formula, warm-up, zero-denominator convention) before promotion — that
   catalog is the authoritative dictionary; this idea does not duplicate it.

### Potential Value

Fills a documented gap: no session-context or price-structure-zone
components exist in the registry today. Session context (previous/current
period extremes, session overlap windows) and structure zones give the
Signal Model vocabulary for zone-based entries without inheriting the
source material's lookahead-bias and broken-dependency defects.

### Main Questions

- Exact ATR-multiple thresholds for `impulse_origin_range` and
  `range_discontinuity` need calibration in this framework, not copying the
  source material's undocumented constants.
- Whether `level_sweep_rejection` and `level_role_reversal` should share a
  base "level" representation with the existing `structure.session_range` /
  `structure.level_distance` components, to avoid duplicating level
  bookkeeping.
- Whether session hour definitions (Asia/London/New York) belong in this
  component pack or in a shared session-calendar reference usable by
  multiple components.

### Dependencies

- None blocking implementation — builds on existing OHLC-based component
  infrastructure; `structure.swing` and `structure.session_range` already
  prove the pattern.

### Validation Approach (directional, not yet sprint-scheduled)

**Supersedes** the now-archived
[Sprint 063 draft](../../archive/superseded/SPRINT_063_STRATEGY_SIMULATION_SERIES.md)
("Reproducible Strategy Simulation Series") — that draft was never approved
or executed, and this idea's validation need is effectively the same
frozen-matrix simulation work retargeted at new components and the
strategies built from them, rather than at the six existing strategies
Sprint 063 named. Its acceptance-criteria discipline (matrix frozen before
results, no post-hoc changes, every case gets a disposition including
zero-trade/negative outcomes, no leaderboard or promotion claim) still
applies; only the subject changed.

Once a subset of these components is implemented and registered, validate
them and strategies built from them in two stages, using that same
explicit, hand-frozen case-list discipline rather than a generic sweep:

1. **Per component** — author a minimal Signal Model using the new
   component and run it through the existing `run_signal_research` /
   `run_signal_research_family` path. This machinery already exists and
   needs no new engineering.
2. **Per strategy** — compose a small, explicitly enumerated set of new
   candidate strategies from the validated components (strategies may
   combine more than one new component) and run that frozen list through
   the existing single-run Strategy Research orchestration, one case at a
   time, not the Strategy Research family/sweep machinery described in
   [PRB-020](prb-017-020.md#prb-020), which does not exist yet (planned
   closure route: Phase 16E, directional/unplanned). If the candidate list
   would need to outgrow a small, hand-frozen matrix to say anything useful,
   that is the trigger to open a Phase 16E Wave 0 instead of building ad hoc
   sweep code here.

This is deliberately **not yet a numbered sprint**: it depends on this idea's
own implementation work finishing first. A sprint gets opened and numbered
once component implementation is actually underway and a maintainer sets
the concrete case list (component subset, candidate strategies, evaluation
periods).

### Risks

- The source material documents systemic lookahead bias in analogous
  constructs (a full-period high/low assigned to bars before the period
  closes). Every `session.*` component here must be causal-only from the
  first implementation — a hard acceptance gate, not a later fix.

### Promotion Criteria

- Naming reviewed and confirmed per the convention above.
- Threshold/parameter design resolved via a Wave 0, matching this project's
  pattern for pre-sprint technical decisions.
- Catalog entries drafted alongside the implementation PR.

---

<a id="idea-028"></a>
## IDEA-028 — Volatility Estimator Component Pack

```text
Status: INBOX
Category: Market Analysis
Added: 2026-09-17
```

### Summary

Add range-based volatility estimators and a regime classifier, found on a
second pass over the same external feature-catalog source material analyzed
for [IDEA-027](#idea-027). Same naming discipline applies: no source-material
jargon as a field or component name, and every component gets a catalog
entry before use.

Proposed components:

- **`volatility.range_based_variance`** — a rolling variance estimator using
  the bar's full range rather than only close-to-close returns
  (parametrized by estimation method, e.g. the source material's
  Garman-Klass and Parkinson formulas). More sample-efficient than a
  close-to-close estimator for the same window length.
- **`volatility.directional_asymmetry`** — average range-based volatility
  computed separately over up-close and down-close bars in a window, plus
  their log-ratio asymmetry.
- **`volatility.acceleration`** — first difference of a volatility measure
  (rate of change of volatility itself, not of price).
- **`volatility.choppiness_index`** — `100·log10(sum(true_range)/(max(high)-min(low)))/log10(period)`
  over a rolling window; a standard, already-named technical measure (not
  source-material slang) of range-bound vs. trending conditions.
- **`volatility.regime_state`** — a three-state classification
  (compression/balanced/expansion) from the ratio of a fast to a slow ATR.
  Distinct from the existing `volatility.state` (LOW/HIGH from a single ATR
  threshold) — this is a second, ratio-based volatility state, not a
  replacement.

### Potential Value

`volatility.range_based_variance` is a materially different (and reportedly
more sample-efficient) estimator family than the close-to-close approach
`volatility.relative_volatility` already uses — worth having as an
alternative, not a replacement. `volatility.regime_state` gives Signal/
Market Models a second, independently useful volatility-state vocabulary
alongside the existing threshold-based one.

### Main Questions

- Whether `directional_asymmetry` needs its own component or can be
  expressed as two calls to `range_based_variance` with a bar-direction
  filter plus a derived ratio in the DSL — avoid a component that only
  wraps arithmetic already expressible.
- Fast/slow ATR period defaults and the compression/balanced/expansion
  thresholds for `regime_state` need calibration in this framework, not
  copied from the source material's undocumented constants.

### Dependencies

- None blocking — OHLC-only, same infrastructure class as the existing
  `volatility.*` components.

### Promotion Criteria

- Naming reviewed and confirmed.
- Catalog entries (formula, warm-up, zero-denominator convention) drafted
  alongside the implementation PR.

---

<a id="idea-029"></a>
## IDEA-029 — Trend and Momentum Efficiency Component Pack

```text
Status: INBOX
Category: Market Analysis
Added: 2026-09-17
```

### Summary

Add volatility-normalized trend and momentum measures, from the same
source-material review as IDEA-027/IDEA-028.

Proposed components:

- **`trend.movement_efficiency`** — `abs(close_t - close_{t-N}) / sum(true_range over N)`:
  how much of the total distance traveled translated into net directional
  movement, over `[0, 1]`.
- **`trend.normalized_slope`** — the slope of a trend measure (e.g. the
  existing `trend.slope` OLS output, or `trend.ema`) divided by a
  concurrent volatility measure, so the slope is comparable across
  different volatility regimes rather than in raw price units.
- **`momentum.normalized_rate_of_change`** — `ln(close_t / close_{t-N})`
  divided by a concurrent volatility measure — a volatility-normalized
  alternative to a raw percentage rate of change.

### Potential Value

All three give Signal Models a way to compare trend/momentum strength
across instruments or volatility regimes without the value scale shifting
with raw price volatility — a documented gap versus the existing
`trend.ema`/`trend.slope`/`momentum.rsi` family, which are either
price-scale or already self-normalized (RSI) but not volatility-normalized.

### Main Questions

- Which volatility measure is the shared normalizer — the existing
  `volatility.relative_volatility`, or a new `volatility.range_based_variance`
  from IDEA-028? This should be decided once, not per-component.
- Whether `normalized_slope` should be a standalone component or a
  documented composition pattern in `ANALYSIS_COMPONENT_CATALOG.md`, since
  the DSL's lack of arithmetic on an `Operand` (noted for
  `structure.level_distance`) applies here too — a division needs a real
  component, not an expression.

### Dependencies

- Depends on which volatility component becomes the shared normalizer
  (see Main Questions) — resolve that before implementation, ideally as
  part of the same Wave 0 that would size IDEA-028.

### Promotion Criteria

- Naming reviewed and confirmed.
- Shared normalizer decision recorded before implementation.
- Catalog entries drafted alongside the implementation PR.

---

<a id="idea-030"></a>
## IDEA-030 — Rolling Window Position (Generic Distribution Utility)

```text
Status: INBOX
Category: Market Analysis
Added: 2026-09-17
```

### Summary

The source material computes a rolling z-score, and both a normal-approximation
percentile/rank and an empirical rolling-rank percentile, repeatedly, by hand,
for each individual indicator it wants to classify into states. Rather than
port that per-indicator duplication, add one generic component:

- **`statistics.rolling_window_position`** — given another component's
  output as input, returns that value's position within its own trailing
  window: a z-score, and a percentile via either a normal approximation or
  an empirical rolling rank (explicit, separate `method` values — the
  source material conflated these under the same field name in different
  places, which this framework should not repeat).

### Potential Value

This is the general mechanism behind every `*_state` classifier discussed
for IDEA-027/IDEA-028 (e.g. `volatility.regime_state`-style three-bucket
labels): instead of writing a bespoke percentile-window classifier for each
new continuous component, any future component gets one "for free" by
composing with `rolling_window_position`. Reduces the friction IDEA-010
(Component Scaffolding CLI) is separately trying to address, for this one
specific, recurring pattern.

### Main Questions

- ~~Component composition mechanics: does the registry/DSL support a
  component taking another component's `OutputRef` as its input today, or
  does this require new registry capability?~~ **RESOLVED (Phase 19 Wave 0,
  2026-09-17): already supported.** `structure.level_distance`,
  `trend.ema_distance` and `momentum.macd` already consume another
  component's output via `ComponentDependency`/`ComponentOutputRef`
  (`src/trading_framework/market_analysis/models/dependencies.py:26-33`).
  No new registry capability needed.
- Whether the empirical-rank variant's warm-up/window-size defaults should
  differ from the normal-approximation variant's, given they have different
  statistical assumptions.

### Dependencies

- ~~Needs the registry's component-composition capability confirmed or
  built first~~ — resolved; none blocking. See
  [Phase 19](../roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md),
  which moved this idea into its Wave A (parallel, independent) increment.

### Promotion Criteria

- Component-composition mechanics confirmed feasible.
- Naming and both `method` variants documented in
  `ANALYSIS_COMPONENT_CATALOG.md` before promotion.

---

<a id="idea-031"></a>
## IDEA-031 — Candle Pattern and Bar-Volume Component Pack

```text
Status: INBOX
Category: Market Analysis
Added: 2026-09-17
```

### Summary

Add candle-pattern classification and bar-volume-derived components — the
latter needs only per-bar volume (already available on OHLCV bars), not the
tick/trade/quote data IDEA-012 (Order-Flow Component Pack) requires, so it
is not blocked on IDEA-012's data-model dependency.

Proposed components:

- **`candle.reversal_pattern`** — a single priority-ordered categorical
  label per bar/side from a fixed, documented rule set (e.g. hammer-style
  rejection, a close-through-held-level pattern, a multi-bar engulfing
  pattern), returning at most one label per side rather than independent
  booleans per pattern — matching the source material's own documented
  choice to prioritize rather than stack labels, made explicit here rather
  than left implicit.
- **`candle.smoothed_ohlc`** — a smoothed OHLC transform (formerly
  "Heikin-Ashi") computed causally from the bar series.
- **`volume.rolling_weighted_price`** — a rolling volume-weighted average
  price over a fixed window, plus deviation bands, computed from per-bar
  volume. Explicitly not a session-anchored VWAP (that has its own
  lookahead/anchoring questions the source material flags) — a rolling
  window only.
- **`volume.cumulative_trend`** — cumulative volume signed by the direction
  of price change bar-to-bar (formerly "Price Volume Trend").

### Potential Value

Gives Signal Models a documented, single-label candle-pattern vocabulary
(replacing ad hoc per-strategy pattern detection) and two volume-derived
measures that need no new data infrastructure.

### Main Questions

- The exact rule set and priority order for `candle.reversal_pattern` needs
  its own design pass in this framework, not a copy of the source
  material's specific thresholds.
- Whether `volume.rolling_weighted_price`'s window should be a fixed bar
  count only, or whether a session-anchored variant belongs in this pack or
  should wait for `session.*` components from IDEA-027 to settle first.

### Dependencies

- None blocking for the rolling-window variant; a session-anchored VWAP
  variant would depend on IDEA-027's session-calendar placement decision.

### Promotion Criteria

- Naming and rule set reviewed and confirmed.
- Catalog entries drafted alongside the implementation PR.

---

<a id="idea-032"></a>
## IDEA-032 — Level Distance Extension and Fibonacci Levels

```text
Status: INBOX
Category: Market Analysis
Added: 2026-09-17
```

### Summary

Extend the existing `structure.level_distance` component (currently
ATR-normalized distance to the running session high/low only) to cover more
level sources, and add Fibonacci retracement/extension levels as their own
components — "Fibonacci" is a standard mathematical/technical term, not
trading slang, so it is kept as the name rather than translated.

Proposed work:

- Extend `structure.level_distance` to accept additional level sources
  beyond the running session high/low — previous-period extremes
  (`session.previous_period_extreme` from IDEA-027), matched extreme pairs
  (`structure.matched_extreme_pair` from IDEA-027) — instead of adding a
  separate near-duplicate distance component per level type, which is what
  the source material did.
- **`structure.fibonacci_retracement_level`** — retracement levels at
  documented ratios (e.g. 0.5, 0.618, 0.66) between a swing's high and low.
- **`structure.fibonacci_extension_level`** — extension levels beyond the
  swing range at ratios above 1.0.

### Potential Value

Avoids the source material's own documented failure mode: multiple
near-identical "distance to level" implementations that drifted out of sync
with each other. One extensible distance component is easier to keep
correct than several.

### Main Questions

- ~~Whether `structure.level_distance`'s existing output shape (a single
  ATR-normalized distance) generalizes cleanly to multiple simultaneous
  level sources, or whether it needs a breaking output-shape change~~ —
  **RESOLVED (Phase 19 Wave 0, 2026-09-17): it does not generalize.**
  `structure.level_distance`'s `OutputSchema` is a fixed two-field shape
  hardcoded to one level source
  (`src/trading_framework/market_analysis/components/structure/level_distance.py:61-66,120-132`).
  Maintainer decision: build a new, generic multi-level-source component
  instead of extending this one in place — see
  [Phase 19](../roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md). Exact
  name/output shape for the new component is still an open architect design
  pass.
- Which swing definition feeds the Fibonacci levels — the existing
  `structure.swing` component's HH/HL/LH/LL output, most likely, but this
  should be confirmed rather than assumed.

### Dependencies

- Best sequenced after `structure.matched_extreme_pair` and
  `session.previous_period_extreme` (IDEA-027) exist, since the extension
  work is partly about wiring those in as additional level sources.

### Promotion Criteria

- Design pass on `structure.level_distance`'s output shape completed.
- Catalog entries drafted alongside the implementation PR.

---
