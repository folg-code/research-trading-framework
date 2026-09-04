# Trading Research Framework

# RESEARCH_SPACE_AND_ANALYTICS.md

> **Target architecture / not-yet-built content.** This file was created by
> Sprint 055 T008 out of `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §4.10;
> `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §11.1, §11.2,
> §11.5, §13, §14.1, §14.2, §14.4, §14.5, §14.6, §19 rules 17/18/20; and
> `docs/vision/WORKFLOWS_AI_ADR.md` §3.12, §3.14, §4.5, §4.13, §4.14, §4.18
> (all three source files now dissolved). It groups "how research spaces
> are bounded, staged and screened" — a continuous argument that was
> previously split across three files. Content below is preserved verbatim
> from the original files; only classification headers, this merge header,
> and provenance notes are newly authored/added.

---

## Research Space Boundaries (planner observability)

*(Longest/primary copy — merged from: `WORKFLOWS_AI_ADR.md` §3.12, now
dissolved. Classified MIXED by Sprint 054 T003b — the four-way conceptual
distinction is real and implemented, and `FamilyExperimentPlan` exposes
`candidates_generated`/`candidates_evaluated`/`candidates_skipped` — a
subset of the telemetry fields suggested below. The literal fields
`number_of_unique_dependencies`, `number_of_reused_nodes`,
`number_of_new_nodes` and `estimated_output_size` do not exist in the
planner.)*

Signal Research must distinguish:

```text
fixed selection
independent alternatives
logical composition
bounded search space
```

The planner should expose where possible:

```text
number_of_candidates
number_of_unique_dependencies
number_of_reused_nodes
number_of_new_nodes
estimated_output_size
applied_constraints
```

Unrestricted Cartesian-product expansion is not the default.

> **Merged from: `ARCHITECTURE_FOUNDATIONS.md` §4.10 "Research Spaces Must
> Be Bounded and Observable (planner-observability portion)", now
> dissolved.** That section (classified MIXED by Sprint 054 T001 — the
> framework-level distinction between fixed selection / independent
> alternatives / bounded search space, and the progressive-research
> staircase, are already realized; the planner-observability metadata has
> no matching field anywhere in `src/`) restated the same six-field
> telemetry list without the `number_of_` prefix (`candidate count`,
> `unique dependency count`, `reused nodes`, `new nodes`, `applied
> constraints`, `estimated output size`) and added: "Large search spaces
> require visible multiple-testing metadata." That one addition is the
> only unique material carried forward.

---

## Research-Space Growth

### The Problem

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §12/§11.1, now
dissolved. Note: this section was numbered `# 12` with subsections `##
11.1`/`## 11.2` in the source file — a pre-existing numbering
inconsistency, carried forward as a known defect rather than silently
renumbered.)*

Multitimeframe analysis expands the number of possible component combinations.

Example dimensions:

```text
4 analytical properties
4 timeframe alternatives
5 parameter variants
```

Naive combination growth may become extremely large before adding:

- Signals,
- Exits,
- Risk Models,
- instruments,
- periods,
- execution assumptions.

A fast engine does not solve the statistical problem.

It may only produce overfitted results faster.

### No Implicit Full Cartesian Product

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §11.2, now
dissolved. §11.3 Fixed Selection and §11.4 Independent Alternatives were
classified CURRENT by Sprint 054 T003 and moved into the former
`docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`, which Sprint 055
T007 merged into
[`docs/reference/system/TIME_AND_ALIGNMENT.md`](../reference/system/TIME_AND_ALIGNMENT.md)
and [`docs/reference/workflows/SIGNAL_RESEARCH.md`](../reference/workflows/SIGNAL_RESEARCH.md#independent-experiment-expansion)
— T007 notes this specific verbatim section was not individually re-verified
against those targets, so treat the exact wording as unconfirmed pending a
follow-up spot-check; not duplicated here.)*

The framework must not interpret every list of timeframe or parameter values as a mandatory full Cartesian product.

Configuration must distinguish:

```text
fixed selection
independent alternatives
bounded search space
logical composition
```

These have different meanings.

### Search Constraints

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §11.5, now
dissolved. Classified MIXED by Sprint 054 T003 —
`candidate_bounds.max_candidates` — a bound-and-prune mechanism — is
confirmed implemented (`research/signal_research/family_planning.py`). The
specific named constraint fields below (`max_distinct_timeframes`,
`require_context_timeframe_gte_signal_timeframe`,
`forbid_duplicate_analysis_category`) returned zero matches in `src/` as of
this sprint.)*

A bounded research space may declare constraints such as:

```yaml
constraints:
  max_components: 4
  max_distinct_timeframes: 3
  require_context_timeframe_gte_signal_timeframe: true
  forbid_duplicate_analysis_category: true
```

Possible semantic constraints:

```text
trend timeframe >= signal timeframe
context timeframe >= entry timeframe
maximum number of Market Model conditions
maximum number of independent parameters
maximum model complexity
```

The planner should reject or prune invalid combinations before computation.

---

## Hierarchical Research Methodology

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §13, now
dissolved. Classified AMBIGUOUS by Sprint 054 T003 — this describes a
research process/methodology for humans/agents to follow rather than a
system behavior with a code artifact to check. The underlying validation
techniques for Stage 5 (`research/robustness/`) do exist as tools; whether
researchers actually follow this staged progression is a process question,
not verifiable via code search.)*

The framework should encourage progressive research rather than immediate full-grid Strategy Research.

### Stage 1: Individual Components

Test one market property at a time.

Examples:

```text
Trend State 1h as a one-condition Market Model
Trend State 4h as a one-condition Market Model
Liquidity Sweep as a one-condition Signal Model
Signal Model × Trend Market Model
```

Questions:

- Does the property add information?
- Which timeframe is meaningful?
- Is the sample size sufficient?
- Is the effect stable over time?
- Does it generalize across instruments?

### Stage 2: Pairwise Interactions

Test only promising pairs.

Examples:

```text
Trend State 4h × Volatility Regime 1h
Trend State 1h × Structural State 30m
Market Phase 4h × Volatility Regime 30m
```

### Stage 3: Small Model Compositions

Build compact Market Models and Signal Models from validated components.

Preferred initial size:

```text
2–4 analytical conditions
```

A larger model requires stronger evidence and explicit complexity justification.

### Stage 4: Complete Strategy Research

Only selected Market Models and Signal Models are combined with:

```text
Exit Model
Risk Model
```

This produces complete Strategy Model candidates.

### Stage 5: Validation

Selected candidates should undergo:

- out-of-sample validation,
- walk-forward analysis,
- parameter perturbation,
- cost sensitivity,
- cross-asset analysis,
- Monte Carlo analysis,
- family analysis.

---

## Automated Analysis of Large Result Spaces

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §15, now
dissolved.)*

Manual inspection must not be the primary method of analysing large research spaces.

The Research domain should support automated analytical passes.

### Screening

*(Classified AMBIGUOUS by Sprint 054 T003 — `research/predictive/selection.py`
is a model-selection module for the Predictive Research track, not a
generalized experiment-screening mechanism matching the criteria below;
`family_planning.py`'s cap-and-skip logic is evidence of *some* automated
pruning, but not specifically of these named screening criteria.)*

Automatically reject or flag experiments with:

- insufficient sample size,
- unstable results,
- weak out-of-sample behaviour,
- extreme parameter sensitivity,
- excessive concentration in one period,
- excessive concentration in one instrument,
- invalid temporal alignment,
- excessive complexity.

### Marginal Contribution

*(Classified AMBIGUOUS by Sprint 054 T003 — no nested-model-comparison
utility or metric was found via targeted search in `research/analytics/`
or `research/robustness/`.)*

The framework should compare nested models.

Example:

```text
Signal
Signal × Trend State 4h
Signal × Trend State 4h × Volatility Regime 1h
```

This measures whether an added condition creates real incremental value.

### Sensitivity Surfaces

*(Classified FUTURE by Sprint 054 T003. `Grep` for `sensitivity_surface`
returned zero matches in `src/`; no matrix/surface-shaped analytics output
was found.)*

Timeframe and parameter combinations should be summarised through matrices or surfaces.

Example:

```text
trend timeframe × volatility timeframe → research score
```

The purpose is to identify stable regions rather than one maximum point.

### Multi-Objective Evaluation

*(Classified FUTURE by Sprint 054 T003. `Grep` for `Pareto` returned zero
matches in `src/`. Individual metrics exist elsewhere, but no
multi-objective combination/ranking mechanism ties them together as
described below.)*

A candidate should not be selected by one metric alone.

Possible dimensions:

```text
expectancy
stability
sample size
drawdown
complexity
out-of-sample performance
cross-asset consistency
execution sensitivity
```

The framework may use Pareto-frontier analysis or an explicit composite score.

### Complexity Penalty

*(Classified FUTURE by Sprint 054 T003. `Grep` for
`complexity_penalty`/`multiple_testing` returned zero matches in `src/`. No
adjusted-score formula of this shape was found in `research/analytics/`.)*

More complex models should require materially better and more stable evidence.

Conceptual score:

```text
adjusted_score
=
performance_score
- complexity_penalty
- instability_penalty
- multiple_testing_penalty
```

The exact formula belongs to Research Analytics configuration and should not be hard-coded globally.

---

## Signal Research Analytics

*(Merged from: `WORKFLOWS_AI_ADR.md` §3.14, now dissolved. Classified MIXED
by Sprint 054 T003b —
`research/analytics/{conditional,diagnostics,grouping,distribution,histograms,aggregates}.py`
implement a substantial subset of the operations below (conditional
analysis, distributions, grouping/aggregation). "Clustering" and general
"insight generation" have no code counterpart.)*

Analytics operate on stored Signal Research Datasets.

Typical operations include:

- forward-return distributions,
- MFE and MAE,
- event frequency,
- context persistence,
- hit rate,
- conditional analysis,
- Market Model comparison,
- Signal Model comparison,
- marginal contribution,
- cross-asset comparison,
- time-of-day analysis,
- stability by period,
- sample-size analysis,
- parameter sensitivity,
- timeframe sensitivity,
- family analysis,
- clustering,
- insight generation.

Analytics must not mutate the source research dataset.

---

## Strategy Research Space

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.5, now dissolved. Classified MIXED
by Sprint 054 T003b — no `research/strategy_research/` package equivalent
to `research/signal_research/family_planning.py` was found; only
`application/strategy_research/` exists, which orchestrates but does not
implement family-style bounded multi-dimension expansion. The
`experiments:` YAML example below is presented as already-working syntax
but has no implementing module.)*

A Strategy Research definition may declare bounded alternatives.

Example:

```yaml
strategy_research:
  assets:
    - NQ
    - ES

  signal_models:
    experiments:
      - bullish_sweep
      - breakout_reclaim

  market_models:
    experiments:
      - bullish_trend
      - ranging_market

  exit_models:
    experiments:
      - fixed_rr
      - atr_exit
      - session_exit

  risk_models:
    experiments:
      - fixed_risk
      - volatility_adjusted_risk
```

The planner should expose:

```text
number_of_candidates
estimated_dependencies
reused_nodes
new_nodes
estimated_storage
applied_constraints
```

before expensive computation.

---

## Rankings

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.13, now dissolved. Classified
AMBIGUOUS by Sprint 054 T003b — `Grep` for `ranking`/`Ranking` found
matches only in `research/robustness/` (verdict/report formatting) and
`research/predictive/leaderboard.py` (a different research track). No
`strategy_research`-scoped ranking module with the six-field contract
below was found; the search was not exhaustive.)*

Strategy rankings are valid research outputs.

A ranking must define:

```text
ranking_objective
eligibility_filters
normalization
tie_breaking
minimum_sample_size
robustness_requirements
```

A raw ranking by net profit is insufficient.

A top-ranked strategy is not automatically validated.

---

## Strategy Families

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.14, now dissolved. Classified
FUTURE by Sprint 054 T003b — unlike Signal Research (`family_planning.py`,
`signal_research_family.py` — confirmed CURRENT), there is no
Strategy-Research-side "family" concept in code at all. See
`docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md` §6 for the `families/`
storage-layout inconsistency this finding exposed.)*

Related candidates should be grouped into Strategy Families.

Example:

```text
Bullish Sweep
Bullish Sweep + Trend
Bullish Sweep + Trend + Volatility
Bullish Sweep + Trend + Volatility + Session Filter
```

Family analysis evaluates:

- component contribution,
- stability across nearby variants,
- parameter sensitivity,
- timeframe sensitivity,
- cross-asset behaviour,
- isolated optimum risk,
- overfitting risk.

---

## Multiple Testing

*(Merged from: `WORKFLOWS_AI_ADR.md` §4.18, now dissolved. Classified MIXED
by Sprint 054 T003b — `candidates_generated`/`candidates_evaluated`/
`candidates_skipped` are confirmed CURRENT for Signal Research families,
and `research/predictive/splitting.py` confirms validation-split
definitions exist for the Predictive Research track. For Strategy Research
specifically, no equivalent candidate-count bookkeeping was found,
consistent with the Strategy Research Space/Strategy Families findings
above that Strategy Research lacks a family/bounded-expansion mechanism
analogous to Signal Research's.)*

Large strategy spaces create false-discovery risk.

Every run should preserve:

- number of generated candidates,
- number of evaluated candidates,
- number of rejected candidates,
- pruning rules,
- selection history,
- validation splits,
- family grouping,
- ranking objective.

A high score among millions of candidates is not automatically evidence of edge.

---

## Architectural Rules (research-space portion)

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §19 rules
17/18/20, now dissolved. Rules 1-16, 19, 22, 24 were classified CURRENT and
moved into the former `docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`,
which Sprint 055 T007 merged into
[`docs/reference/system/TIME_AND_ALIGNMENT.md`](../reference/system/TIME_AND_ALIGNMENT.md)
(rules 13/16 explicitly retained there; the rest were judged duplicative of
`DOMAIN_MODEL.md`/`MODULE_MAP.md`/`SYSTEM_OVERVIEW.md` per T007's own notes
and not individually re-verified — treat as unconfirmed pending a follow-up
spot-check). Rule 21 (fingerprints) lives in `COMPONENT_PROMOTION_LIFECYCLE.md`;
rule 23 (execution runtime modes) lives in `EXECUTION_RUNTIME_FUTURE.md`.)*

17. Research spaces are bounded and observable. *(Partially built — see "Search Constraints" above.)*
18. Research progresses from small hypotheses to complete Strategy Models. *(See "Hierarchical Research Methodology" above — process claim, AMBIGUOUS.)*
20. Large spaces require automated screening and multiple-testing metadata. *(Screening is AMBIGUOUS — see "Screening" above; multiple-testing metadata is CURRENT for the Signal Research family case only, see the reference copy of the source document's former §16.)*
