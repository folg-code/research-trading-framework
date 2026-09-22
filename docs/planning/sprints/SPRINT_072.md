# Sprint 072: Signal Research Root-Mismatch Fix and Backfill (Phase 18, 18B Milestone 1)

Status: **Open** — maintainer authorized opening this sprint 2026-09-22.
Goal: Implement Phase 18 18B's Milestone 1 — the root-mismatch fix and
3-run backfill decided in Wave 0 (D-P18B-01/02). Regenerate the committed
`projection.json` for real, as 18A's Sprint 070 did for Strategy Research.

Sources:

- `docs/product/PRD-dashboard-signal-research-evidence.md` (APPROVED 2026-09-18)
- `docs/planning/roadmap/PHASE_18B_WAVE0_DECISIONS.md` — D-P18B-01 (root
  mismatch), D-P18B-02 (backfill via existing tooling), both ACCEPTED
  (maintainer, 2026-09-22)
- `scripts/dashboard/generate_public_projection.py` (the orchestrator this
  sprint fixes)
- `scripts/signal_research/analyze_signal_research.py`,
  `scripts/strategy_research/backfill_run_analytics.py`,
  `scripts/strategy_research/backfill_context_expectancy.py` (existing
  tools this sprint reuses, none modified)

Architecture triage: **one finding beyond Wave 0's four decisions,
surfaced during implementation, not assumed away** — 18B's PRD stated
"Strategy Research's own root is already correct (18A)" as a Non-goal.
Verifying D-P18B-01's fix by actually running it (not just reading code)
found a 4th real Strategy Research run,
`f4f3093ec5ec3f3a` (canonical example, `high_vol_higher_low_fixed_exit`
on `NQ.c.0`, created 2026-07-17 — older than any of the 3 runs 18A ever
knew about), living under the exact same second root as Signal Research.
18A's own Non-goal assumption was wrong. Flagged to the maintainer
directly rather than silently left as a bare, evidence-less catalog
entry; the maintainer chose to fold the same fix into this sprint. See
Scope.

## Scope

In scope:

- **T001 — Root-mismatch fix in `generate_public_projection.py`.**
  `discover_catalog_inputs` now scans both `--storage-root` and
  `--evidence-root.parent` (the latter because `discover_catalog_inputs`'s
  internal path convention expects "the workspace root" and appends
  `research/` itself, unlike `discover_research_evidence_inputs`, which
  expects `--evidence-root` to already be that directory — a real,
  documented asymmetry between the two path conventions, not a typo).
  `discover_strategy_research_evidence_inputs` (Sprint 070) is extended
  the same way, closing the just-found 4th-run gap in the same change.
- **T002 — Backfill the 3 unpublished `signal_research.v2` Signal
  Research runs.** Via the existing
  `scripts/signal_research/analyze_signal_research.py --persist-analytics`,
  no new code (D-P18B-02). Run against `25ca54931e1f16e6`,
  `3aae07449003f025`, `49e89db334b67d2b`.
- **T003 — Backfill the newly-found 4th Strategy Research run** to parity
  with 18A's other 3: `scripts/strategy_research/backfill_run_analytics.py`
  (manifest assumptions, `drawdown_episodes`, `exposure`) and
  `scripts/strategy_research/backfill_context_expectancy.py`
  (`strategy_source_ref` resolved to
  `trading_framework.strategy.canonical_examples:build_canonical_strategy_model`
  — the same canonical-example builder 18A's `eb80de6c9a6e3ab1` already
  uses, confirmed by identical `strategy_model_id`/`market_model_id`/
  `signal_model_id`). No new code — the exact same Sprint 068/069 tools.
- **T004 — Regenerate the committed `projection.json` for real** and
  update the 3 existing tests that hardcoded the pre-fix catalog counts.

Out of scope (per the PRD and Wave 0):

- **`mfe_mae_pairs`, `adjusted_forward_drift`, `context_timeline`,
  `context_persistence`** — Milestone 1's remaining new artifacts
  (D-P18B-03/04's shrinkage formula and table shape), a separate,
  later sprint (Sprint N+1), matching 18A's Milestone-1a/1b split.
- **Authoring a `--definition` file** for the 3 backfilled Signal
  Research runs to also produce `grouped_summaries` — deferred per
  D-P18B-02, not this sprint's job.
- **18B's Milestone 2 (dashboard UI)** — later, after Milestone 1
  completes, per the PRD's hard sequencing gate.

## Decisions

Binding detail and rationale:
[`PHASE_18B_WAVE0_DECISIONS.md`](../roadmap/PHASE_18B_WAVE0_DECISIONS.md)
D-P18B-01/02, both ACCEPTED (maintainer, 2026-09-22). The 4th-Strategy-run
finding and its fold-in are this sprint's own implementer-level
discovery, confirmed with the maintainer directly rather than assumed —
see Architecture triage above.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Both discovery functions scan `evidence_root.parent` in addition to `storage_root` | None | `scripts/dashboard/generate_public_projection.py` | standard | Done | — |
| T002 | 3 Signal Research runs backfilled via existing tooling | None | (workspace data only, no code) | standard | Done | — |
| T003 | 4th Strategy Research run backfilled to 18A parity | T001 (found while verifying it) | (workspace data only, no code) | standard | Done | — |
| T004 | Committed `projection.json` regenerated; 3 tests' hardcoded counts updated | T001, T002, T003 | `apps/dashboard/publication_data/`, `apps/dashboard/tests/` | standard | Done | — |

## Branch and PR rules

Per the `git-workflow` skill defaults; matches Sprints 068-071's
precedent — bundled in one PR (T001-T004 are one coherent fix + data
regeneration).

```text
main
  └── sprint/dashboard-signal-research-evidence-m1
        └── feat/signal-research-root-mismatch-fix  (T001-T004)
```

## Acceptance criteria

- Research Catalog shows the true counts (Market 1, Signal 5, Strategy 4,
  Robustness 1, Predictive 4 — 15 total, not the pre-fix 7).
- All 6 real Signal Research runs are projected via `signal_research_evidence`.
- All 4 real Strategy Research runs are projected via
  `strategy_research_evidence`.
- No `DuplicateArtifactIdError` on regeneration (verified by actually
  running the generator, not just reasoning about ids).
- `pages/1_Research_Catalog.py`, `pages/4_Market_and_Signal_Research.py`
  and `pages/6_Strategy_Research.py` all still render correctly against
  the regenerated bundle, verified in a running dashboard.
- Dashboard suite green (with the 3 count-assertion tests updated, not
  disabled); `ruff check`, `ruff format --check`, `mypy` clean.

## Closeout

**Status: DONE.** All 4 tasks (T001-T004) implemented and verified.

**Implementation**:

- `scripts/dashboard/generate_public_projection.py` — both
  `discover_catalog_inputs` and `discover_strategy_research_evidence_inputs`
  now also scan `args.evidence_root.parent`.
- `apps/dashboard/publication_data/projection.json` — regenerated: 32
  artifacts (was 20 after Sprint 070), 26 projected inputs, 0 skipped
  (was 3 skipped before this sprint). `research_catalog_entry`: 15 (was
  7). `signal_research_evidence`: 6 (was 3). `strategy_research_evidence`:
  4 (was 3 — the newly-found run).
- `apps/dashboard/tests/test_projected_research_evidence.py`,
  `test_public_catalog_acceptance.py`, `test_public_catalog_index.py` —
  3 hardcoded-count assertions updated to the new, correct totals, each
  with a comment explaining why the number changed.

**Backfill result** (all outside git, `user_data/` is gitignored):

- `25ca54931e1f16e6`, `3aae07449003f025`, `49e89db334b67d2b` — full
  `analytics/` folder (summary_metrics, distribution_summaries,
  conditional_comparison, metric_histograms, quality_warnings) via the
  existing `analyze_signal_research.py --persist-analytics`.
  `grouped_summaries` correctly absent (needs a `--definition` file none
  of these runs have — deferred per D-P18B-02, not fabricated).
- `f4f3093ec5ec3f3a` — manifest assumptions, `drawdown_episodes`,
  `exposure`, `context_expectancy`, `strategy_source_ref` via the
  existing Sprint 068/069 backfill scripts.

**Manual verification**: started the dashboard against the regenerated
bundle. Research Catalog shows the corrected 1/5/4/1/4 counts (15 runs
total, "Showing 15 of 15"). Strategy Research's overview table lists all
4 runs including the newly-found one, distinguishable by dataset (`NQ.c.0`
vs `BTCUSDT.P`) from the pre-existing canonical example. No server errors
on either page.

**Tests**: dashboard suite **297 passed** (unchanged count — 3 existing
tests updated in place, none added, since this sprint is a data/config
fix, not new behavior). Root suite unaffected: **2057 passed**. `ruff
check`, `ruff format --check`, `mypy` (full project-configured file set —
an isolated single-file mypy run on the changed script produces a false
"missing py.typed marker" error because `apps/dashboard/src` is outside
its own analysis scope; the full-scope run this project's own pre-commit
hook actually uses passes clean) all clean.

**Acceptance criteria**: all met — see Manual verification and Tests
above.

**Remaining work**: Sprint N+1 (Milestone 1's remaining new artifacts —
`mfe_mae_pairs`, `adjusted_forward_drift`, `context_timeline`,
`context_persistence`, per D-P18B-03/04) is next, followed by Milestone 2
(dashboard UI).
