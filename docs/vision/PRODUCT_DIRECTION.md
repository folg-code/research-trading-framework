# Product Direction

This page states future product direction. The [System Overview](../reference/system/SYSTEM_OVERVIEW.md) and [Domain Model](../reference/system/DOMAIN_MODEL.md) describe the implemented architecture; [ADRs](../adr/README.md) are binding decisions. The [pre-review snapshot](../archive/snapshots/PRODUCT_DIRECTION_pre_review.md) preserves the earlier mixed architectural/product wording.

## Purpose

The framework should remain a modular platform for systematic trading research and strategy execution, independent of a single asset class, broker, provider, timeframe or strategy style. It should help a user move from trusted market facts to reusable analytical language, explicit models, reproducible research and controlled execution without imposing one mandatory pipeline.

Signal Research, Strategy Research and Strategy Execution are independent capabilities with shared domain contracts. Further product surfaces may compose them, but must not make their private workflow state mandatory input to another capability.

## Long-term capabilities

The product may expand to more asset classes and market-fact types when concrete research questions justify them: futures, equities, forex, crypto, options context and other sources. Market Analysis should support reusable components without turning strategy-specific hypotheses into shared market facts.

Future research directions include bounded automated screening, portfolio research, additional statistical and machine-learning methods, order-flow analysis and options-derived context. Execution may grow from the current dry-run slice toward replay, paper, live and multi-account modes through explicit gates. Distributed computation is a response to demonstrated scale limits, not a default platform shape.

A local-first Research Application can offer a coherent interface over these capabilities while preserving explicit CLI interoperability, private control and deliberate public publication. See [Research Application Product Vision](RESEARCH_APPLICATION_PRODUCT_VISION.md).

## Constraints on expansion

New capabilities must preserve reproducibility, temporal correctness, domain ownership, user-space separation and independent workflows. A future extension is not an implementation claim or an approved sprint. Use the [Roadmap](../planning/ROADMAP.md) for sequencing and the [ADR process](../adr/README.md) for durable architectural changes.
