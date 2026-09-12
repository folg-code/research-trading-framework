# Future Direction

This directory is for product and architecture directions **not yet delivered in full**. It is not evidence that a capability exists. For current behavior use [Reference](../reference/README.md); for sequencing use [Roadmap](../planning/ROADMAP.md); for binding decisions use the [ADR index](../adr/README.md).

| Direction | Document |
|---|---|
| Product-level direction and design principles | [Product Direction](PRODUCT_DIRECTION.md) |
| Local-first research application and public/private boundaries | [Research Application Product Vision](RESEARCH_APPLICATION_PRODUCT_VISION.md) |
| Calendar, holiday and broader session model | [Time Model Future](TIME_MODEL_FUTURE.md) |
| Historical synchronization, quotes/options, live recording and replay | [Market Data Future](MARKET_DATA_FUTURE.md) |
| State taxonomy, intrabar contract and expanded component requests | [Market Analysis Future](MARKET_ANALYSIS_FUTURE.md) |
| Bounded search and broader research-space analytics | [Research Space and Analytics](RESEARCH_SPACE_AND_ANALYTICS.md) |
| Replay, paper/live modes and broker/reconciliation targets | [Execution Runtime Future](EXECUTION_RUNTIME_FUTURE.md) |
| Event-system expansion | [Event System Future](EVENT_SYSTEM_FUTURE.md) |
| Component promotion lifecycle | [Component Promotion Lifecycle](COMPONENT_PROMOTION_LIFECYCLE.md) |
| Run identity and configuration layering | [Run Identity and Configuration](RUN_IDENTITY_AND_CONFIGURATION.md) |

The Market Analysis decision register now lives with [ADRs](../adr/MARKET_ANALYSIS_DECISIONS.md). Earlier mixed current/future wording is preserved as dated snapshots in the [Archive](../archive/snapshots/); the current pages above state future intent and link to Reference for the implemented baseline.

## Review rule

When a proposed capability ships, move its implemented contract into the relevant Reference page and leave only the still-future portion here. Do not keep a second current-state description in Vision. An accepted ADR takes precedence over an older design sketch; changing the decision requires the ADR process.
