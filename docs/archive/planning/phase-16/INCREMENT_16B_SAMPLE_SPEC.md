# Increment 16B — SampleSpec Foundation

Detailed outcome and criteria from the accepted phase plan. Return to the [Phase 16 index](../../../planning/roadmap/PHASE_16_QUANT_WORKBENCH.md).

## 13H.2 — Increment 16B — SampleSpec Foundation

### Purpose

Predictive rows today are effectively evaluation bars. That is one question
("what happens next, from anywhere?") and it is the *least* interesting one
for a strategy-centric framework. An explicit sample-universe contract lets
the same pipeline answer materially different questions without forking it.

### Expected capabilities

- An explicit `sample:` block in `PredictiveStudySpec`, defaulting to today's
  behaviour so every existing spec keeps working unchanged.
- Two kinds only in this increment:

```text
every_bar             the current behaviour, made explicit
signal_occurrences    rows are a Signal/Strategy Model's firings
```

- `strategy_trades` and `labelled_setups` are declared in the contract's
  design intent but **not implemented here** (16F, and a later discretionary
  labelling increment).
- A higher-level `PredictiveTask` distinguishing the research question from
  the statistical task type. `REGRESSION | CLASSIFICATION` remains the
  estimator's task type; `PredictiveTask` records intent:
  `FORWARD_RETURN`, `SIGNAL_QUALITY`, `TRADE_OUTCOME`, `REGIME_CLASSIFICATION`,
  `VOLATILITY_FORECAST`, `NO_TRADE_FILTER`,
  `DISCRETIONARY_SETUP_CLASSIFICATION`. Only the kinds a shipped sample/label
  builder supports are accepted at load time; the rest are reserved names, not
  silently-accepted no-ops.
- Label builders become the extension point. The framework's next unit of
  value is more **label builders**, not more estimator classes.

### Primary flow

```text
PredictiveStudySpec
  = DatasetRef + range + SampleSpec + FeatureSpec[] + LabelSpec
      + PredictiveTask + purged walk-forward split
  -> sample universe resolved FIRST
  -> features computed AT those rows
  -> labels built for those rows
  -> the unchanged fit / fold / metrics path
```

### Completion criteria

- Every existing `PredictiveStudySpec` still loads and produces an identical
  `definition_hash`-comparable result under the `every_bar` default.
- A `signal_occurrences` study builds a dataset whose row count equals the
  Signal Model's firing count over the same range — asserted, not assumed.
- Purge/embargo semantics are re-derived for irregularly-spaced rows and shown
  correct; leakage guards (ADR-0023 §4) are strengthened or unchanged, never
  relaxed to accommodate a new sample kind.
- CI stays synthetic-only and network-free (ADR-0023 §8 untouched).

### Dependencies

- Phase 10 pipeline; Phase 5 Signal Research semantics.
- **Entry condition (maintainer, 2026-09-04, §13H.12 Q3): 16B is exempt from
  the phase's Sprint 052 gate and MAY be planned and started in parallel with
  Sprint 052.** 16B depends on Sprint 052 existing as a study, not on its
  result. The exemption carries one obligation: 16B must not land a change
  that Sprint 052 would then be consuming, because Sprint 052 runs the Phase
  10 pipeline unmodified — non-interference is a Wave 0 decision for 16B's
  sprint if the two overlap in time.
- 16A only if the maintainer wants verdicts on the new sample kinds from day
  one (not required).

### Main risks

- **Leakage moves house.** With irregular rows, an embargo expressed in bars
  is not the same guard it was. This is the increment's central technical
  risk and its central test target.
- **Sample selection bias.** Rows conditioned on a signal firing are a biased
  slice of the market by construction. The contract must make that visible
  (persisted sample provenance), not hide it.
- Small sample universes: a selective signal may yield too few rows per fold
  to learn anything. `REJECTED_LOW_SAMPLE` (16A) exists for exactly this.
- **Parallel-start friction with Sprint 052** (new, from the Q3 carve-out): a
  shared-file collision between 16B's contract work and Sprint 052's run is
  possible if both are open at once. Mitigation: Sprint 052's FORBIDDEN-paths
  discipline already keeps it out of the pipeline; 16B's sprint declares the
  reverse boundary at Wave 0.

### Out of scope

- `strategy_trades`, `labelled_setups`, `sessions_or_windows` sample kinds.
- Any new estimator family, extra or dependency.
- MTF-capable `FeatureSpec` (a known, separately-tracked structural gap,
  §13G "Main risks").

### ADR

The `SampleSpec` contract shape and the `PredictiveTask` taxonomy are
hard-to-reverse contract decisions that every later increment depends on.
**An ADR is required for this increment** (§13H.9).

### Completion note (added at closure, 2026-09-08 — append-only, does not replace the text above)

**16B is DONE.** Delivered by Sprint 056 (`docs/archive/phases/phase-16-research-workbench/SPRINT_056.md`),
7/7 tasks, merged as five PRs into `sprint/sample-spec-foundation`
(#448 contract types + default elision, #449 sample provenance + schema v2,
#450 real `signal_occurrences` resolution, #451 irregular-spacing leakage
proof, #456 committed example + docs). ADR-0031 was accepted 2026-09-04 with
no corrections and the shipped contract shape matches it exactly — a
confirmation, not a surprise.

All four completion criteria above were met: the `every_bar` default is
byte-identical (`definition_hash`-comparable, asserted not assumed); a
`signal_occurrences` study's row count is asserted equal to the Signal
Model's occurrence count; purge/embargo semantics were re-derived and shown
correct for irregular spacing with no guard relaxed (the leakage-guard code
itself needed zero changes — Sprint 056 Finding 1 confirmed the risk was
elsewhere, at `label_end_at` derivation, and D-S056-05's filter-late rule
closed it); CI stayed synthetic-only and network-free throughout.

One item of technical debt was left open: **TD-031**
(`docs/planning/TECHNICAL_DEBT.md`, ACCEPTED/MEDIUM) — no loader exists yet
to turn a declared `signal_model_file` path into a `SignalModelDefinition`,
so a real (non-fixture) `signal_occurrences` study cannot run through
`trading-cli` today; every current caller must supply the resolved object
in-process. Its repayment trigger is 16C being planned, or an operator
needing a CLI-driven `signal_occurrences` study before then.

**This closure produced no verdict, no scorer and no study.** 16B remains a
contract-only increment; it does not advance 16A or 16C. Integration of
`sprint/sample-spec-foundation` into `main` is a separate, distinct
maintainer decision (SPRINT_056.md D-S056-03) and had not happened as of
this note — see `docs/planning/CURRENT_STATUS.md` §2/§3 for the current
integration state.
