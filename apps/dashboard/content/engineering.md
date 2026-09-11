---
slug: engineering
title: Engineering
status: AS_BUILT
updated: 2026-09-10
order: 11
links: .github/workflows/ci.yml, apps/dashboard/docs/RUNBOOK.md, docs/adr/ADR-0034-portfolio-publication-boundary.md, docs/planning/PROBLEM_REGISTRY.md
---

Engineering quality in this project is expressed as boundaries that can fail
loudly, not only as successful output.

## Data and research integrity

Market-data import separates provider adapters, normalization, validation,
version allocation and publication. Research workflows record material
identity and preserve structured artifacts so later analytics can inspect a
run without quietly repeating it. Temporal alignment, leakage guards and
simulation assumptions have focused regression tests.

## Application boundaries

The dashboard is tested as a separate deployable consumer. Static import
checks prevent its source and page modules from importing framework research,
execution or provider implementations. The public portfolio path adds a
stricter rule: it reads an allowlisted projection that omits paths, private
configuration, source code, model binaries, credentials and operational logs.

The older technical pages are still being migrated from direct workspace
scanning during Sprint 061. Until that work is complete, the stricter
publication statement applies to the portfolio path rather than every legacy
view.

## Quality gates

Pull requests to `main` and `sprint/**` run Ruff lint and formatting, mypy,
unit and integration tests, package build checks, optional ML-family suites,
dashboard tests and CLI tests. Architectural checks cover the `src/` /
`user_data/` dependency and application imports.

Two gaps remain explicit at the start of this sprint: root mypy and pytest do
not cover the dashboard or scripts, and `scripts/dashboard/` is outside the
dashboard import scan. They are tracked as PRB-023 and PRB-024 rather than
hidden behind a general claim of complete coverage.

## Deployment and runtime

Changes to the dashboard on `main` trigger an SSH deployment that updates the
VPS checkout and rebuilds Docker Compose. The dashboard storage mount is
read-only; TLS terminates at a shared VPS edge outside this repository.
Application deployment is automated, while private workspace synchronization
is operator-managed today.

The public Live Paper view is also read-only. Its current path observes live
public market data with simulated execution and no real orders. Missing or
stale status is shown as such; the dashboard does not repair the runtime.
