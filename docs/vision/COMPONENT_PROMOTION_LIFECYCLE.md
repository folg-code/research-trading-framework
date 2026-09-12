# Component Promotion Lifecycle — Future Direction

This is a proposed lifecycle for locally developed Market Analysis components and mutable model definitions. Existing component identity and registry behavior belong in [Market Analysis Architecture](../reference/system/MARKET_ANALYSIS_ARCHITECTURE.md) and its [module guide](../reference/modules/MARKET_ANALYSIS.md). The [pre-review snapshot](../archive/snapshots/COMPONENT_PROMOTION_LIFECYCLE_pre_review.md) preserves the longer proposal.

## Promotion path

```text
Local working component → Experimental component → Validated candidate
                        → Promoted framework component → Released component
```

Working components may change freely, but research using them should preserve an implementation fingerprint. A proposed identity includes `component_id`, implementation and dependency hashes, resolved parameters and an explicit experimental reproducibility status. Those specific fields and the five-stage lifecycle are not current framework contracts.

Promotion into the maintained framework requires stability, strategy independence, reuse, tests, documentation and compatibility ownership. Formal versioning begins at that boundary. Not every completed local component must become public.

## Mutable model definitions

A similar future fingerprint rule may apply to locally edited Market, Signal, Exit, Risk and Strategy Models. It should include a definition hash, resolved parameters and dependency identities before formal release identity exists. Exact algorithms and storage paths require a separate design decision; do not infer them from the suggested lifecycle.
