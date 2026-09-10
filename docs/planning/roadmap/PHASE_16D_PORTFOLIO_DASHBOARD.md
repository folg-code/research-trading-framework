# Phase 16D — Portfolio Dashboard

```text
Status: IN PROGRESS
Product direction: ACCEPTED (maintainer, 2026-09-09)
PRD: ACCEPTED (maintainer, 2026-09-09)
Sprint plans: SPRINT_059 and SPRINT_060 are COMPLETE; SPRINT_061 is ACTIVE
```

This file is the detailed roadmap entry for Phase 16 increment 16D. The phase
index remains `PHASE_16_QUANT_WORKBENCH.md` §13H.4.

## Purpose

Evolve `apps/dashboard` from an artifact browser into a public portfolio that
lets a general software developer understand what was built and why, how the
architecture and independent workflows operate, and which persisted artifacts
demonstrate the result.

`docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` is authoritative for this
increment. It replaces the former Quant Lab framing. The dashboard presents
upstream verdicts and evidence; it does not create an accept/reject opinion.

## Planned outcomes

- A portfolio foundation: product thesis, a small shared-domain map, entry
  points to six independent workflows, explicit maturity labels and stable
  URLs for portfolio concepts.
- A deny-by-default, allowlisted public projection so the new public path does
  not expose the mounted private workspace or internal storage paths.
- A first complete vertical slice through Signal and Predictive Research:
  accessible workflow context, living Signal Quality methodology, the BTC
  Signal Quality study, a simplified persisted result and `Explore Evidence`.
- Version-controlled public content and reusable presentation components that
  can support later workflow slices without implying one mandatory pipeline.
- A complete study-grouped catalog over an automatically generated safe
  projection, representative evidence for every workflow and an immutable,
  recoverable production publication lifecycle (Sprint 061).

## Dependencies

- Phase 16A verdict artifacts.
- Phase 16C Signal Quality evidence, merged to `main` via #480.
- ADR-0022's read-only dashboard application boundary.
- The accepted `DASHBOARD_DEVELOPMENT_DIRECTION.md`.
- Maintainer approval of `docs/product/PRD-portfolio-dashboard-mvp.md` and the
  architecture recommendations in `SPRINT_059.md`.

## Completion criteria

- A general software developer can explain the product purpose, the shared
  domain foundation and the independence of the six workflows after a short
  maintainer-observed walkthrough.
- The BTC Signal Quality study is reachable from the overview in at most three
  navigation actions; its methodology and technical evidence are each one
  action away.
- The simplified study answers what was studied, the baseline/assumptions, the
  persisted result and persisted limitations, with two or three charts sourced
  only from allowlisted facts.
- Every displayed number, classification and verdict is traceable to a
  persisted artifact. The dashboard fits nothing, recomputes no research
  metric, imports no research engine, promotes nothing and declares nothing
  validated.
- Negative and `INCONCLUSIVE` evidence remains visible without implying a live
  edge, market forecast or trading approval.
- The dashboard import-boundary check covers both `apps/dashboard/src/` and
  `apps/dashboard/pages/`, closing the enforcement gap recorded as PRB-022.
- Existing technical evidence pages and current-only live-paper behavior remain
  available.

## Delivery slices

- **Sprint 059 — Portfolio Publication Foundation (COMPLETE):** settle the public
  projection and study-identity boundary, strengthen the app boundary test,
  establish content/routing contracts and ship the portfolio overview.
- **Sprint 060 — Signal Quality Portfolio Evidence (COMPLETE):** publish the
  methodology and the first simplified study view, connect it to the technical
  evidence, and validate the complete desktop walkthrough.
- **Sprint 061 — Portfolio Story, Content and Direction Completion (ACTIVE):**
  complete the public narrative, safe study-grouped catalog, representative
  workflow evidence and immutable production publication lifecycle.

## Extended completion scope

Sprint 061 pulls the remaining accepted Direction outcomes into the completion
scope: the study-grouped catalog, one representative result per workflow,
Engineering, Future Direction and Research & Engineering Notes. This extends
beyond the first-slice PRD without changing the read-only product boundary.

## Main risks

- Filesystem discoverability could be mistaken for publication approval.
- A presentation manifest could invent cross-workflow lineage.
- Presentation pressure could introduce dashboard-side metrics or verdicts.
- A coherent narrative could be drawn as one mandatory pipeline.
- The first slice could expand into the complete target information
  architecture.
