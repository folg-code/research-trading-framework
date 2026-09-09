# Sprint 058: Signal Quality Scoring (Phase 16, increment 16C)

Status: COMPLETE (6/6 tasks, 2026-09-09). ADR-0033 (score delivery
boundary) is ACCEPTED. Working PRs #472-#479, integration into
`sprint/signal-quality-scoring` / `main` a separate, maintainer-reviewed
step (per `AGENTS.md`'s Sprint Git Workflow).

Goal: Build the phase's key vertical slice — a `SIGNAL_QUALITY` predictive
study over signal occurrences, a promotable-family estimator comparison, a
scorer-reference contract Strategy Research can name from a config, and one
worked example on real data comparing a strategy's baseline vs.
score-filtered variants. TD-021 and TD-022's promotion branch are repaid
inside this sprint; TD-029 is explicitly re-deferred to 16G, in writing and
in code.

Sources:

- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3 — 16C's full,
  maintainer-negotiated scope (authoritative; every completion criterion,
  dependency, risk, and out-of-scope item below is drawn from it, not
  paraphrased loosely).
- §13H.8 (binding rules for the whole phase), §13H.9 row 2 (score-delivery
  ADR, this sprint's), §13H.12 Q6 (TD-029 scope, resolved Option B),
  §13H.13 (registry entries this sprint closes: TD-021, TD-022's promotion
  branch).
- `docs/adr/ADR-0033-predictive-score-delivery-boundary.md` — the central
  design decision (score delivery boundary), PROPOSED, drafted for this
  sprint.
- `docs/adr/ADR-0029-promoted-predictive-artifact.md`,
  `docs/adr/ADR-0031-predictive-sample-spec-and-task.md`,
  `docs/adr/ADR-0032-predictive-run-verdict-artifact.md` — consumed as
  binding constraints, not reopened.
- `docs/planning/TECHNICAL_DEBT.md` (TD-021, TD-022, TD-029),
  `docs/planning/PROBLEM_REGISTRY.md`.

Architecture triage: `docs/adr/ADR-0033-predictive-score-delivery-boundary.md`
(ACCEPTED, 2026-09-08).

## Scope

In scope:

- A `SIGNAL_QUALITY` `PredictiveTask` study over `signal_occurrences` samples
  (16B) with a forward-outcome quality label (binary threshold or
  continuous).
- Estimator comparison and score-threshold sensitivity analysis, restricted
  to promotable families (`sklearn.ridge`, `sklearn.elastic_net`,
  `sklearn.logistic`) for anything that may gate a strategy.
- The scorer-reference contract: how a Strategy Research config identifies
  which fitted (promoted) model produces the score (ADR-0033).
- A new Strategy Research condition consuming a predictive score as an
  ordinary gating condition, evaluated in-process under `available_at`
  (ADR-0033), with config-load-time refusal of non-promotable families,
  covered by a test.
- A baseline-vs-filtered comparison on real data: signal counts,
  performance, rejected losers, rejected winners, false rejects, fold
  stability, feature importance.
- Closing documentation: TD-021 confirmed against a real consumer, TD-022's
  promotion branch repaid and asserted by test, TD-029 re-deferred to 16G in
  `TECHNICAL_DEBT.md`.

Out of scope:

- Trade-outcome and no-trade models (16F).
- Promotion of any scorer to runtime or dry-run (16G).
- Any change to `MODEL_FAMILY_ALLOWLIST` whatsoever (Q6 = Option B).
- Designing the tree/neural serialization path (16G, its own ADR).
- Replacing any rule-based strategy with an opaque model.
- TD-022's residual (never-promoted research-run blob opacity) — stays open.
- Parity testing (PRB-013) and Strategy Research family/planner machinery
  (PRB-020/PRB-012) — those are 16G and 16E respectively; do not pull them
  forward into this sprint.
- The Quant Lab Dashboard (16D) — no dashboard change in this sprint.
- Pre-materialized score-column artifact (ADR-0033 Option B) — not built
  unless a follow-up decision reopens it.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `SIGNAL_QUALITY` label builder + sample wiring: a runnable `PredictiveStudySpec` over `signal_occurrences` with a forward-outcome quality label, through the unmodified Phase 10 pipeline | 16B (merged, `main`), Phase 10 pipeline | TBD | standard | Done | #473 |
| T002 | Estimator comparison + threshold sensitivity report over the T001 study, promotable families only for anything gate-eligible; tree/neural remain usable for research-only comparison, clearly separated | T001 | TBD | standard | Done | #474 |
| T003 | Scorer-reference contract: fingerprint resolution via `PromotedArtifactRepository` at config load time; named-error refusal for (a) missing fingerprint, (b) non-allowlisted family; boundary test asserting Strategy Research imports nothing from `infrastructure/ml/` | ADR-0033 (accepted), ADR-0029 promotion store | TBD | high | Done | #475, #476 |
| T004 | Strategy Research condition: predictive score gate, evaluated in-process via the unmodified NumPy evaluator under `available_at`; no-look-ahead test (score computed only from features available at occurrence time); simulator (fills/slippage/sizing/ledger) unchanged | T003 | TBD | high | Done | #477 |
| T005 | Worked example on real data: one strategy, its scorer, baseline vs. score-filtered variants, comparison written down whether or not the score helps (a negative result is a complete outcome) | T001, T002, T004, Sprint 052 real-data pipeline | TBD | standard | Done | #478 |
| T006 | Closing documentation: apply 16A's verdict to the T005 run; record TD-021 confirmation, TD-022 promotion-branch repayment (asserted by test, cited here), TD-029 re-deferral to 16G, in `TECHNICAL_DEBT.md` and this sprint's Closeout | T001–T005, 16A (merged, `main`) | TBD | low | Done | #TBD |

## Acceptance criteria

Drawn directly from §13H.3's completion criteria — do not weaken:

- One end-to-end worked example on real data: a strategy, its scorer, and
  both simulated variants, with the comparison written down whether or not
  the score helps.
- The simulator is not bypassed. Entries, exits, fills, slippage,
  commissions, sizing, the trade ledger and the equity curve stay owned by
  Strategy Research. A prediction is never treated as a trade.
- The score enters simulation only as a declared strategy condition,
  evaluated under the same `available_at` discipline as every other
  component — no look-ahead through the model.
- A negative result ("the score does not improve the strategy") is a
  complete, reportable outcome. So is "only the linear model is usable as a
  gate."
- TD-021 is repaid: the scorer-reference contract is written down, the
  worked example exercises it, and ADR-0024 condition 5 is confirmed
  sufficient (no registry introduced as a side effect).
- TD-022's promotion branch is repaid: the shipped score path depends on no
  opaque blob, asserted by a test, not by convention. The remaining
  residual is stated explicitly in the closing notes.
- TD-029 is explicitly re-deferred, in writing and in code: config-load-time
  refusal of a non-promotable family as a strategy gate, covered by a test,
  re-deferral recorded against 16G.
- `MODEL_FAMILY_ALLOWLIST` is unchanged by this sprint. Any diff to it is
  out of scope by definition.

## Integration risks

- **Threshold overfitting** — the score cutoff that flatters the backtest is
  trivial and invalidating. Mitigation: threshold sensitivity is a required
  output (T002), the cutoff is chosen out of sample.
- **Double-dipping the same data** for both signal design and score
  training. Mitigation: purged walk-forward discipline applies to the
  *combined* workflow, not the model in isolation.
- **Runtime model loading creeping back in** — the key design question
  (ADR-0033) explicitly forecloses this; T003/T004 must each carry a test
  asserting no `infrastructure/ml` / sklearn import reaches Strategy
  Research's condition module.
- **Option B's honest cost** — 16C can only claim "the best *promotable*
  model gates the strategy." T005's write-up must say so explicitly, not
  imply the comparison was unrestricted.
- Survivorship of the interesting cases: rejected winners matter as much as
  rejected losers and must be reported in T005.

## Closeout

- **Integrated checks:** Full unit suite green at every task boundary
  (final count: 1785 passed, 4 skipped [torch, opt-in extra], 0 failed —
  `tests/unit -q`), full `mypy` clean (900 source files), `ruff
  check`/`format --check` clean on every changed file. No regression was
  introduced in any of T001-T005's six PRs; each was independently
  fresh-context reviewed (per `.claude/WORKFLOW.md`'s risk table for
  `standard`/`high` risk work) before the next task built on it. One real
  bug was found and fixed mid-sprint by a reviewer (T004: a scorer feature
  needing more warm-up history than the strategy's own market/signal
  components was silently starved of it — `run_strategy_research.py`'s
  `_resolve_evaluation_inputs` now widens the preload for both) — see
  PR #477's commit history. A second real bug was found by running the
  suite, not by review (T005: the worked-example scripts were initially
  placed under the wave4-restricted `scripts/predictive_research/`,
  caught by `test_architecture_boundaries.py`; moved to
  `scripts/strategy_research/`).
- **Documentation reconciliation:**
  - `docs/planning/CURRENT_STATUS.md`, `docs/planning/ROADMAP.md` §13H row
    for 16C, `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3
    completion note — updated to COMPLETE alongside this Closeout.
  - `docs/planning/TECHNICAL_DEBT.md` — TD-021 marked **REPAID** (16C
    confirmed a bare fingerprint reference suffices from a real Strategy
    Research consumer; no registry, index, or `latest` pointer
    introduced). TD-022 stays ACCEPTED with its promotion branch
    confirmed repaid (asserted by
    `test_strategy_research_does_not_import_ml_infrastructure`, not
    merely convention) and its never-promoted-blob residual explicitly
    still open. TD-029 stays ACCEPTED, re-deferred to 16G in both writing
    and code (`ScoreConditionFamilyRefusedError`, asserted by test;
    `MODEL_FAMILY_ALLOWLIST` unchanged, asserted by test).
  - `docs/adr/README.md` index — ADR-0033 already listed ACCEPTED.
  - `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` (T005) carries the 16A
    verdict applied to the T005 predictive run
    (`run_id=2ef6426b3cc06463`): **INCONCLUSIVE** (rule O3 fired — a
    positive pooled baseline delta over `RANDOM_PERMUTATION`, but a
    per-fold win rate of only 0.5, below the 0.667 threshold R4/O2
    require for a stronger verdict). This is consistent with, not a
    contradiction of, T005's own "the score does not meaningfully filter
    this strategy's trades" finding — a positive-but-inconsistent pooled
    effect is exactly what INCONCLUSIVE is for.
- **Review:** Every PR (#472-#478) received an independent fresh-context
  review per `.claude/WORKFLOW.md`'s risk table before the next task
  built on it. No open review findings remain unaddressed; optional
  (non-blocking) findings from T002/T004/T005's reviews are recorded in
  their own PR threads, not repeated here.
- **Remaining work:** None for 16C itself. Explicitly out of scope and
  carried forward as directional increments per
  `PHASE_16_QUANT_WORKBENCH.md` §13H: 16D (Quant Lab Dashboard), 16E
  (Strategy Families / PRB-020 / PRB-012), 16F (Trade Outcome Models),
  16G (Promotion Candidate Gate / PRB-013 / TD-029's remaining
  repayment). Integration of `sprint/signal-quality-scoring` into `main`
  is a separate, maintainer-reviewed step, per `AGENTS.md`'s Sprint Git
  Workflow — not performed as part of this Closeout.
