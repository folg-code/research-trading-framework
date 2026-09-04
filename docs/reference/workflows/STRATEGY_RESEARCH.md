# Strategy Research — As-Built Reference

> Extracted from the former `docs/reference/system/WORKFLOWS_ARCHITECTURE.md`
> ("Strategy Research" section) by Sprint 055 T007, per the maintainer-approved
> reversal of Sprint 054 T007's rejection in
> `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md` §1 — this is a section
> extraction with no new prose, not authoring. That source file's own content
> originated in `docs/vision/WORKFLOWS_AI_ADR.md`, moved by Sprint 054 T006c.
> The section was classified **CURRENT** (or is the current-behavior portion
> of a section classified **MIXED**) against the codebase as of 2026-09-03.
> See
> `docs/planning/sprints/SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`
> for the full section-by-section classification, evidence, and code
> references.
>
> For "which methodology should I choose", see
> [`RESEARCH_METHODOLOGIES.md`](RESEARCH_METHODOLOGIES.md) §5.

---

## Purpose

Strategy Research evaluates complete Strategy Models.

Its research vector is:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

Strategy Research evaluates:

- profitability,
- stability,
- robustness,
- execution sensitivity,
- component interactions,
- capital and exposure behaviour.

---

## Core Question

Strategy Research answers:

```text
How does a complete Strategy Model perform under explicit historical and execution assumptions?
```

It does not merely ask whether a signal contains predictive information.

It evaluates how the complete composition behaves as a trading system.

---

## Strategy Model

A Strategy Model is composed from:

```text
Market Model
×
Signal Model
×
Exit Model
×
Risk Model
```

Position sizing belongs to the Risk Model in Version 1.

A Strategy Model preserves:

- component identities,
- versions or definition hashes,
- parameters,
- dependency lineage,
- composition identity.

A Strategy Model is not a monolithic class that calculates:

- Market Analysis,
- entries,
- exits,
- position sizing,
- broker interaction.

---

## Composition Rules

Market Models and Signal Models may use explicit logical expression trees.

Exit Models and Risk Models are contract-based components.

They may use:

- declarative conditions,
- deterministic calculation logic,
- controlled references to Strategy and Market Analysis state.

Version 1 should normally select one Exit Model and one Risk Model per Strategy Model unless composite contracts are explicitly defined.

---

## Historical Strategy Simulation

Batch or vectorized backtesting belongs to Research.

It is optimized for:

- large strategy spaces,
- historical performance analysis,
- explicit simulation assumptions,
- reusable Strategy Research Datasets.

It may simulate:

- order generation,
- fills,
- commissions,
- slippage,
- latency,
- position state,
- cash state,
- realized PnL,
- unrealized PnL.

Historical Strategy Simulation consumes Strategy Models.

It does not define them.

---

## Strategy Research Computation Output

The computation phase produces a persistent:

```text
Strategy Research Dataset
```

It may contain:

- Strategy Model identity,
- component identities,
- definition hashes,
- individual simulated trades,
- simulated orders,
- simulated fills,
- position history,
- equity curve,
- return series,
- performance facts,
- execution assumptions,
- experiment dimensions,
- failure states.

Raw trade-level and time-series results should be preserved where practical.

Aggregated metrics alone are insufficient for future analysis.

---

## Strategy Analytics

Analytics may calculate:

- total return,
- CAGR where meaningful,
- expectancy,
- profit factor,
- Sharpe ratio,
- Sortino ratio,
- maximum drawdown,
- MAR ratio,
- win rate,
- payoff ratio,
- exposure,
- turnover,
- tail loss,
- stability by period,
- parameter sensitivity,
- asset sensitivity,
- execution-cost sensitivity,
- component contribution.

No single metric determines strategy quality.

---

## Walk Forward

Walk-forward analysis is a Research validation tool.

It records:

- train windows,
- validation windows,
- test windows,
- step size,
- parameter selection rules,
- retraining policy,
- aggregation policy.

It is not a Strategy Model component.

---

## Monte Carlo

Monte Carlo analysis evaluates uncertainty and path dependence.

Possible methods:

- trade-order reshuffling,
- bootstrap resampling,
- block bootstrap,
- execution-cost perturbation,
- return perturbation,
- missed-trade simulation.

Every method must state its assumptions.

Monte Carlo outputs are derived analytics, not replacements for raw results.

---

## Robustness

Robustness analysis may include:

- parameter perturbation,
- neighbouring model variants,
- subperiod analysis,
- cross-asset analysis,
- cost sensitivity,
- delayed entry,
- worse fills,
- missing trades,
- regime segmentation,
- out-of-sample validation.

A candidate must not be described as validated without explicit robustness criteria.

---

## Reuse Rule

If the following remain unchanged:

```text
Market Dataset
Market Analysis definitions
Strategy component definitions
execution assumptions
simulation engine version
configuration
random seeds
```

then the existing Strategy Research Dataset should be reused.

New rankings, filters and family analyses — **not yet implemented for
Strategy Research, see PRB-020** — should not trigger a new backtest
automatically.

> **PRB-020 note (added Sprint 055 T007, per D-S055-04 SS3 G-03):**
> `docs/planning/PROBLEM_REGISTRY.md` **PRB-020** (OPEN, MEDIUM) records
> that Signal Research has a real "family" concept
> (`research/signal_research/family_planning.py`) while Strategy Research
> has no equivalent in code today. The "family analyses" reference above is
> qualified accordingly rather than rewritten, per verbatim-move discipline
> (D-S055-04). See [`SIGNAL_RESEARCH.md`](SIGNAL_RESEARCH.md)'s reuse rule
> for the Signal Research side, where the concept is real.
