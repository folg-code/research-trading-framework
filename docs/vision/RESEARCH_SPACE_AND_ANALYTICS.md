# Research Space and Analytics — Future Direction

This page describes possible extensions to research-space planning and analytics. Current workflow behavior belongs to [Research Methodologies](../reference/workflows/RESEARCH_METHODOLOGIES.md), the [Research module guide](../reference/modules/RESEARCH.md) and workflow references. The [pre-review snapshot](../archive/snapshots/RESEARCH_SPACE_AND_ANALYTICS_pre_review.md) preserves the earlier mixed current/future text.

## Bounded research spaces

Signal Research already implements bounded family expansion, and Predictive
Research supports a bounded `CandidateSetSpec`; see their
[workflow](../reference/workflows/SIGNAL_RESEARCH.md) and
[methodology](../reference/workflows/methodologies/PREDICTIVE_RESEARCH.md).
The remaining direction is a cross-workflow preflight view of candidate count,
estimated compute/storage cost and pruning before a large run. It must avoid
implicit Cartesian expansion of parameters, components, datasets and folds.
Future planners may support staged expansion and explicit search constraints
without treating those two existing bounded paths as unimplemented.

## Staged methodology

A future screening path can move from individual components to pairwise interactions, small model compositions, complete strategy research and independent validation. Each stage should persist enough evidence to explain why candidates advanced or stopped. Screening is a prioritization tool, not a substitute for out-of-sample validation.

## Large result spaces

Potential analytics include marginal contribution, sensitivity surfaces, stability across regimes, multi-objective comparison and an explicit complexity penalty. Ranking should expose the underlying measures and uncertainty; it must not turn a noisy score into a trading recommendation.

Research families and parameter spaces may be grouped to compare related hypotheses while bounding multiplicity. Multiple-testing controls and walk-forward or other independent validation become more important as the number of candidates grows. A future implementation must state its correction method and evaluation scope before interpreting winners.

## Workflow-specific extensions

Signal Research may expand occurrence/outcome analytics and family-level comparison. Strategy Research may add bounded strategy-family search, no-trade analysis and broader market-fact support when its dependencies exist. Robustness and Predictive Research retain their own outcome semantics rather than being hidden inside one generic ranking pipeline.

See [Phase 16](../planning/roadmap/PHASE_16_QUANT_WORKBENCH.md) for currently sequenced work. This page is directional; it does not open an increment or change an accepted research contract.
