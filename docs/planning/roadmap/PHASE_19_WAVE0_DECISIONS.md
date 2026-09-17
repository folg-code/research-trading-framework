# Phase 19 — Wave 0 Decisions (Market Analysis Component Catalog Expansion)

```text
Status: ACCEPTED (maintainer, 2026-09-17)
Basis:  docs/product/PRD-market-analysis-catalog-expansion-2026-09.md (APPROVED)
        docs/planning/roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md
        docs/planning/registries/idea-market-analysis.md (IDEA-010, IDEA-011, IDEA-027-IDEA-032)
        src/trading_framework/market_analysis/registry/builtins.py as on main
        src/trading_framework/market_analysis/components/structure/level_distance.py as on main
        src/trading_framework/market_analysis/components/volatility/relative_volatility.py as on main
        src/trading_framework/market_analysis/models/dependencies.py as on main
        src/trading_framework/time/sessions/ as on main
```

Architecture triage recommended these decisions; the maintainer accepted
all six as proposed on 2026-09-17, matching this project's Wave 0
governance convention (see
`docs/archive/phases/phase-02-market-data/S045_WAVE0_DECISIONS.md` for the
precedent format). They are now binding for implementation.

Two of the PRD's five original Wave 0 questions are already resolved and are
**not reopened here**: IDEA-030's composition-capability question (the
registry already supports `ComponentDependency`/`ComponentOutputRef`
composition — confirmed in the PRD and Phase 19 roadmap) and IDEA-032's
extend-vs-new-component question (a new component, not an in-place
extension of `structure.level_distance`). This document covers the
remaining open items plus the sprint-splitting confirmation.

---

## D-P19-01 — Registration tooling design (IDEA-010, IDEA-011)

### Problem statement

Today, adding one component to the catalog requires, by hand, in
`src/trading_framework/market_analysis/registry/builtins.py`:

1. a component class + implementation class (elsewhere, under
   `components/<pack>/`),
2. a `register_<name>_component(registry) -> None` function that calls
   `registry.register(SomeComponent(), NumpySomeImplementation(), default=True)`,
3. one call to that function added inside `register_mvp_components`,
4. an `__all__` entry for the new `register_*` function,
5. an import line pulling the component/implementation classes into
   `builtins.py`'s header,
6. (per the phase's binding rules) a hand-written entry in
   `docs/reference/modules/ANALYSIS_COMPONENT_CATALOG.md`.

This is small per component but fully manual and repeated identically 26+
times in this PRD. IDEA-010 (Component Scaffolding CLI) and IDEA-011
(Automatic Candidate Promotion Report) exist specifically to remove that
repetition, and the PRD requires them "before or alongside the first wave
of components," not after.

### Decision

Build both, scoped narrowly — this is scaffolding for ~26 known components
in one existing pattern, not a general-purpose code generator:

**IDEA-010 — `scripts/market_analysis/scaffold_component.py`, a thin CLI**
(consistent with ADR-0022's "scripts stay thin — parse args, call an
application API, write output" convention):

- **Inputs from the author** (CLI flags, all required except where noted):
  `--component-id` (e.g. `structure.range_discontinuity`, validated against
  the `<pack>.<name>` pattern already used by every existing `ComponentId`),
  `--pack` (must match an existing `components/<pack>/` directory or a new
  one the CLI is allowed to create — `structure`, `session`, `volatility`,
  `trend`, `momentum`, `candle`, `volume`, `statistics`), `--kind`
  (`FEATURE` or `STATE`, from `ComponentKind`), `--causal` (defaults to
  `true` — a `session.*` component author cannot opt out silently; see
  D-P19-05 for why this flag exists at all), and `--depends-on` (repeatable,
  optional, `ComponentId` values for component dependencies the author
  already knows they need — e.g. `structure.matched_extreme_pair` scaffolds
  with a `component_dependencies()` stub pre-populated for a
  `session.previous_period_extreme` dependency).
- **What it generates** — a file skeleton plus registration boilerplate,
  both, matching the existing hand-written pattern exactly (not a new
  pattern the CLI invents):
  - `src/trading_framework/market_analysis/components/<pack>/<name>.py`
    with the component class, implementation class, module docstring
    stub, `_COMPONENT_ID`/`_COMPONENT_VERSION`/`_IMPLEMENTATION_ID`/
    `_IMPLEMENTATION_VERSION` constants pre-filled, empty
    `_PARAMETER_SCHEMA`/`_OUTPUT_SCHEMA`, and `history_requirement`/
    `data_dependencies`/`component_dependencies`/`compute` methods
    stubbed with `raise NotImplementedError` (the author fills in the
    actual math — the CLI does not guess formulas), `__all__` populated.
  - `tests/market_analysis/components/<pack>/test_<name>.py` with a
    component-contract test stub (import the component, assert
    `component_id`/`component_version`/`kind`/`causality`, assert
    registration round-trips through the registry) — enough to make
    "add the real assertions" the remaining work, not "write a test
    file from scratch."
  - A **registration patch**, applied directly to
    `registry/builtins.py` (not a separate file the author copy-pastes):
    add the import line, add `register_<name>_component`, add its call
    inside `register_mvp_components`, add the `__all__` entry — using a
    simple text-anchor insertion (e.g. insert alphabetically among
    existing `register_*` functions), not an AST rewrite. This is the
    single highest-friction step per the PRD's own framing, so it is the
    one piece scripted rather than templated-and-copied.
  - A stub `ANALYSIS_COMPONENT_CATALOG.md` entry (component ID, one-line
    placeholder for formula/warmup/zero-denominator convention, marked
    `<!-- TODO: fill in before promotion -->`), appended under a
    "Phase 19 additions" heading the CLI creates once and reuses.
- **Explicitly not generated**: the actual math, parameter defaults beyond
  the trivial `causal`/`kind` ones, or DSL example configuration content
  beyond a placeholder — those need the author's domain judgment and are
  out of scope for a scaffolding tool, per the PRD's "proportional to ~26
  components" framing.

**IDEA-011 — `scripts/market_analysis/check_promotion_readiness.py`, a
read-only report, never an auto-promoter** (the idea's own "Important
Rule" — the tool may recommend, never promote — is treated as load-bearing,
not aspirational):

- **Checks, all mechanically verifiable** (no judgment calls the tool
  would have to fake):
  1. registered — the component ID appears in `default_mvp_registry()`,
  2. tested — a `tests/.../test_<name>.py` exists and its test collection
     is non-empty,
  3. output schema stable — `OutputSchema` has at least one
     `OutputFieldSpec` (catches a scaffold left unfinished),
  4. dependency declaration present — `component_dependencies()` and
     `data_dependencies()` are both implemented (not left raising
     `NotImplementedError`),
  5. catalog entry exists — a heading matching the component ID appears
     in `ANALYSIS_COMPONENT_CATALOG.md` and does not contain the
     `<!-- TODO -->` marker IDEA-010 inserts,
  6. causal-only gate, pack-conditional — for any `session.*` component,
     the causality flag is `Causality.CAUSAL` and a lightweight static
     check flags any output field whose docstring/name suggests a
     full-period value (heuristic only — flagged for human review, not a
     pass/fail gate on its own; see D-P19-05 on why this check is
     pack-specific).
- **Output**: a per-component PASS/FAIL/NEEDS-REVIEW table to stdout (and
  optionally a markdown file for pasting into a PR description) — a
  recommendation surface, never a mutation. It does not edit the registry,
  the catalog doc, or any component's status field. "Strategy
  independence" and "proprietary thresholds" (named in IDEA-011's own
  "Possible checks") are dropped from v1: both need human judgment this
  tool cannot mechanize honestly, and a check that always reports
  "needs human review" is not worth building — track them as promotion
  checklist prose in `ANALYSIS_COMPONENT_CATALOG.md`'s promotion-criteria
  section instead, not as a scripted check.

### Reasoning

Both tools mirror an existing, already-working pattern instead of
introducing a new one — the scaffolding CLI's output is exactly what a
careful author would hand-write today, and the promotion report checks
exactly the mechanical parts of the PRD's "done" bar (registered, tested,
documented, causal-only where applicable). Keeping both read-only /
patch-only (never deleting or overwriting hand-written logic, never
auto-promoting) matches IDEA-011's explicit rule and avoids a tool that
silently corrupts a component the author has already started customizing.

### Alternatives considered

- **A full code generator that infers component logic from a DSL-like
  spec file.** Rejected — over-engineered for 26 components with 26
  distinct formulas; the risk is generating subtly wrong math that looks
  finished.
- **IDEA-011 as a CI gate that blocks merge.** Rejected for v1 — the PRD's
  non-goals exclude validation/promotion decisions from this phase; a
  blocking gate conflates "implemented and contract-tested" (this PRD's
  bar) with "ready for Signal Research promotion" (a separate, later
  concern). A non-blocking report satisfies IDEA-011's "recommend, never
  promote" rule more literally than a gate would.
- **Skipping IDEA-010 and only building IDEA-011.** Rejected — the PRD is
  explicit that both are wanted before Wave A, and the registration-patch
  step (the CLI's highest-value piece) has no equivalent in a
  report-only tool.

---

## D-P19-02 — Shared volatility normalizer for IDEA-029

### Problem statement

`trend.normalized_slope` and `momentum.normalized_rate_of_change`
(IDEA-029) both need to divide by "a concurrent volatility measure." Two
candidates exist: the already-implemented `volatility.relative_volatility`
(`value`/`ratio` outputs, log-return population stdev over `period` vs.
`baseline_period`) and the not-yet-built `volatility.range_based_variance`
(IDEA-028, a range-based estimator — Garman-Klass/Parkinson family).

### Decision

**Use `volatility.relative_volatility`'s `value` output as the shared
normalizer for both `trend.normalized_slope` and
`momentum.normalized_rate_of_change`.** `volatility.range_based_variance`
is built as an independent IDEA-028 estimator but is **not** wired in as
IDEA-029's normalizer.

### Reasoning

- **Estimator-family mismatch.** `relative_volatility` is a close-to-close,
  log-return estimator — the same return-space `trend.slope`,
  `trend.ema`, and `momentum.rate_of_change`-style measures already live
  in (log or simple close-to-close returns). `range_based_variance` is
  explicitly a *different* estimator family (uses the bar's full range,
  not just closes) proposed for its own, separate reason — sample
  efficiency for volatility estimation itself, not comparability with a
  trend/momentum measure. Normalizing a close-based trend slope by a
  range-based variance mixes two different notions of "movement" in one
  ratio; normalizing it by a close-based volatility measure keeps the
  ratio internally consistent (numerator and denominator both describe
  close-to-close behavior).
- **It already exists and is already used analogously.**
  `relative_volatility` is registered, tested, and its docstring already
  documents a zero-denominator convention (0.0 when the baseline window is
  perfectly flat) that IDEA-029's components can point to instead of
  re-deriving one. Building on it means Wave B's two new components need
  no new normalizer machinery, only a `ComponentDependency` on an
  existing output — the exact pattern `structure.level_distance` already
  proves for `volatility.atr`.
- **No forced sequencing risk.** Because `relative_volatility` is Wave-A
  complete already (built), using it as the normalizer means IDEA-029 is
  blocked only on IDEA-028's Wave A landing in the trivial sense of "Wave B
  comes after Wave A," not on any additional design or implementation
  work inside IDEA-028 itself. Choosing `range_based_variance` instead
  would tie IDEA-029 to IDEA-028 shipping a specific estimator variant
  (Garman-Klass vs. Parkinson — still an open parameter choice inside
  IDEA-028) before IDEA-029 could even be designed, adding a dependency
  the PRD's "decided once" framing is trying to avoid.
- **Which `relative_volatility` output**: use `value` (the
  `period`-window population stdev of log returns), not `ratio` (the
  regime ratio against `baseline_period`). `ratio` is itself a derived,
  already-relative quantity (roughly centered near 1.0); dividing a slope
  by a value that is itself a ratio produces a harder-to-interpret unit
  than dividing by a stdev — `value` is a return-scale volatility
  estimate, matching the numerator's return-scale units directly.

### Alternatives considered

- **`volatility.range_based_variance` as the normalizer.** Rejected per
  the estimator-family-mismatch reasoning above; also not yet built,
  which would put a Wave B item's design work inside Wave A's critical
  path.
- **Let each of the two new components pick its own normalizer.**
  Rejected — the PRD explicitly asks for this decided once, not
  per-component, to avoid two similar components disagreeing on what
  "volatility-normalized" means.
- **A new, dedicated normalizer component built just for IDEA-029.**
  Rejected as unnecessary duplication — `relative_volatility.value` already
  is exactly "a rolling volatility measure in return-space"; no gap to
  fill.

### Follow-on note

`trend.normalized_slope` and `momentum.normalized_rate_of_change` both
need a real division (`slope / volatility`, `ln(close_t/close_{t-N}) /
volatility`) that the DSL cannot express as an `Operand` expression (no
arithmetic on comparisons — the same limitation `structure.level_distance`
and `volatility.relative_volatility.ratio` already work around by doing
the division inside `compute()`). Confirming this: both become
**standalone components** with a `ComponentDependency` on
`volatility.relative_volatility` (and on `trend.slope`/`trend.ema` or
`momentum.rate_of_change`'s output respectively), not a "documented
composition pattern" in the catalog doc — IDEA-029's own Main Questions
raised this as open; this Wave 0 pass resolves it in favor of a real
component, consistent with every existing division-needing precedent in
the codebase.

---

## D-P19-03 — New multi-level-source component for IDEA-032

### Problem statement

The maintainer already declined extending `structure.level_distance` in
place (its `OutputSchema` is fixed at
`distance_to_session_high_atr`/`distance_to_session_low_atr`, hardcoded to
`structure.session_range` as the sole level source — see
`level_distance.py:44-66,120-140`). IDEA-032 needs a new component that
computes ATR-normalized distance to an arbitrary configured level source,
including `structure.matched_extreme_pair` and
`session.previous_period_extreme` (both IDEA-027, not yet built) as
additional sources, without repeating `structure.level_distance`'s
one-source-only shape.

### Decision

**Name: `structure.distance_to_level`.** Output shape: **one row per bar,
fixed named-field pairs per entry in a `level_sources` list parameter** —
not a long/tall one-row-per-(bar, level-source) shape.

Concretely:

- **Parameter**: `level_sources`, a list of level-source identifiers
  (e.g. `("session_high", "session_low", "previous_day_high",
  "previous_day_low", "matched_extreme_pair_high",
  "matched_extreme_pair_low")` — a small, fixed enum-like set of string
  literals the component's parameter schema validates, not a free-form
  `ComponentId` string, so a typo fails schema validation rather than
  silently producing an all-`NaN` column). `period` (ATR period) remains a
  parameter, same convention as `structure.level_distance`.
- **Output**: for each configured source, two `float64` output fields
  named `distance_to_<source>_atr` (e.g. `distance_to_session_high_atr`,
  `distance_to_previous_day_high_atr`,
  `distance_to_matched_extreme_pair_high_atr`) — a fixed set of named
  fields, sized by the `level_sources` parameter at construction/canonicalization
  time, not a variable-length row-per-source table.
- **Dependency wiring**: one `ComponentDependency` per configured source
  plus one on `volatility.atr`, same pattern `level_distance.py` already
  uses for `structure.session_range` + `volatility.atr` — this component
  is a generalization of that dependency pattern, not a new mechanism.
- **`structure.level_distance` is untouched** — kept exactly as-is (single
  source, two fixed fields) as the simple, common case; `structure.distance_to_level`
  is the multi-source generalization for consumers that need it. No
  migration, no deprecation.

### Reasoning

- **Fixed named fields, not one-row-per-(bar, level-source), because this
  registry's output model is column-oriented, not tabular-per-key.**
  Every existing component (`level_distance`, `session_range`,
  `relative_volatility`) reports a small, statically-known
  `OutputSchema` of named `float64` series, one value per bar. A
  one-row-per-(bar, level-source) shape would require either a variable
  number of output rows per bar (breaking the one-value-per-bar-per-field
  invariant every downstream consumer, e.g. a Signal Model condition,
  already assumes) or a nested/long-format encoding this registry has no
  precedent or plumbing for (`OutputSeries` is a flat float64 array
  aligned to bar index — see `ndarray_to_output_series`/`OutputSeries` in
  `models/result.py`). Fixed named fields keep `structure.distance_to_level`
  a drop-in peer of every other `FEATURE` component: same `OutputSchema`
  shape, same alignment guarantees, same DSL usage pattern
  (`structure.distance_to_level(level_sources=[...]).distance_to_previous_day_high_atr`).
- **Naming**: `distance_to_level` describes the calculation ("distance
  to a level, ATR-normalized") per IDEA-027's naming convention (no
  trading metaphor); it deliberately avoids `level_distance_v2` or
  `level_distance_multi`, since the PRD's naming rule treats a
  variant/generalization as a new, clearly-named component, not a
  versioned or qualified name that implies the old one is deprecated.
- **Plugging in `structure.matched_extreme_pair` / `session.previous_period_extreme`**:
  each configured `level_sources` entry maps to a specific
  `ComponentOutputRef` (component ID + canonicalized parameters + output
  ID) internally — e.g. `"previous_day_high"` resolves to
  `ComponentDependency(ComponentOutputRef(component_id=session.previous_period_extreme,
  parameters={period: "day", side: "high"}, output_id=value))`. Because
  `matched_extreme_pair` and `previous_period_extreme` don't exist yet
  (they're Wave A, `structure.distance_to_level` is Wave B), this mapping
  table is finalized when those two components' actual output IDs are
  known — a small addition to `structure.distance_to_level`'s
  implementation, not a redesign, since the parameter-to-dependency
  mapping pattern itself doesn't change per source added.
- **Fibonacci components are separate, not level sources here.**
  `structure.fibonacci_retracement_level` and
  `structure.fibonacci_extension_level` (also IDEA-032) compute levels
  themselves (a swing's high/low at documented ratios) rather than
  reporting distance to an existing level — they stay their own
  components, feeding `structure.distance_to_level` as yet another
  `level_sources` entry only if a future consumer needs "distance to a
  Fibonacci level," which is not asked for in this PRD's scope.

### Alternatives considered

- **One row per (bar, level-source) pair (a "tall" output).** Rejected —
  no precedent in this registry's `OutputSchema`/`OutputSeries` model;
  would require new plumbing this PRD's non-goals explicitly exclude
  ("no registry structural change assumed in advance").
- **A single `distance_atr` field with a companion `level_source` label
  field.** Rejected for the same tall-shape reason, and because it can't
  report multiple sources for the same bar simultaneously (a real need —
  a Signal Model may want "distance to session high" and "distance to
  previous-day high" as two separate, simultaneously-available
  conditions).
- **`structure.level_distance_v2`.** Rejected on naming-convention
  grounds — versioned/qualified names read as "the old one is being
  replaced," which is explicitly false here.

---

## D-P19-04 — Session-hour calendar placement

### Problem statement

Session-hour windows (Asia/London/New York) are needed by `session.overlap_window`
and `session.previous_period_extreme`/`session.current_period_extreme`
(IDEA-027), and by IDEA-031's deferred session-anchored VWAP variant. The
open question is whether session-hour definitions live inside IDEA-027's
component pack or as a shared reference module.

### Decision

**Shared reference module: `src/trading_framework/time/sessions/`** (already
exists — currently home to `CmeEsRthSessionResolver`, the
`TradingSessionResolver` protocol, and session ID constants). Add named
session-window resolvers there (`AsiaSessionResolver`, `LondonSessionResolver`,
`NewYorkSessionResolver`, or one parametrized resolver covering all three),
consumed by IDEA-027's `session.*` components and, later, by IDEA-031's
deferred VWAP variant — not duplicated inside either pack.

### Reasoning

- **A working, in-repo precedent already exists and already solves the
  hard part.** `CmeEsRthSessionResolver`
  (`src/trading_framework/time/sessions/cme_es_rth.py`) already
  demonstrates exactly the pattern needed: validate the input is UTC
  (`_validate_timestamps` rejects naive or non-UTC timestamps, matching
  AGENTS.md's "reject naive datetimes; use UTC internally" rule),
  convert to the session's local timezone (`dt.convert_time_zone`), derive
  weekday/hour/minute, and return a `session_id`/`is_rth`-style column set
  via `TradingSessionResolver.resolve(timestamps: pl.Series) -> pl.DataFrame`.
  Asia/London/New York session windows are the same shape of problem
  (a named window keyed by hour-of-day in a named IANA zone, with
  optional holiday handling) — reusing the pattern is far cheaper than
  reinventing timezone handling per component pack, and avoids each of
  IDEA-027's `session.*` components (and, later, IDEA-031's VWAP variant)
  quietly drifting on what "the London session" means.
- **Two consumers already named in the PRD.** IDEA-027 needs it now;
  IDEA-031's deferred VWAP variant explicitly needs the same placement
  decision per its own Dependencies section. A module used by two
  unrelated packs is the textbook case for a shared reference module
  rather than pack-local duplication.
- **What it needs to expose**, sketched (final field names are an
  implementation detail for whoever builds IDEA-027, not fixed here):
  - A resolver (or one parametrized resolver instance) per named session
    — `Asia` (e.g. 00:00-09:00 Asia/Tokyo, exact bounds TBD by whoever
    implements this against a documented reference, not invented here),
    `London` (e.g. 08:00-16:30 Europe/London), `New York` (e.g.
    09:30-16:00 America/New_York — note this overlaps, not duplicates,
    the existing `CmeEsRthSessionResolver`'s RTH window; the two answer
    different questions — "is this bar in the NY trading session" vs.
    "is this bar in CME ES RTH" — and should stay separate rather than
    one reusing the other's exact hours as an assumption).
  - Each resolver takes UTC `pl.Series` timestamps in, per the existing
    `TradingSessionResolver` protocol, and returns a `session_id`/
    membership-boolean column set the same shape as `CmeEsRthSessionResolver`
    already returns — so `session.overlap_window` can compute the
    overlap of any two named sessions' boolean columns with plain
    boolean AND, and `session.previous_period_extreme`/
    `current_period_extreme` can group bars by `trading_day`-equivalent
    session boundaries the same way `structure.session_range` already
    groups by RTH session.
  - No new timezone-handling code — all conversion goes through
    `pl.Series.dt.convert_time_zone` against IANA zone names
    (`Asia/Tokyo`, `Europe/London`, `America/New_York`), consistent with
    `_NY_TIMEZONE = "America/New_York"` already used in
    `cme_es_rth.py`, and consistent with AGENTS.md's UTC-internal rule —
    UTC is always the wire/storage representation; local-zone conversion
    happens only inside the resolver, only for window membership
    computation.

### Alternatives considered

- **Inline inside IDEA-027's `session.*` components.** Rejected — would
  duplicate timezone-window logic between `session.overlap_window`,
  `session.previous_period_extreme` and (later) IDEA-031's VWAP variant,
  and duplicates logic the `time/sessions/` module already owns for
  `structure.session_range`'s RTH concept. The PRD's own IDEA-027 Main
  Questions already flags this ("whether session hour definitions belong
  in this component pack or a shared session-calendar reference") as
  worth resolving once, not per-component.
- **A brand-new module rather than extending `time/sessions/`.**
  Rejected — `time/sessions/` already exists, already owns exactly this
  concept (`TradingSessionResolver`), and already has one working
  session resolver to pattern-match against; a second, parallel module
  would fragment session-window logic across two places for no benefit.

---

## D-P19-05 — Secondary open items

### `candle.reversal_pattern` rule set and priority order (IDEA-031)

**Decision**: a small, documented, prioritized rule set of **four** named
patterns, evaluated in this fixed priority order per bar/side (first match
wins — matching the source material's own documented "one label, not a
stack" choice, made explicit rather than left implicit):

1. **`engulfing`** — the current bar's body fully contains the prior bar's
   body and closes in the opposite direction to the prior bar's close
   (a multi-bar pattern; checked first because it needs the widest
   context and should not be shadowed by a single-bar pattern on the
   same side).
2. **`level_close_reversal`** — price closes back on the opposite side of
   a level it traded through intrabar (the "close-through-held-level"
   pattern named in IDEA-031's summary) — depends on a level input (this
   makes it, structurally, a composed component consuming a level source
   the same way `structure.distance_to_level` does; the exact level
   source parameter is left to whoever implements this, not fixed here).
3. **`rejection_wick`** — a hammer-style single-bar rejection: a wick on
   one side at least `wick_ratio_threshold` (proposed default `2.0`, i.e.
   the rejecting wick is at least twice the body length) times the body,
   with a small opposite wick, reusing `candle.wick`'s already-defined
   `upper_wick_ratio`/`lower_wick_ratio`/`body_ratio` outputs as a
   dependency rather than recomputing wick geometry.
4. **`none`** — no pattern matched; an explicit label, not a missing/NaN
   value, so downstream consumers can distinguish "evaluated, no pattern"
   from "not yet warmed up."

This is proposed as a starting, documented rule set — calibratable later,
not treated as final science. It is deliberately smaller than the source
material's fuller pattern catalog per the PRD's "don't port the source
material's thresholds" instruction.

### ATR-multiple threshold defaults (`structure.impulse_origin_range`, `structure.range_discontinuity`)

**Decision**: propose starting defaults, explicitly marked calibratable,
not left unspecified:

- `structure.impulse_origin_range`: `impulse_atr_multiple` default
  **`1.5`** — an impulse leg must span at least 1.5x the concurrent ATR to
  qualify as the directional move that makes the preceding opposite-
  direction bar an "origin range." Chosen as a starting point roughly at
  the boundary where `volatility.range_expansion`'s own existing
  threshold-based logic already treats a single-bar range as "expanded"
  (consistent unit and rough magnitude with an already-shipped component,
  rather than an unrelated constant).
- `structure.range_discontinuity`: `min_gap_atr_multiple` default
  **`0.1`** — the non-overlapping three-bar range gap must be at least
  0.1x ATR to avoid flagging noise-level, sub-tick gaps as discontinuities
  on low-volatility bars.
- Both defaults are `ParameterFieldSpec` values, overridable per DSL
  usage, not hardcoded constants — consistent with every existing
  threshold-bearing component (`volatility.state`'s threshold,
  `volatility.relative_volatility`'s `period`/`baseline_period`). The PRD
  asked for an empirical check rather than a guess where practical;
  absent a maintainer-provided historical dataset to calibrate against
  during this Wave 0 pass, these are principled starting points (unit-
  matched to ATR, order-of-magnitude-consistent with existing threshold
  components) explicitly flagged for recalibration once Wave A components
  are running against real data — not a substitute for that empirical
  check.

### MTF (multi-timeframe) variants from day one

**Decision**: precedent (`volatility.atr`, `trend.slope` — single-timeframe
first, MTF projection later) **applies uniformly to all 26 components in
this PRD, with no exceptions**. No component in Wave A or Wave B gets an
MTF variant in this PRD; every component's `ComponentRequest` already
supports an optional `computation_timeframe` per the existing MVP
convention (`ANALYSIS_COMPONENT_CATALOG.md`'s "All components accept
optional `computation_timeframe`" note), so single-timeframe-first does
not foreclose MTF later — it is deferred, not precluded.

### Promotion criteria: catalog-wide vs. pack-specific

**Catalog-wide** (every one of the 26+1 components, no exceptions):

- Naming convention compliance (IDEA-027's rules: describes the
  calculation, no trading slang, abbreviation once in prose only,
  variant states as fields not components).
- A passing component-contract test (registration round-trip, output
  schema shape, warmup behavior).
- An `ANALYSIS_COMPONENT_CATALOG.md` entry (formula, warm-up,
  zero-denominator convention) before promotion.
- Dependency declaration correctness (`data_dependencies`/
  `component_dependencies` both implemented and accurate).

**Pack-specific** (do not generalize beyond their pack):

- **Causal-only gate** — hard acceptance gate for every `session.*`
  component (IDEA-027) and for any Wave B component that reads a
  `session.*` output (e.g. `structure.distance_to_level` when configured
  with a `session.previous_period_extreme` source). Does **not**
  generalize to IDEA-028's volatility estimators, IDEA-029's normalizers,
  or IDEA-030/031's statistics/candle/volume components — those are
  already causal by construction (rolling windows over past bars only,
  no period-final aggregate involved) and gain nothing from a dedicated
  gate; re-applying the `session.*` gate's specific check (no full-period
  value assigned before period close) to a component that has no concept
  of "period close" would be a meaningless check, not a stricter one.
- **ATR-multiple threshold calibration** — specific to
  `structure.impulse_origin_range`, `structure.range_discontinuity`, and
  `candle.reversal_pattern`'s `wick_ratio_threshold` (this document's
  proposed starting defaults, above). Does not generalize to components
  with no threshold parameter (e.g. `volatility.range_based_variance`,
  `statistics.rolling_window_position`).
- **Shared normalizer consistency** — specific to IDEA-029's two
  components; not a criterion for any other pack.

---

## D-P19-06 — Sprint-splitting confirmation

### Problem statement

The PRD's Handoff asks whether "Wave A + tooling" (IDEA-027, IDEA-028,
IDEA-030, IDEA-031-base components, plus IDEA-010/011 tooling) fits one
sprint, or needs splitting further, once tooling and per-component designs
are drafted.

### Decision

**Split into two sprints, not one: a Tooling sprint, then a Wave A
sprint** (Wave B remains its own, separate, later sprint, per the PRD's
existing Wave A/Wave B split — this decision only addresses whether "Wave
A + tooling" further subdivides).

Concrete estimate: **3 sprints total for this PRD** —

1. **Sprint N — Tooling** (IDEA-010 + IDEA-011): the scaffolding CLI, the
   promotion report, and a dry run of both against one real Wave A
   component (chosen as a pilot, e.g. `structure.opening_gap` — the
   simplest proposed component, single-bar, no component dependencies) to
   prove the generated skeleton actually gets used, per the PRD's success
   metric 1 ("Wave A actually uses them, not built and left unused").
2. **Sprint N+1 — Wave A** (IDEA-027's 11 components, IDEA-028's 5,
   IDEA-031's 4 base components, IDEA-030's 1 — 21 components total),
   using the tooling from Sprint N.
3. **Sprint N+2 — Wave B** (IDEA-029's 2 components, IDEA-032's 3
   components — `structure.distance_to_level` + both Fibonacci
   components — and IDEA-031's deferred VWAP variant — 6 components
   total), depending on Wave A's `structure.matched_extreme_pair`,
   `session.previous_period_extreme`, and the session-calendar module
   from D-P19-04.

### Reasoning

- **Scope size, once drafted, does not fit one sprint.** 21 Wave A
  components each need: implementation, a component-contract test, a
  catalog entry, and (for the 11 `session.*`/`structure.*` IDEA-027
  components) a causal-only correctness check. Even with tooling removing
  the registration-boilerplate cost, that is still 21 independent units
  of actual formula-writing and testing work — larger than a typical
  single sprint in this project's own precedent (Sprint 047 added 2
  components, Sprint 048 added a handful, Sprint 051 added the
  volatility-regime pair). Bundling tooling into the same sprint as 21
  components risks the tooling being rushed to unblock components,
  defeating its own purpose.
- **Tooling first, alone, de-risks Wave A.** The PRD's success metric 1
  requires the tooling to exist and be *used* by Wave A, not merely
  exist. A dedicated tooling sprint with a one-component pilot run
  catches a broken scaffold or a promotion-report false-positive before
  it's baked into 20 more components' worth of copy-pasted patterns.
- **Wave A stays one sprint despite being large, not split further,
  because it has no internal sequencing** — the PRD's own framing is
  "simple/independent, built in parallel," and this Wave 0 pass found no
  hidden cross-component dependency inside Wave A (the PRD's "riskiest
  assumption" section asks specifically for this check). 21 independent
  components is a lot of work but not a coordination problem the way
  Wave A -> Wave B's dependency chain is — so it is one (large) sprint,
  not several small ones, to avoid arbitrary subdivision with no
  technical justification.
- **Wave B stays its own sprint** as the PRD already specifies — it has
  a real, checked dependency chain (D-P19-03's `structure.distance_to_level`
  needs Wave A's `matched_extreme_pair`/`previous_period_extreme`;
  D-P19-04's VWAP variant needs the session-calendar module; D-P19-02's
  IDEA-029 components need `relative_volatility`, already built).

### Alternatives considered

- **One sprint for tooling + Wave A**, as the PRD's Handoff floated as
  the "likely shape." Rejected after sizing: 21 components is too large a
  single sprint payload next to this project's own sprint-size precedent,
  and would pressure-test tooling and components simultaneously rather
  than tooling first.
- **Split Wave A itself into two sprints** (e.g. IDEA-027 alone, then
  IDEA-028+030+031 together). Rejected — no dependency argues for this
  split; it would be an arbitrary line through an intentionally parallel,
  independent set of components, adding sprint-boundary overhead without
  a technical reason.

---

## Summary for maintainer review

| Decision | Recommendation | Status |
|---|---|---|
| D-P19-01 | Scaffolding CLI (file+test+registration-patch+catalog stub) and read-only promotion report, both scoped to the existing manual pattern | ACCEPTED (maintainer, 2026-09-17) |
| D-P19-02 | `volatility.relative_volatility.value` as IDEA-029's shared normalizer; both normalized components are new standalone components, not a documented composition pattern | ACCEPTED (maintainer, 2026-09-17) |
| D-P19-03 | New component `structure.distance_to_level`; fixed named-field-per-configured-source output, `structure.level_distance` left untouched | ACCEPTED (maintainer, 2026-09-17) |
| D-P19-04 | Session-hour windows live in shared `src/trading_framework/time/sessions/` module, extending the existing `TradingSessionResolver` pattern | ACCEPTED (maintainer, 2026-09-17) |
| D-P19-05 | 4-pattern prioritized rule set for `candle.reversal_pattern`; starting ATR-multiple defaults (1.5 / 0.1); MTF deferred uniformly, no exceptions; catalog-wide vs. pack-specific promotion criteria enumerated | ACCEPTED (maintainer, 2026-09-17) |
| D-P19-06 | Split into 3 sprints: Tooling, then Wave A, then Wave B (not "Wave A + tooling" as one sprint) | ACCEPTED (maintainer, 2026-09-17) |

All six decisions above are Accepted (maintainer, 2026-09-17). Per this
project's governance convention, architecture triage recommended; the
maintainer's explicit review and acceptance make them binding on
implementation from this point forward.
