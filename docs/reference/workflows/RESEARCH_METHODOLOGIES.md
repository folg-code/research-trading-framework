# Research Methodologies

Choose a methodology by the question and evidence it produces. This page is the entry point; topic pages carry detail, while [workflow references](README.md) define contracts and persisted outputs. The [pre-review snapshot](../../archive/snapshots/RESEARCH_METHODOLOGIES_pre_review.md) preserves the earlier combined narrative.

## 1. Methodology Overview

| Question | Methodology | Detailed method |
|---|---|---|
| Does a market condition precede an outcome? | Signal Research | [Signal](methodologies/SIGNAL_RESEARCH.md) |
| Which reusable model composition explains that condition? | Model Research | [Model](methodologies/MODEL_RESEARCH.md) |
| How does a complete strategy perform under explicit fills and risk? | Strategy Research | [Strategy](methodologies/STRATEGY_RESEARCH.md) |
| Does a strategy survive perturbation and regime changes? | Robustness Research | [Robustness](methodologies/ROBUSTNESS_RESEARCH.md) |
| Does a predictive task generalize out of sample? | Predictive Research | [Predictive](methodologies/PREDICTIVE_RESEARCH.md) |
| How do multiple strategies or exposures interact? | Future Portfolio Research | [Portfolio direction](../../vision/PORTFOLIO_RESEARCH_FUTURE.md) |

## 2. Shared Research Foundations

All methods use published market data, explicit model/component identities, time and availability semantics, bounded experiments and persisted artifacts. Analytics reads evidence instead of silently rerunning computation. See [Market Data](MARKET_DATA.md), [Research module](../modules/RESEARCH.md) and [Time and Alignment](../system/TIME_AND_ALIGNMENT.md).

## 3. Shared Research Principles

Declare the hypothesis, inputs, candidate space and evaluation policy before interpreting outcomes. Make missing data, look-ahead protection, cost assumptions and failure cases visible. A result is evidence for a bounded question, not permission to trade.

## 4. Signal Research

[Signal methodology](methodologies/SIGNAL_RESEARCH.md) covers occurrence and forward-outcome questions. [Signal workflow](SIGNAL_RESEARCH.md) specifies scopes, contracts and persisted outputs.

## 5. Model Research Methodology

[Model methodology](methodologies/MODEL_RESEARCH.md) compares reusable model compositions without turning them into complete strategies.

## 6. Strategy Research

[Strategy methodology](methodologies/STRATEGY_RESEARCH.md) evaluates complete strategies under simulation assumptions. [Strategy workflow](STRATEGY_RESEARCH.md) owns the computation and artifact contract.

## 7. Robustness Research

[Robustness methodology](methodologies/ROBUSTNESS_RESEARCH.md) studies stability across parameters, time, stress and perturbation.

## 8. Predictive Research

[Predictive methodology](methodologies/PREDICTIVE_RESEARCH.md) covers task/sample declarations, validation folds, baselines and honest out-of-sample verdicts. See [Predictive Verdict](../PREDICTIVE_VERDICT.md) for the versioned artifact.

## 9. Portfolio Research

[Portfolio Research Future](../../vision/PORTFOLIO_RESEARCH_FUTURE.md) records
the proposed method. There is no current Portfolio Research workflow contract.

## 10. Choosing a Methodology

Start with the narrowest question that can falsify the hypothesis. If the question is about a condition, use Signal/Model Research; if it includes entries, exits and sizing, use Strategy Research; if it concerns stability, use Robustness; if it predicts a declared target, use Predictive Research. Cross-workflow progression is optional, not a mandatory pipeline.

## 11. Optional Research Progression

One useful path is component observation → model comparison → strategy simulation → robustness validation → independent review. Each step produces its own evidence and can be entered independently when the question warrants it.

## 12. Research Artifacts

Persist material input identity, dataset versions, configuration, time policy, results and lineage. The exact artifact schema belongs to each [workflow](README.md) and its module contracts.

## 13. Quality and Anti-Overfitting Principles

Bound candidate counts, keep validation independent, expose multiple-testing risk, compare against baselines and record negative results. Prefer reproducible, interpretable evidence over a single favorable score.

## 14. Relationship to Execution

Research simulation and runtime execution have different owners. A successful research result does not authorize execution; [Strategy Execution](STRATEGY_EXECUTION.md) has its own safety and state contracts.

## 15. Methodology Boundaries

This index answers **which method and why**. Workflow pages answer **what runs and what it persists**. Module pages answer **which package owns the contract**.

## 16. References

[System Overview](../system/SYSTEM_OVERVIEW.md) → [Module Map](../system/MODULE_MAP.md) → [Research module](../modules/RESEARCH.md) → [workflow index](README.md). Future research-space directions are in [Vision](../../vision/RESEARCH_SPACE_AND_ANALYTICS.md).
