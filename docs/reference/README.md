# As-Implemented Reference

This layer describes current behavior. Start at the [System Overview](system/SYSTEM_OVERVIEW.md), then use the [Module Map](system/MODULE_MAP.md) to locate ownership. For future intentions see [Vision](../vision/README.md); for decision history see [ADRs](../adr/README.md).

| Area | Start here | When to read |
|---|---|---|
| System | [System index](system/README.md) | Architecture, domain ownership, dependencies, time and data contracts |
| Modules | [Module guides](modules/README.md) | Package responsibilities and implementation entry points |
| Workflows | [Workflow index](workflows/README.md) | End-to-end Market Data, Research and Execution paths |
| Runbooks | [Runbook index](runbooks/README.md) | Operating the local/AWS dry-run and checking its pipeline |
| Examples | [Predictive BTC study](examples/BTC_PREDICTIVE_STUDY.md), [Signal Quality BTC study](examples/BTC_SIGNAL_QUALITY_STUDY.md) | Worked evidence, not universal behavior |

The [Predictive Verdict](PREDICTIVE_VERDICT.md) explains the versioned analyst verdict artifact. Detailed authoring examples and the component catalog live under [Modules](modules/README.md).

## Reading rule

Use the smallest page that answers the question. A workflow explains how modules cooperate; a module guide explains what a package owns; an ADR explains why a durable decision was made. Check implementation claims against the relevant code and tests when changing behavior.
