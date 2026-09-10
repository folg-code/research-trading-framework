---
slug: future-research-application
title: Research Application
status: FUTURE_IDEAS
updated: 2026-09-10
order: 14
links: docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md, docs/vision/PRODUCT_DIRECTION.md
---

The Research Application is a **Draft** product vision. It is not implemented,
no UI stack or sprint is approved, and this page does not turn the vision into
an architecture decision.

## Local-first Workbench

The proposed Workbench would make existing framework workflows easier to
operate near local research data and compute. A maintainer could select an
immutable dataset, prepare an explicit configuration, run an existing workflow
and inspect persisted results without memorizing every command.

The application would remain another front door. Python and CLI operation stay
supported, configurations remain human-readable, and artifacts produced
outside the UI remain discoverable when they satisfy the same contracts.

## Inspectable comparison

Comparison would show material differences such as dataset, instrument, period,
timeframe, model identity and simulation assumptions. Incompatible runs could
remain inspectable without the application manufacturing a universal winner.
The framework or owning analytics layer would still produce every metric,
classification and verdict.

## Immutable artifacts and explicit publication

Imported source data would remain untouched. Canonical datasets and research
artifacts would be versioned and treated as immutable. Publishing would create
a sanitized read-only projection rather than expose private configuration,
strategy source, model files, infrastructure details, logs or controls.

Sprint 061's automatic safe catalog inclusion is a public-dashboard rule. It
does not approve the draft Workbench's private publishing interaction or a new
framework Study aggregate.

## Later private operation

A later private live/paper control surface could be separated from the public
portfolio. It would need explicit authorization, deployment identity, recovery,
reconciliation and audit decisions before implementation. The public site
would remain read-only and could never become a disguised command surface.

## Hard boundaries

The Research Application cannot become:

- a second research, simulation or execution engine;
- an automatic strategy selector or promotion authority;
- a destructive market-data or artifact editor;
- a public start, stop, order or emergency-control surface;
- a reason to couple independent workflows or replace CLI/Python operation.
