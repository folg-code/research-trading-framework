# S049-T001 — Availability Enforcement Finding

Spike (no code). Answers `SPRINT_049.md` §4 Finding 2: does the engine reject
a dependency read whose `available_at` postdates the consuming result's
`detected_at`, and where?

Status: this document is the deliverable. It modifies no production file.

---

## 1. Question being answered

ADR-0024 condition 2 (`docs/adr/ADR-0024-machine-learned-state-promotion.md`
lines 94–113) states, verbatim:

> "Inference-time availability is a **component-contract** obligation,
> enforced by the same executor validation that already rejects a non-causal
> read for rule-based components (ADR-MA-009 'engine responsibilities'), not
> a documentation note in the model's spec."

This spike checks whether that executor validation exists today, by reading
the code, not the ADR prose that describes it.

---

## 2. Verdict

**The mechanism ADR-0024 condition 2 presupposes does not exist in the
`market_analysis` executor.** No code path in `executor.py`, `planner.py`,
`assembler.py`, `models/availability.py`, `models/result.py`,
`storage/workspace.py`, or `storage/result_store.py` raises, rejects, or even
inspects `available_at` when one component reads another component's
`AnalysisResult` as a dependency. This is a STOP-and-report per D-S049-10 —
the finding is stated plainly, not softened, and no fix is proposed here.

**ADR-0030 is needed.** Sprint 050 cannot rely on "the same executor
validation" because there is no such validation to reuse; it must design and
build the mechanism from nothing, which is executor/runtime work whose
existence (not just its size) was previously assumed. This should be recorded
as a new ADR before Sprint 050 implements it, per governance's rule that an
architectural decision (a new invariant on the executor) is an `architect`
ADR, not something `engineer` improvises during implementation.

A **different, unrelated** causal check exists in a **different layer**
(`research/predictive/matrix.py`), for a **different consumer**
(offline feature-matrix construction, not runtime component execution). It
enforces "matrix `available_at` must not be later than `detected_at`"
(ADR-0023 §4), which is textually similar to condition 2's language but is
not the executor mechanism condition 2 names, does not run inside
`SequentialBatchExecutor`, and does not fire when one `market_analysis`
component reads another's output during planning/execution. See §5.

---

## 3. What the four named files actually do

### 3.1 `market_analysis/models/availability.py` (34 lines, whole file read)

Defines `AvailabilityPolicy` (`SAME_BAR` / `DELAYED_BARS` / `RETROSPECTIVE`)
and `AvailabilityMetadata` (`policy`, `delay_bars`). `AvailabilityMetadata.__post_init__`
(lines 24–33) validates only internal consistency of these two fields
(`delay_bars >= 0`; `delay_bars >= 1` iff `policy is DELAYED_BARS`). It is a
**declared policy label** carried on `AnalysisResult.availability`
(`models/result.py:67`). Nothing in this file reads a timestamp, compares two
results, or can reject anything at read time — it has no access to any other
result when constructed.

### 3.2 `market_analysis/execution/executor.py` (170 lines, whole file read)

- `validate_analysis_result` (lines 54–71) is the **only** validation
  function the executor runs on a freshly computed result. It checks
  exactly three things: `computation_identity.component_id` matches
  the executed component (60–62), every output series' length equals
  `bar_count` (64–67), and `validity.valid_from_index >= warmup.warmup_bars`
  (69–71). It does not touch `available_at`, `availability`, or any
  dependency's timestamps.
- `_execute_component_node` (lines 127–169) is where a component reads its
  dependencies: `workspace.view_for(node.dependency_keys, ...)` (141–146)
  builds the `AnalysisWorkspaceView` passed to `node.implementation.compute(...)`
  (149–153). No availability check happens between `view_for` returning and
  `compute` being called — the dependency results are handed to the
  implementation's `compute()` unfiltered and unchecked.
- `ExecutionCache` and `ResampleCache` (lines 22–51) are pure identity-keyed
  memoization; neither touches `available_at`.

### 3.3 `market_analysis/planning/planner.py` (316 lines, whole file read)

`DependencyPlanner` builds the DAG (`_expand_dependencies`, lines 166–194) and
topologically sorts it (`_topological_sort`, lines 200–231), raising
`CyclicDependencyError` (line 229) only on a **cycle**, never on a timing
relationship. Nothing in this file reads `available_at`, `detected_at`, or
any `AnalysisResult` at all — the planner operates purely on `ComponentDependency`
/ `OutputRef` declarations and `ComponentRequest` parameters, before any bar
data or result exists. Ordering here guarantees a dependency is *computed*
before its dependent (structural precedence), which is a different guarantee
than "the dependency's per-bar value was available before the consumer's
per-bar timestamp" (per-bar causal precedence). ADR-MA-006 (`docs/adr/ADR-MA-006-dependency-dag-and-execution-planning.md`)
confirms this is the intended scope of the planner: 5 decision steps (expand,
resolve, dedupe, topo-sort, reject cycles), none mentioning availability.

### 3.4 `market_analysis/assembly/assembler.py` (215 lines, whole file read)

`AnalysisFrameAssembler.assemble` (lines 55–118) and its helper
`_resolve_column_values` (120–164) are the **one place** `available_at` is
actually consumed for a causal purpose: when `evaluation_timeframe` differs
from a component's `computation_timeframe` (`needs_alignment`, checked at
line 133), the column is run through `align_output_series`
(`data/align.py`, called at assembler.py:158). That function performs a
backward as-of join (or event-at-available placement) so that a higher-timeframe
value is only exposed on evaluation bars at or after its `available_at`
(see §4). Two things to note about this code path:

1. It runs in the **assembler**, at flat-frame materialization time for one
   named consumer (the caller building an `AnalysisFrame`), not in the
   **executor**, at dependency-read time between two components inside a
   plan (`_execute_component_node`). Condition 2's requirement is about a
   model component's `AnalysisDataView`/dependency read during `compute()`;
   the assembler runs strictly after all components in the plan have already
   executed and been validated.
2. It only fires when `evaluation_timeframe is not None` and
   `needs_alignment(...)` is true (assembler.py:132–140) — i.e. only for
   genuine multitimeframe projection. A same-timeframe dependency read
   (the common case, and the case ADR-MA-009 §MVP calls out: "MVP uses
   same-bar availability policy for single-timeframe batch runs") never
   passes through this code at all.

`_find_result` (177–190) locates a result by `component_id` + `parameters`
match only — no timestamp comparison.

---

## 4. What `available_at` mechanism does exist, and its actual behavior

`market_analysis/data/align.py` (whole file read) is the only module that
consumes `available_at` causally:

- `align_event_at_available` (lines 43–70): for each active event value,
  finds the first evaluation timestamp `>= available_at[i]` via
  `np.searchsorted` (line 66) and places the value there; nothing before that
  index. A value whose `available_at` never falls within
  `evaluation_timestamps` is silently never placed — no error.
- `align_values_to_evaluation_grid` -> `LAST_CLOSED_BAR` (lines 92–123): a
  Polars `join_asof(..., strategy="backward")` (lines 112–117) — each
  evaluation timestamp gets the latest value whose `available_at <=`
  that timestamp. A future `available_at` is simply not joined; it never
  raises.
- `align_output_series` (lines 126–148) requires `series.available_at is not
  None` (raises `ValidationError` if absent, lines 133–135) but this is a
  **presence** check, not a **causality** check — it is refusing to align a
  series that carries no timestamps at all, not refusing a series whose
  timestamps are too late.

**None of these three functions ever raises because a value's `available_at`
is "too late."** They express causality by construction (an as-of-backward
join structurally cannot select a future row) and by silent omission (a
value with no valid placement is left as the fill value), not by rejecting
the read with an error the way condition 2's language ("fail the same way a
rule-based component fails today") implies. There is no rule-based component
failure mode to point to, because nothing fails today.

---

## 5. The look-alike mechanism, and why it is not the one ADR-0024 cites

`src/trading_framework/research/predictive/matrix.py:144–157`
(`_resolve_available_at`) does raise:

```python
for detected_at, feature_available_at in zip(timestamps, available_at, strict=True):
    if feature_available_at > detected_at:
        msg = "feature available_at must not be later than detected_at"
        raise PredictiveMatrixError(msg)
```

This is ADR-0023 §4's leakage guard, confirmed in
`src/trading_framework/research/predictive/CLAUDE.md`: *"Matrix `available_at`
must not be later than `detected_at` (ADR-0023 §4 / SPRINT_039 §9.1).
Look-ahead availability is rejected at build time. This is not
`MarketBar.available_at`, which may be after `observed_at` and is not passed
through to the labelled matrix."*

Three reasons this is not the mechanism ADR-0024 condition 2 names:

1. **Different layer.** It runs in `research/predictive/`
   (`build_predictive_matrix`, offline feature-matrix construction), not in
   `market_analysis/execution/` (`SequentialBatchExecutor`, runtime component
   execution). ADR-0024 condition 2 is explicitly about **inference time**
   ("nothing today stops a model component from being wired to a feature
   whose `available_at` has not yet elapsed relative to the State's
   `detected_at`" — line 102–104), which is an executor/runtime concern, not
   an offline research-pipeline concern.
2. **Different input shape.** It compares an already-assembled
   `AnalysisFrame` column's `available_at` against a matrix row's
   `detected_at`, both derived after the executor and assembler have already
   run. It has no notion of "one component reading another component's
   `AnalysisResult` during `compute()`," which is what condition 2 describes.
3. **`detected_at` does not exist as a field anywhere in `market_analysis`.**
   `grep` for `detected_at` under `market_analysis/` returns zero matches;
   `AnalysisResult` (`models/result.py`) has no `detected_at` field, only
   `availability: AvailabilityMetadata` (a policy label, §3.1) and each
   `OutputSeries.available_at` (an optional per-bar timestamp tuple,
   `models/result.py:21`). `detected_at` is a `Signal Model` /
   `Predictive Research` concept (ADR-0011, ADR-0012, ADR-0023,
   `signal_model/`, `research/predictive/`) — it is not defined for a
   `market_analysis` `AnalysisResult`, so a literal reading of the spike's
   question ("a consuming result's `detected_at`") does not even type-check
   against the executor's domain model. The nearest analogue on an
   `AnalysisResult` is its own per-bar evaluation timestamp on the market
   view it was computed over, which the executor also never compares against
   a dependency's `available_at`.

---

## 6. Cross-checked against the ADRs describing these files

- **ADR-MA-009** (`docs/adr/ADR-MA-009-warmup-causality-and-availability.md`)
  lists exactly three "Engine responsibilities" (lines 22–26): extend
  `computation_range` for warm-up, validate output length/valid-index range,
  expose warm-up metadata. This matches `executor.py`'s
  `validate_analysis_result` line for line (§3.2) — there is no fourth,
  undocumented responsibility hiding in the code. Tellingly, ADR-MA-009's own
  "Consequences / Positive" section (line 49) lists *"future workflows can
  reject non-causal components"* as a forward-looking benefit, not a present
  capability — the ADR that condition 2 cites as already having built this
  says, in its own text, that the capability is future work.
- **ADR-MA-006** (`docs/adr/ADR-MA-006-dependency-dag-and-execution-planning.md`)
  describes the planner's 5 decision steps (expand, resolve, dedupe,
  topo-sort, reject cycles) — matches `planner.py` line for line (§3.3), no
  availability step.
- **ADR-MA-005** (`docs/adr/ADR-MA-005-analysis-result-and-output-identity.md`)
  describes `AnalysisResult`'s shape (`ComputationIdentity`, `OutputSchema`,
  `Lineage`, `ValidityMetadata`, `WarmUpMetadata`, `AvailabilityMetadata`,
  diagnostics) — matches `models/result.py` (§3.1) — and assigns no
  enforcement duty to any of these fields at read time.

---

## 7. Consequence for Sprint 050

- Sprint 050 (Phase 14B) must **design and build** inference-time
  availability enforcement in the executor; it cannot "reuse" an existing
  check, because none exists for this purpose. This is new executor surface
  area, not a wiring task.
- **ADR-0030 is needed** before that mechanism is implemented — an
  architectural decision proposing *where* the check lives (candidates the
  code suggests without prescribing: inside `_execute_component_node` before
  `compute()` is called, as a new step in `validate_analysis_result`, or as a
  new `AnalysisWorkspace`/`AnalysisResultStore` responsibility comparable to
  `dependency_results`'s existing missing-key check), *what* it compares
  (per-output-series `available_at` vs. what — the consuming component has no
  `detected_at` of its own, only its own evaluation timestamps and warm-up
  range), and *how* it fails (a new error type, analogous to
  `OutputValidationError` or `PredictiveMatrixError`). None of that design
  work is done by this spike — proposing and designing it is `architect`
  work with maintainer approval, per governance, not something this
  document should improvise.
- This does not change Sprint 049's scope (D-S049-10). No production file
  was touched to produce this finding.

---

## 8. Files read for this spike

- `src/trading_framework/market_analysis/execution/executor.py` (whole file)
- `src/trading_framework/market_analysis/planning/planner.py` (whole file)
- `src/trading_framework/market_analysis/assembly/assembler.py` (whole file)
- `src/trading_framework/market_analysis/models/availability.py` (whole file)
- `src/trading_framework/market_analysis/models/result.py` (whole file)
- `src/trading_framework/market_analysis/storage/workspace.py` (whole file)
- `src/trading_framework/market_analysis/storage/result_store.py` (whole file)
- `src/trading_framework/market_analysis/data/align.py` (whole file)
- `src/trading_framework/research/predictive/matrix.py` (relevant section,
  `_resolve_available_at`, lines 144–157)
- `src/trading_framework/research/predictive/CLAUDE.md`
- `docs/adr/ADR-MA-009-warmup-causality-and-availability.md`
- `docs/adr/ADR-MA-006-dependency-dag-and-execution-planning.md`
- `docs/adr/ADR-MA-005-analysis-result-and-output-identity.md`
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` §"2. Data leakage
  (inference-time feature availability)"
