# Phase 18 (Increment 18B) — Wave 0 Decisions

```text
Status: ACCEPTED (maintainer, 2026-09-22)
Basis:  docs/product/PRD-dashboard-signal-research-evidence.md (APPROVED)
        docs/planning/roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md
        apps/dashboard/src/dashboard_app/catalog/paths.py as on main
        src/trading_framework/infrastructure/storage/paths.py as on main
        scripts/signal_research/analyze_signal_research.py as on main
        src/trading_framework/application/signal_research/persist_analytics.py as on main
        user_data/research/market_research/runs/* on disk (6 runs)
```

Architecture triage investigated all four of the PRD's Handoff items
directly against the codebase and the 6 real runs, rather than treating
them as open design questions to answer from first principles — the same
discipline 18A's Wave 0 applied. Three of the four turned out to need no
new code at all, only correctly invoking tools that already exist. The
maintainer accepted all decisions below on 2026-09-22.

---

## D-P18B-01 — Root-mismatch fix mechanism

### Problem statement

The Research Catalog shows "Signal: 0" because
`discover_catalog_inputs` (the generic identity scanner) is only ever
called with `--storage-root user_data/workspace`, and
`market_research_runs_dir` resolves under whichever root it is given —
`workspace/research/market_research/` does not exist. The real data
lives under `user_data/research/market_research/runs/`.

### Decision

**Not a historical accident — a genuinely different physical root that
the dashboard's own generator script already treats as a second, first-
class root (`--evidence-root`), just not yet for identity.** Both
`src/trading_framework/infrastructure/storage/paths.py`'s
`research_root(workspace) = workspace / "research"` and the dashboard's
mirror in `catalog/paths.py` apply the exact same `<root>/research/...`
convention — the difference is which value gets passed as `<root>`.
Verified directly: running the existing
`scripts/signal_research/analyze_signal_research.py --storage-root
user_data --run-id <id>` (i.e., `<root> = user_data`, not
`user_data/workspace`) resolves and writes to exactly
`user_data/research/market_research/runs/<id>/...`. Signal Research has
always used `user_data` as its effective root; Strategy Research's newer
`StrategyResearchDatasetRepository` convention uses `user_data/workspace`
instead — two real, independently-evolved roots, not a bug in either one
alone, only in the dashboard never scanning both for identity.

**Fix: `generate_public_projection.py` calls `discover_catalog_inputs`
against both `args.storage_root` and `args.evidence_root`, merging the
results** — the same two CLI arguments the script already accepts and
already passes separately to `discover_research_evidence_inputs`
(evidence_root) and `discover_catalog_inputs` (storage_root today, only).
No new CLI argument, no migration of physical data, no reconciling the
two roots into one.

### Reasoning

- The two roots are both already named as CLI concepts in this exact
  script (`--storage-root`, `--evidence-root`) — the fix is completing
  an asymmetry the script itself already half-solved, not inventing new
  plumbing.
- No collision risk: Strategy Research data lives correctly only under
  `user_data/workspace/`, Signal Research data lives correctly only under
  `user_data/research/`; scanning both for identity finds each workflow's
  real runs exactly once.
- The 44 robustness-experiment child runs under
  `user_data/research/strategy_research/runs/` are already excluded by
  `scanner.py`'s existing `experiment_id` filter (confirmed in 18A's
  Sprint 070) regardless of which root scans them — scanning
  `evidence_root` a second time does not resurrect that already-solved
  problem.

### Alternatives considered

- **Migrate/symlink Signal Research's physical data under
  `user_data/workspace/`.** Rejected — touches real on-disk data for a
  purely cosmetic path unification; the two-root scan is a smaller,
  safer, purely additive change.
- **Reconcile the two roots into one going forward via an ADR.**
  Rejected as premature — nothing about *how* new data is written needs
  to change, only *where the dashboard looks* for already-correctly-
  written data. Revisit only if a future workflow adds a third
  inconsistent root.

---

## D-P18B-02 — Backfilling the 3 `signal_research.v2` runs

### Problem statement

3 of the 6 real runs (`25ca54931e1f16e6`, `3aae07449003f025`,
`49e89db334b67d2b`, all created 2026-09-15) have raw
`occurrences.parquet`/`outcomes.parquet`/`context.parquet` but no
`analytics/` folder, so `discover_research_evidence_inputs` silently
skips them. Does closing this gap need a new dual-format reader in the
dashboard, or can it reuse something that already exists?

### Decision

**No new code. Backfill via the existing
`scripts/signal_research/analyze_signal_research.py --storage-root
user_data --run-id <id> --persist-analytics`, one of the 3 runs already
verified directly:** running it against `25ca54931e1f16e6` produced a
complete `analytics/` folder (`summary_metrics.parquet`,
`distribution_summaries.parquet`, `conditional_comparison.parquet`,
`metric_histograms.parquet`, `quality_warnings.parquet`,
`summary.json`) from its existing raw files, no new raw data, no
simulator/analysis-engine change — `analyze_signal_research_run` (the
underlying application function) already reads exactly this raw shape.

**One real gap found**: this run's backfilled `analytics/` is missing
`grouped_summaries.parquet`, present for the 3 already-published runs.
Producing it requires an explicit `--definition` file (group-by
dimensions) that these 3 newer runs never had one authored for. Backfill
proceeds without it — `grouped_summaries` absence is handled the same
"unavailable, not fabricated" way any other missing table already is
(per the dashboard's existing multi-table convention) — and authoring a
definition file for these runs is left as a candidate future task, not a
blocker for this PRD's Milestone 1.

### Reasoning

- `analyze_signal_research_run` / `persist_signal_research_analytics` are
  exactly the "compute `analytics/`'s shape from raw occurrences/outcomes"
  step this PRD's Open Questions asked whether to build — it already
  exists, already dual-writes JSON + every named Parquet table, and was
  verified against real data in this Wave 0 pass rather than assumed.
- No architecture decision needed on "backfill vs. dual-format read" —
  backfill is strictly cheaper once the existing tool is known, and
  produces output in the exact same shape `discover_research_evidence_inputs`
  already expects, requiring zero changes to the read path.

### Alternatives considered

- **Extend `discover_research_evidence_inputs` to read the raw
  `occurrences`/`outcomes`/`context` shape directly, computing aggregates
  in the dashboard's publication layer.** Rejected — this is exactly the
  kind of metric computation ADR-0034/0035 keeps out of the publication
  layer; `analyze_signal_research_run` already exists specifically to own
  this computation in the research/analytics layer.
- **Author `--definition` files now to also backfill `grouped_summaries`.**
  Deferred, not rejected — no maintainer-set group-by dimensions exist
  yet for these 3 runs' contexts; inventing one to fill a table is worse
  than an honest "unavailable."

---

## D-P18B-03 — Adjusted forward drift: shrinkage formula and constant

### Problem statement

No shrinkage/empirical-Bayes precedent exists anywhere in this codebase.
The PRD committed to the *technique* (sample-size-weighted shrinkage
toward the global mean) but left the exact formula and prior-strength
constant open, per its own Riskiest assumption.

### Decision

**Standard Bayesian-average shrinkage, prior strength `k` set to the
Signal Research analytics package's own existing
`DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE` constant (100), not a new
number:**

```text
adjusted_mean = (sample_size_complete * group_mean + k * global_mean) / (sample_size_complete + k)
```

applied per `grouped_summaries` row (one (context, horizon) group),
where `global_mean` is that run's own ungrouped forward-return mean at
the same horizon (already computable from `distribution_summaries` or
directly from `outcomes.parquet`), and `k = 100`.

### Reasoning

- Reuses this project's own existing interpretability threshold
  (`analyze_signal_research.py` imports
  `DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE`, already used to mark a
  distribution "interpretable" at `sample_size_complete >= 100`) instead
  of inventing an unrelated constant — a group shrinks roughly half-way
  toward the global mean exactly at the same sample size this codebase
  already calls "not yet reliably interpretable," a consistent, not
  coincidental, alignment.
- Checked against real data, not assumed: the one real run inspected
  (`a6dff1e5365fe839`) has `grouped_summaries` sample sizes from 209 to
  7,551 (median 517) — all comfortably above `k=100`, so this run's own
  adjusted means will sit close to their raw means (little visible
  shrinkage) while a smaller future run's rarer context/horizon
  combinations would shrink more visibly. This matches the PRD's
  Riskiest assumption's own criterion ("shrinks measurably... in
  proportion to sample size") without over- or under-shrinking the one
  real run available to check against.
- Matches Phase 19 Wave 0's precedent of anchoring a new constant to an
  existing, already-reviewed one rather than a bare guess, while still
  being explicitly flagged (in the PRD) as recalibratable.

### Alternatives considered

- **A new, standalone prior-strength constant** (e.g. 30, matching 18A's
  `context_expectancy` interpretation threshold). Rejected — that
  threshold belongs to a different workflow's analytics package with its
  own sample-size regime (Strategy Research trades: tens to low
  thousands) and Signal Research's own package already has its own,
  more directly applicable constant.
- **A fixed shrinkage percentage** (e.g. always shrink 20% toward the
  mean). Rejected — ignores sample size entirely, exactly the "dashboard
  applies no shrinkage, adjustment happens once, correctly, upstream"
  discipline the vision doc asks for; a fixed percentage is not
  principled by group size at all.

---

## D-P18B-04 — `context_persistence` table shape

### Problem statement

The PRD's Open Questions proposed generalizing 18A's `drawdown_episodes`
shape (`episode_id`/`peak_at`/`trough_at`/`duration_bars`/
`recovery_bars`) to a run-length encoding of any categorical context
series, without fixing it as binding.

### Decision

**Confirmed as proposed, with column names generalized away from
drawdown-specific terms:**

```text
run_id, component_id, label, start_at, end_at, duration_bars
```

One row per maximal run of consecutive bars where the resolved
`STATE`-kind component (per `state_context_aliases`, reused from 18A's
D-P18-02) holds the same `label`. No `recovery_bars`-equivalent field —
unlike a drawdown episode, a context run has no asymmetric "recovery"
concept; `end_at` is simply `null` for a run still open at the series'
last observation (the same "not yet resolved" honesty 18A's
`recovery_bars=null` already established, renamed here since "recovery"
does not apply to a context label).

### Reasoning

- Directly reuses 18A's already-implemented, already-tested run-length-
  encoding *algorithm* (`compute_drawdown_episodes`'s peak-to-next-peak
  loop is structurally a run-length encoder over a derived boolean
  series; `context_persistence` needs the same loop over the raw
  categorical series directly, an even simpler case since there is no
  "peak"/"trough" asymmetry to track).
- Column naming avoids importing drawdown-specific vocabulary
  (`peak_at`/`trough_at`) into a context-timeline concept where it would
  not describe anything real, per this project's naming-convention
  discipline (IDEA-027's rule, applied here to artifact schemas, not just
  component names: a name should describe the fact, not borrow a
  metaphor from an unrelated domain).

### Alternatives considered

- **Reuse `drawdown_episodes`'s exact column names for
  `context_persistence`** (i.e. `peak_at`→`start_at` only implicitly, via
  aliasing). Rejected — `peak_equity`/`trough_equity` have no context-
  timeline equivalent at all; a partially-reused schema with some columns
  meaningless is worse than a small, purpose-named one.

---

## Summary for maintainer review

| Decision | Recommendation | Status |
|---|---|---|
| D-P18B-01 | `generate_public_projection.py` scans both `storage_root` and `evidence_root` for catalog identity (was: `storage_root` only) | ACCEPTED (maintainer, 2026-09-22) |
| D-P18B-02 | Backfill the 3 unpublished runs via the existing `analyze_signal_research.py --persist-analytics` script, no new code; `grouped_summaries` deferred for these 3 (needs a definition file nobody has authored) | ACCEPTED (maintainer, 2026-09-22) |
| D-P18B-03 | Bayesian-average shrinkage, `k=100` (reusing `DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE`), for `adjusted_forward_drift` | ACCEPTED (maintainer, 2026-09-22) |
| D-P18B-04 | `context_persistence` table: `run_id, component_id, label, start_at, end_at, duration_bars`; `end_at` null for an unresolved run | ACCEPTED (maintainer, 2026-09-22) |

All four decisions above are Accepted (maintainer, 2026-09-22). Per this
project's governance convention, architecture triage investigated and
recommended; the maintainer's explicit review and acceptance make them
binding on implementation from this point forward.
