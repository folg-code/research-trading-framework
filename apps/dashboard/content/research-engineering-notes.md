---
slug: research-engineering-notes
title: Research & Engineering Notes
status: AS_BUILT
updated: 2026-09-10
order: 15
links: docs/adr/ADR-0034-portfolio-publication-boundary.md, docs/reference/BTC_SIGNAL_QUALITY_STUDY.md, docs/reference/BTC_PREDICTIVE_STUDY.md, docs/adr/ADR-0021-live-dry-run-execution-demo.md
---

These notes record meaningful changes in method, architecture and direction.
They are selected editorial entries, not an automatic sprint changelog.

## 2026-09-10 — Publishing evidence without publishing the workspace

The first portfolio slice replaced filesystem discoverability with an explicit
publication decision. A build-time generator copies only allowlisted persisted
facts into a versioned projection. Unknown fields and internal paths are denied
by default, while a dashboard-local manifest groups named evidence without
claiming hidden lineage between workflows.

The remaining technical pages still use the earlier scanner and are being
migrated during Sprint 061. The distinction stays visible until that work is
complete.

## 2026-09-09 — Why negative results stay visible

The BTC Signal Quality study persisted an `INCONCLUSIVE` predictive verdict and
found that score filtering did not meaningfully improve its downstream strategy
comparison. The earlier real-data Predictive Study also preserved a split
result: classification cleared its declared comparison bar, regression did not,
and the conditionally triggered tree pass showed a stronger overfit signature.

Neither result was repaired by widening the search after seeing the numbers.
That stopping discipline is part of the evidence.

## 2026-08-12 — Live data is not live trading

The BTC dry-run path consumes public live market data but sends decisions to a
simulated broker. Runtime events, positions and health can be observed through
a read-only status surface. It cannot place real exchange orders.

This boundary is why the dashboard uses the explicit label `LIVE MARKET DATA /
SIMULATED EXECUTION / NO REAL ORDERS` and treats a stale status as unavailable
rather than presenting an old snapshot as current operation.
