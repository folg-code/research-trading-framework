# Phase 18 (Increment 18A) — Wave 0 Decisions

```text
Status: ACCEPTED (maintainer, 2026-09-18)
Basis:  docs/product/PRD-dashboard-strategy-research-evidence.md (APPROVED)
        docs/planning/roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md
        src/trading_framework/research/simulation/assumptions.py as on main
        src/trading_framework/market_model/results.py as on main
        src/trading_framework/research/observations/market_model_observation.py as on main
        apps/dashboard/src/dashboard_app/publication/sanitizers.py as on main
        apps/dashboard/src/dashboard_app/publication/workspace.py as on main
        apps/dashboard/src/dashboard_app/catalog/scanner.py as on main
        scripts/dashboard/generate_btc_signal_quality_projection.py as on main
        src/trading_framework/research/analytics/{aggregates,distribution,grouping}.py as on main
        user_data/workspace/research/strategy_research/runs/* on disk (3 runs)
```

Architecture triage investigated the PRD's four Handoff items directly
against the codebase and the 3 persisted runs, rather than treating them as
open design questions to answer from first principles. Two investigations
overturned an assumption the PRD stated as fact; both are corrected here and
cross-referenced back into the PRD. The maintainer accepted all decisions
below on 2026-09-18.

---

## D-P18-01 — SimulationAssumptions backfill for the 3 existing runs

### Problem statement

The PRD flagged as an open question whether the 3 existing runs' original
`SimulationAssumptions` (`initial_capital`, `commission_per_side`,
`slippage_bps`, fill policy) are recoverable, since only a one-way
SHA-256 fingerprint was persisted, not the field values themselves.

### Decision

**Resolved without needing Sprint 064's config at all.** All 3 runs'
manifests carry the identical fingerprint `1aa6ee647c5cc636`. Hashing the
`SimulationAssumptions` dataclass's own defaults
(`fill_policy_entry=NEXT_BAR_OPEN`, `fill_policy_exit=NEXT_BAR_OPEN`,
`slippage_bps=0`, `commission_per_side=0`, `initial_capital=100000`) through
`simulation_assumptions_fingerprint`'s exact algorithm reproduces
`1aa6ee647c5cc636` exactly. All 3 runs used the framework's plain defaults —
no custom assumptions were ever set for any of them.

Backfill for the 3 existing runs: write these 5 default field values
directly into each of their `manifest.json` files. No config archaeology,
no "assumptions not recovered" disclosure needed — the PRD's contingency
for that case does not trigger.

### Reasoning

Brute-forcing a 16-hex-char truncated SHA-256 in general is infeasible, but
this was never a general preimage search — there is exactly one plausible
candidate (the dataclass's own defaults, since no run-launching code path
that existed before this PRD ever passed non-default assumptions), and
verifying one candidate against a known hash is trivial. This is a directly
checked fact, not an inference from context.

### Alternatives considered

- **Search Sprint 064/058/013 git history for the original launch
  configs.** Unnecessary once the fingerprint-matches-defaults check
  succeeded; would have been the fallback if it had failed.
- **Mark all 3 runs "assumptions not recovered."** Rejected — factually
  wrong now that the values are known with certainty, not merely assumed.

### PRD correction

The PRD's Milestone 1 "Backfill" bullet's contingency ("assumptions not
recovered for pre-2026-09-18 runs") does not apply to any of the 3 existing
runs. Struck from the PRD; see the edit there.

---

## D-P18-02 — Context-expectancy computation mechanism

### Problem statement

The PRD's Milestone 1 described `context_expectancy.parquet` as computed
"post-hoc from already-persisted `equity.parquet`/`trades.parquet`" by
joining trades against "the run's Market Model evaluation" at
`entry_signal_at`. Investigation found this premise **factually wrong**:

- `MarketModelEvaluator.evaluate()` → `market_model_result_dataframe()`
  (`src/trading_framework/market_model/results.py:6-14`) persists only
  `timestamp`, `available_at` and a single **boolean** `model_result` column
  — the final gate value. It explicitly drops every intermediate
  Market Analysis component value the underlying expression evaluated.
- The richer intermediate values live only in the transient in-memory
  `AnalysisFrame` (`market_analysis/assembly/frame.py:33-38`) used during
  evaluation. Nothing persists it per run today. Confirmed no per-run
  artifact holds it: the 3 runs' directories contain exactly
  `manifest.json`, `equity.parquet`, `trades.parquet`,
  `analytics/summary_metrics.parquet` — nothing else.
- There is **no market-model-id → definition registry**. Grepping for a
  reverse lookup (`market_model_id ==`, `MarketModelRegistry`) found
  nothing. Market Models are built by calling a specific Python builder
  function directly (e.g. `build_canonical_strategy_model()` in
  `src/trading_framework/strategy/canonical_examples.py`, or
  `build_market_model()` in
  `scripts/strategy_research/_btc_rsi_relative_volatility.py`), not resolved
  generically from an id string at runtime.

So "join trades against the Market Model's per-bar component context" is
not free — it requires recomputing Market Analysis components from the raw
OHLCV dataset by re-invoking the correct builder, which in turn requires
knowing *which builder* produced a given run's `market_model_id`.

### Decision

**Recompute, don't reconstruct from thin air — and add a forward-looking
identity field to make this generic for future runs.**

1. **Going forward**: `run_strategy_research.py`'s manifest write (already
   being touched for D-P18-01's assumptions fields) also gains a
   `strategy_source_ref` field — the Python module path that built the
   run's `StrategyModelDefinition` (already available at request time
   through the CLI's `strategy_file` config key per
   `docs/product/PRD-strategy-authoring.md`, or the invoking script's own
   `__file__` for script-launched runs). This is the one piece of new
   identity the codebase does not currently retain anywhere, and it is
   what makes `context_expectancy` computable for **any** future run
   without manual source-grepping.
2. **For the 3 existing legacy runs** (predating `strategy_source_ref`),
   resolved by direct source match, done once during this Wave 0 pass, not
   treated as a repeatable mechanism:
   - `eb80de6c9a6e3ab1` → `src/trading_framework/strategy/canonical_examples.py::build_canonical_strategy_model`
   - `4dbf98822e6ae591`, `8d050f623a034a58` → `scripts/strategy_research/_btc_rsi_relative_volatility.py::build_market_model`/`build_signal_model`/`build_strategy`
   Both files are still tracked on `main` and callable as-is.
3. **Computation**: for a resolved run, call its Market Model builder,
   recompute Market Analysis components over `source_dataset_ref` (a
   deterministic, already-existing, read-only capability — the same
   computation the original run already performed once to build the
   Market Model's expression inputs), inspect the resulting `AnalysisFrame`
   for every component the Market Model's expression actually references,
   and keep only outputs whose declared `OutputSchema` field is boolean or
   a small, fixed-cardinality categorical (a schema-level check at
   implementation time, not a guess from field name). Join those values to
   `trades.parquet` at `entry_signal_at`, then group per (component,
   label) per the PRD's existing field list.
4. **This is not a simulator rerun.** `BarSequentialSimulator` is not
   invoked; only the deterministic Market Analysis component-computation
   path is, which is the same code every Market/Signal Model already runs
   through once during original evaluation. Milestone 1's "no simulator
   rerun" framing still holds; its "purely from already-persisted
   trades/equity" framing does not, and is corrected in the PRD.
5. **A run whose Market Model references no boolean/categorical component**
   produces an empty `context_expectancy.parquet` for that run — reported
   as unavailable by the dashboard, not fabricated. Confirming this against
   real data is Milestone 1's own implementation step, not assumed here.

### Reasoning

- Recomputing Market Analysis components from raw OHLCV is exactly the
  operation the vision doc already permits the "owning research or
  analytics layer" to perform (compute and persist new metrics/state
  series) — it is categorically different from the dashboard inventing a
  metric at request time, which stays prohibited.
- Adding `strategy_source_ref` is the minimum new identity needed to make
  this mechanism generic rather than a one-time archaeology exercise;
  without it, every future run would need the same manual grep-and-match
  this Wave 0 pass just did for 3 runs, which does not scale and silently
  degrades to "unavailable" for any run whose builder isn't findable by
  hand.
- Not building a full market-model-id registry: out of proportion to this
  PRD. `strategy_source_ref` solves the actual need (resolve *this run's*
  builder) without a general lookup service nothing else asks for yet.

### Alternatives considered

- **Extend the Strategy Research simulation pipeline to persist per-bar
  component values at run time**, avoiding any recomputation. Rejected —
  materially larger (touches the simulator's own execution path, not just
  post-run analytics), and turns every future run's storage footprint into
  "however many components its Market Model touches," an open-ended cost
  the PRD's post-hoc-analytics framing was specifically trying to avoid.
- **Give up on `context_expectancy` for the 3 legacy runs**, scope it to
  future runs only. Rejected — the manual resolution took a few grep calls
  and both builder files still exist and are trivially callable; discarding
  known-recoverable evidence for no reason contradicts the project's
  "negative/incomplete evidence stays discoverable" rule applied to the
  data engineering itself.
- **A generic market-model-id registry** resolving any id to its builder.
  Rejected as premature — no other feature has asked for this, and
  `strategy_source_ref` is a narrower, sufficient fix.

### PRD correction

Milestone 1's `context_expectancy.parquet` bullet is corrected: it is not
purely post-hoc from `trades.parquet`/`equity.parquet`; it additionally
needs (a) the new `strategy_source_ref` manifest field and (b) recomputing
Market Analysis components from `source_dataset_ref` via the resolved
builder. See the PRD edit.

---

## D-P18-03 — Generic Strategy Research publication pipeline

### Problem statement

The PRD's Milestone 2 said to "extend the publication-boundary allowlist"
as though the only gap were the `frozenset[str]` allowlists in
`sanitizers.py`. Investigation found a bigger gap:

- `apps/dashboard/src/dashboard_app/publication/workspace.py` —
  "the only publication helper that reads the private workspace" — calls
  `catalog.scanner.list_runs()` and builds **only** identity
  (`research_catalog_entry`) `RawArtifactInput`s via
  `build_catalog_artifact_input`. It does not read
  `analytics/summary_metrics.parquet`, `equity.parquet` or
  `trades.parquet` for any run.
- The only code that ever produces a `strategy_research_run_summary`
  artifact is `scripts/dashboard/generate_btc_signal_quality_projection.py`
  — a one-off script hardcoding exactly two run ids
  (`_STRATEGY_BASELINE_RUN_ID`, `_STRATEGY_SCORED_RUN_ID`) for one named
  study release. The third existing run (`eb80de6c9a6e3ab1`) has a
  `research_catalog_entry` (from the generic scanner) but **no**
  `strategy_research_run_summary` at all in the committed
  `projection.json` — confirmed by direct inspection.
- This means today's "KPI summary" row is not actually generic across
  "every persisted run," contrary to ADR-0035's D061-01 eligibility
  principle ("every ... Strategy ... Research run is eligible when the
  build-time scanner can establish a supported workflow and a safe public
  identity ... Eligibility does not depend on ... manual featuring") — the
  richer evidence roles have silently regressed to manual featuring for
  this workflow, even though identity publication is already generic.

### Decision

**Build a generic Strategy Research evidence publisher, not just wider
allowlists.** Add a sibling function to `discover_catalog_inputs` (same
`publication/workspace.py` module, same build-time-only reading rule) that,
for every run `catalog.scanner.list_runs()` already discovers safely:

- reads `analytics/summary_metrics.parquet` and emits a
  `strategy_research_run_summary` `RawArtifactInput` using the (now
  expanded, see PRD) allowlist,
- reads `equity.parquet` and emits a new `strategy_research_equity_curve`
  role,
- reads `trades.parquet` and emits a new `strategy_research_trades` role
  (net_pnl, exit_reason only — never entry/exit price or quantity, which
  are not on any existing allowlist and are not asked for by the PRD),
- reads the 3 new Milestone-1 artifacts (`drawdown_episodes.parquet`,
  `context_expectancy.parquet`, `exposure.parquet`) and emits their roles,
- reads the (now-populated, per D-P18-01) `SimulationAssumptions` fields
  from `manifest.json` and folds them into the `strategy_research_run_summary`
  payload rather than a separate role, since they are per-run identity-
  adjacent facts, not a time series.

A run missing one of these files (e.g. a future run without a
Milestone-1 backfill) simply does not get that artifact role — same
"unavailable, not fabricated" handling the scanner already applies to
`verdict.json`.

`generate_btc_signal_quality_projection.py` is left as-is for whatever
Signal/Predictive artifacts are unique to that curated study release; this
decision only moves *Strategy Research* evidence onto the generic path,
since that workflow's identity is already generic per ADR-0035 and its
evidence should not be the exception.

### Reasoning

- Matches this project's own stated principle (ADR-0035 D061-01) that
  eligibility should not depend on manual featuring — the current
  Strategy Research evidence gap is exactly the kind of drift that
  principle exists to prevent, and Milestone 2 is the natural point to
  close it rather than add a 4th run to a hardcoded 2-run script.
- Reuses the existing scanner/workspace split cleanly: `scanner.py` already
  knows how to discover runs safely; `workspace.py` already owns "read
  more files from a discovered run's directory" (it already does this for
  `verdict.json`). Adding sibling reads for `equity.parquet`/
  `trades.parquet`/the new analytics files is the same pattern, not a new
  one.
- Keeps the "publisher copies approved facts, does not derive new ones"
  rule intact — every new role is a straight parquet-row-to-dict copy
  through an explicit allowlist, identical in kind to what
  `sanitize_strategy_research_run_summary` already does for 4 fields.

### Alternatives considered

- **Add the 4th run to the existing hardcoded script.** Rejected — treats
  a structural gap (no generic path for this workflow's evidence) as a
  one-off data problem; does not fix anything for the *next* new run
  either, which is exactly this PRD's overview-table goal.
- **Leave the allowlist-only framing and let the overview table silently
  show fewer runs with full evidence than exist.** Rejected — contradicts
  the PRD's own success metric ("all 3 persisted runs" listed, "no run
  silently dropped for missing an unrelated field") and ADR-0035's
  eligibility principle.

### PRD correction

Milestone 2's first bullet ("Extend the publication-boundary allowlist...")
is corrected to state the actual scope: a new generic publisher function in
`publication/workspace.py`, not only wider `frozenset[str]` allowlists. See
the PRD edit.

---

## D-P18-04 — Context-expectancy eligibility thresholds

### Problem statement

The PRD's Open Questions flagged whether `context_expectancy`'s
per-(component, label) groups need a minimum sample count before a metric
is marked eligible, to avoid a single-trade "expectancy" reading as
meaningful.

### Decision

**Reuse the existing two-tier `min_sample_size` /
`interpretation_min_sample_size` convention already used across Signal
Research analytics** (`research/analytics/aggregates.py`,
`distribution.py`, `grouping.py` — `metrics_eligible = sample_complete >=
min_sample_size`, with a stricter `interpretation_min_sample_size` gating
whether a value is presented as interpretable) rather than inventing a new
scheme.

Starting defaults, explicit and calibratable, not silently hardcoded:
`min_sample_size = 5` (below this, no expectancy value is computed for that
group at all — `null`, not zero), `interpretation_min_sample_size = 30`
(between 5 and 30, a value is computed and shown but flagged, matching how
`distribution.py` already separates "computable" from "interpretable").
Both become explicit parameters of the `context_expectancy` computation,
not literals.

### Reasoning

- This project already has exactly this two-tier eligibility concept,
  built for the same class of problem (a group's metric being computed
  from too few observations to mean anything). Reusing it keeps one
  eligibility vocabulary across Signal and Strategy Research rather than
  two subtly different ones a future reader has to reconcile.
- `spec.quality_rules.minimum_sample_size` (`map_definition.py:124`) shows
  this project's precedent of making the threshold a request-level
  parameter, not a constant — followed here too.
- Values chosen as principled starting points (5 as "not a single trade or
  two," 30 as the common small-sample rule-of-thumb already implicit in
  `interpretation_min_sample_size`'s naming elsewhere in this codebase),
  explicitly flagged for recalibration once real multi-context runs exist
  — matching Phase 19 Wave 0's precedent for proposing calibratable
  starting defaults rather than leaving a threshold unspecified.

### Alternatives considered

- **No minimum, show every group.** Rejected — the PRD's own question
  raised this risk explicitly; a 1-trade group's "100% win rate" is
  actively misleading, not merely unpolished.
- **A single threshold, no interpretation tier.** Rejected — the codebase
  already distinguishes "computable" from "interpretable" for this exact
  reason elsewhere; a single tier would be a step backward from existing
  practice, not a simplification.

---

## D-P18-05 — Sprint splitting

### Problem statement

The PRD's Milestone 1 → Milestone 2 ordering was set at PRD time, before
D-P18-02 and D-P18-03 revealed that `context_expectancy` and the
publication pipeline are each substantially larger than the PRD's original
framing implied. Does the two-milestone split still map to two sprints, or
does either milestone now need splitting?

### Decision

**Four sprints, not two**, split by the risk/dependency tiers this Wave 0
pass actually found:

1. **Sprint N — Milestone 1a (low-risk artifacts).** D-P18-01's manifest
   backfill (trivial — 3 known values, already verified) plus
   `drawdown_episodes.parquet` and `exposure.parquet` (both pure post-hoc
   from already-persisted `equity.parquet`/`trades.parquet`, no market-model
   dependency, no new identity field). Backfilled for all 3 existing runs
   in this sprint.
2. **Sprint N+1 — Milestone 1b (context expectancy).** The
   `strategy_source_ref` manifest field, the Market-Model-recomputation
   mechanism (D-P18-02), and the 3-run legacy backfill via the two known
   builders. Isolated from Sprint N because it is the one genuinely novel
   piece of engineering in Milestone 1 and should not block the two simple
   artifacts behind it.
3. **Sprint N+2 — Milestone 2a (generic publisher).** D-P18-03's
   `publication/workspace.py` extension covering all 5 new/expanded roles.
   Depends on Sprints N and N+1 having produced the artifacts it reads.
4. **Sprint N+3 — Milestone 2b (dashboard UI).** Overview table, run
   selector, and the 8-section detail view, consuming Sprint N+2's
   published data. The largest single UI surface in this PRD; kept as its
   own sprint rather than folded into N+2 so the publisher's correctness
   can be verified (e.g. against the committed `projection.json`) before
   UI work builds on it.

### Reasoning

- Mirrors Phase 19 Wave 0's own precedent (D-P19-06): split by actual
  discovered dependency/risk structure once real scope is known, not by
  the PRD's a-priori two-milestone framing, which undersized both
  `context_expectancy` and the publisher before this investigation.
- Sprint N and N+1 can, in principle, run in either order or even overlap
  (no dependency between them), but are kept as two sprints rather than
  one because D-P18-02's mechanism is the riskiest, least-precedented part
  of this whole PRD (per the PRD's own "Riskiest assumption" section) and
  benefits from being isolated rather than bundled with the two
  comparatively mechanical artifacts.
- Sprint N+2 must follow N/N+1 for real, not just nominally — it reads the
  files those sprints produce; sequencing here is a hard dependency.
- Sprint N+3 follows N+2 for the same hard-dependency reason (UI reads
  published data, not raw workspace files, per ADR-0034).

### Alternatives considered

- **Two sprints, matching the PRD's Milestone 1/Milestone 2 split exactly.**
  Rejected after sizing — Milestone 1 alone now contains one trivial task,
  two moderate tasks and one genuinely novel mechanism; bundling all four
  into one sprint repeats the exact risk Phase 19's Wave 0 flagged for a
  similarly oversized "Wave A + tooling" bundle.
- **Five sprints, splitting Milestone 1a further (assumptions backfill
  alone vs. drawdown/exposure).** Rejected — the assumptions backfill is a
  few-line change with no design risk; pairing it with the two equally
  mechanical post-hoc artifacts does not create the "tooling rushed to
  unblock components" risk that justified Phase 19's separate tooling
  sprint.

---

## Summary for maintainer review

| Decision | Recommendation | Status |
|---|---|---|
| D-P18-01 | All 3 existing runs used `SimulationAssumptions` defaults (verified by fingerprint match); backfill their manifests with the known default values, no recovery gap | ACCEPTED (maintainer, 2026-09-18) |
| D-P18-02 | `context_expectancy` requires recomputing Market Analysis components via a resolved builder, not pure post-hoc trades/equity reading; add `strategy_source_ref` to the manifest going forward; 3 legacy runs resolved by one-time source match | ACCEPTED (maintainer, 2026-09-18) |
| D-P18-03 | Build a generic Strategy Research evidence publisher in `publication/workspace.py` (5 new/expanded roles for every discovered run), not just wider allowlists; the current hardcoded 2-run script is the gap this closes | ACCEPTED (maintainer, 2026-09-18) |
| D-P18-04 | Reuse the existing `min_sample_size` (5) / `interpretation_min_sample_size` (30) two-tier convention for `context_expectancy` group eligibility | ACCEPTED (maintainer, 2026-09-18) |
| D-P18-05 | Split into 4 sprints: Milestone 1a (low-risk artifacts), Milestone 1b (context expectancy), Milestone 2a (generic publisher), Milestone 2b (dashboard UI) | ACCEPTED (maintainer, 2026-09-18) |

All five decisions above are Accepted (maintainer, 2026-09-18). Per this
project's governance convention, architecture triage investigated and
recommended; the maintainer's explicit review and acceptance make them
binding on implementation from this point forward. D-P18-02 and D-P18-03
correct factual statements in the PRD itself — those edits are applied
directly to `docs/product/PRD-dashboard-strategy-research-evidence.md`,
not left as a divergence between the two documents.
